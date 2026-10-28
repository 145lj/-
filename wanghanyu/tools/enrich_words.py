"""
用 krdict 给 data/words.json 补词性、中文多义项、分级。

  python tools/enrich_words.py            # 增量：已补过的跳过
  python tools/enrich_words.py --limit 30 # 先试跑一小批
  python tools/enrich_words.py --force    # 全部重取

新增字段（原有字段一律不动，出错可回退）：
  pos / pos_cn      词性（韩文原名 + 中文）
  grade_cn          词典分级（初级/中级），没有则为空
  pronunciation     音变标注，如 책까방
  senses_cn         各义项中文，按义项顺序
  meaning_cn        合并去重后的一行中文释义（界面直接用这个）
"""
import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from utils.krdict import lookup, API, PROXY_URL          # noqa: E402

WORDS = os.path.join(ROOT, 'data', 'words.json')
FAILED = os.path.join(ROOT, 'data', 'krdict_failed.txt')
MAX_SENSES = 6          # 一张卡片放不下 33 个义项
SPLIT = re.compile(r'[，,;；、]')

_session = requests.Session()
_session.headers.update({'User-Agent': 'Mozilla/5.0'})
_session.proxies.update({'http': PROXY_URL, 'https': PROXY_URL})

_lock = threading.Lock()
_next_allowed = [0.0]


def throttle(seconds):
    """全局限速：不管开几个线程，两次请求之间至少间隔 seconds"""
    with _lock:
        now = time.time()
        wait = _next_allowed[0] - now
        _next_allowed[0] = max(now, _next_allowed[0]) + seconds
    if wait > 0:
        time.sleep(wait)


def merge_meaning(senses):
    """把前几个义项的中文词义拆开、去重、按原顺序拼成一行"""
    seen = []
    for sense in senses[:MAX_SENSES]:
        for part in SPLIT.split(sense['zh_word']):
            part = part.strip()
            if part and part not in seen:
                seen.append(part)
    return '；'.join(seen)


def one(entry, delay, retries=3):
    word = entry['word']
    last = None
    for attempt in range(retries):
        throttle(delay)
        try:
            hit = lookup(word, session=_session)
        except Exception as e:
            last = '%s: %s' % (type(e).__name__, str(e)[-60:])
            time.sleep(2.0 * (attempt + 1) ** 2)   # 2s / 8s / 18s 退避
            continue
        if hit is None:
            entry['krdict_miss'] = True    # 标记未收录，下次增量不再重复请求
            return entry, 'miss'
        entry['pos'] = hit['pos']
        entry['pos_cn'] = hit['pos_cn']
        entry['grade_cn'] = hit['grade_cn']
        entry['pronunciation'] = hit['pronunciation']
        entry['senses_cn'] = [s['zh_word'] for s in hit['senses'] if s['zh_word']]
        entry['senses_ko'] = [s['definition'] for s in hit['senses']]
        entry['meaning_cn'] = merge_meaning(hit['senses'])
        return entry, 'ok'
    return entry, 'error:%s' % last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--delay', type=float, default=1.0, help='两次请求之间的最小间隔秒数')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()

    with open(WORDS, encoding='utf-8') as f:
        words = json.load(f)

    todo = [w for w in words if args.force
            or (not w.get('pos_cn') and not w.get('krdict_miss'))]
    if args.limit:
        todo = todo[:args.limit]
    print('共 %d 词，本次处理 %d，并发 %d，间隔 %.1fs（约 %.0f 分钟）'
          % (len(words), len(todo), args.workers, args.delay,
             len(todo) * args.delay / 60))
    if not todo:
        print('全部已补齐。')
        return 0

    stats = {'ok': 0, 'miss': 0, 'error': 0}
    failed = []
    t0 = time.time()
    done = 0

    with open(FAILED, 'w', encoding='utf-8') as fail_f:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for entry, status in pool.map(lambda w: one(w, args.delay), todo):
                done += 1
                key = status if status in stats else 'error'
                stats[key] = stats.get(key, 0) + 1
                if key != 'ok':
                    failed.append('%s\t%s' % (entry['word'], status))
                    fail_f.write(failed[-1] + '\n')
                    fail_f.flush()
                    print('  失败 %s -> %s' % (entry['word'], status), flush=True)
                if done % 50 == 0 or done == len(todo):
                    speed = done / max(time.time() - t0, 1e-6)
                    left = (len(todo) - done) / max(speed, 1e-6)
                    print('  %d/%d  %.1f 词/秒  剩余约 %.0f 分钟  命中 %d 未收录 %d 出错 %d'
                          % (done, len(todo), speed, left / 60,
                             stats['ok'], stats['miss'], stats['error']), flush=True)
                    _save(words)

    _save(words)
    print('完成：命中 %d，未收录 %d，出错 %d（清单 %s）'
          % (stats['ok'], stats['miss'], stats['error'], FAILED))
    print('已写回 %s' % WORDS)
    return 0


def _save(words):
    tmp = WORDS + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)
    os.replace(tmp, WORDS)


if __name__ == '__main__':
    sys.exit(main())
