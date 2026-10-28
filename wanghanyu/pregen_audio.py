"""
批量预生成韩语发音，一次性把 data/words.json 里的单词和例句全拉到 data/tts/。

  python pregen_audio.py                 # 增量：已存在的跳过
  python pregen_audio.py --rate +40%     # 换语速（会重跑，因为文件名不含语速）
  python pregen_audio.py --force         # 全部重做
  python pregen_audio.py --only word     # 只拉单词（word / example / all）

缓存文件名和 App 里 AudioPlayer 用的是同一个 sha1，所以拉完 App 直接命中，
之后不再需要网络。失败条目写进 data/tts/_failed.txt，重跑即可续传。
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')
os.environ.setdefault('KIVY_NO_ARGS', '1')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import audio                      # noqa: E402
from utils.audio import fetch, speakable     # noqa: E402
from utils.paths import resource            # noqa: E402

WORDS_JSON = resource('data', 'words.json')
FAILED_TXT = resource('data', 'tts', '_failed.txt')


def collect(only, limit):
    with open(WORDS_JSON, encoding='utf-8') as f:
        words = json.load(f)
    texts = []
    seen = set()
    for w in words:
        for field in (('word',) if only == 'word' else
                      ('example',) if only == 'example' else ('word', 'example')):
            text = speakable(w.get(field) or '')
            if text and text not in seen:
                seen.add(text)
                texts.append(text)
    return texts[:limit] if limit else texts


def one(text, retries):
    for attempt in range(retries):
        path = fetch(text, 'ko')
        if path:
            return text, True
        time.sleep(1.5 * (attempt + 1))
    return text, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rate', default=None, help="edge-tts 语速，如 +30%%")
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--retries', type=int, default=3)
    ap.add_argument('--force', action='store_true', help='忽略已有缓存，全部重做')
    ap.add_argument('--only', choices=('word', 'example', 'all'), default='all')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    if args.rate:
        audio.TTS_RATE = args.rate
    os.makedirs(audio.CACHE_DIR, exist_ok=True)

    texts = collect(args.only, args.limit)
    if args.force:
        for t in texts:
            p = audio.cache_path(t, 'ko')
            if os.path.exists(p):
                os.remove(p)
    todo = [t for t in texts if not os.path.exists(audio.cache_path(t, 'ko'))]

    print('文本 %d 条，待生成 %d 条，语速 %s，并发 %d'
          % (len(texts), len(todo), audio.TTS_RATE, args.workers))
    if not todo:
        print('全部已缓存，无需联网。')
        return 0

    failed = []
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for text, ok in pool.map(lambda t: one(t, args.retries), todo):
            done += 1
            if not ok:
                failed.append(text)
            if done % 20 == 0 or done == len(todo):
                speed = done / max(time.time() - t0, 1e-6)
                left = (len(todo) - done) / max(speed, 1e-6)
                print('  %d/%d  %.1f 条/秒  剩余约 %.0f 分钟  失败 %d'
                      % (done, len(todo), speed, left / 60, len(failed)),
                      flush=True)

    with open(FAILED_TXT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(failed))
    total = sum(1 for n in os.listdir(audio.CACHE_DIR) if n.endswith('.mp3'))
    size_mb = sum(os.path.getsize(os.path.join(audio.CACHE_DIR, n))
                  for n in os.listdir(audio.CACHE_DIR) if n.endswith('.mp3')) / 1048576
    print('完成：本次成功 %d，失败 %d；缓存共 %d 个文件 / %.1f MB'
          % (len(todo) - len(failed), len(failed), total, size_mb))
    if failed:
        print('失败清单已写入 %s，重跑本脚本即可续传。' % FAILED_TXT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
