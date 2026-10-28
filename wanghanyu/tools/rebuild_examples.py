"""
用 Tatoeba 真实句子替换 data/words.json 里的模板例句。

  python tools/rebuild_examples.py            # 预览，不写文件
  python tools/rebuild_examples.py --write    # 写回（原件备份为 words.json.bak）

取值优先级：
  1. 有普通话译文、句长适中、且该句还没被别的词用过
  2. 只有韩文句（译文留空，卡片会自动不显示那一行）
  3. 没匹配到 -> 保留原模板句，只把 '을/를' 按收音改成正确的一个

匹配用 bigram 倒排索引：1671 个词逐个全表扫 15946 句要 2600 万次子串匹配，
先按二字组取交集把候选压到几十条再验。
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'data', 'corpus')
WORDS = os.path.join(ROOT, 'data', 'words.json')
ATTR = os.path.join(ROOT, 'data', 'attribution', 'tatoeba_used.tsv')

MIN_LEN = 8      # 太短基本等于词条本身
MAX_LEN = 46     # 卡片一行放不下
IDEAL_LEN = 24   # 离这个长度越近越好


def read_tsv(name):
    with open(os.path.join(CORPUS, name), encoding='utf-8') as f:
        for line in f:
            yield line.rstrip('\n').split('\t')


def load_corpus():
    kor = {sid: text for sid, lang, text in read_tsv('kor_sentences.tsv')}
    cmn = {sid: text for sid, lang, text in read_tsv('cmn_sentences.tsv')}
    zh = defaultdict(list)
    for src, trg in read_tsv('kor-cmn_links.tsv'):
        if src in kor and trg in cmn:
            zh[src].append(cmn[trg])
    return kor, zh


def build_index(kor):
    index = defaultdict(set)
    for sid, text in kor.items():
        for i in range(len(text) - 1):
            index[text[i:i + 2]].add(sid)
    return index


def candidates(word, index, kor):
    if len(word) < 2:
        return [sid for sid, t in kor.items() if word in t]
    bigrams = sorted({word[i:i + 2] for i in range(len(word) - 1)},
                     key=lambda g: len(index.get(g, ())))
    pool = set(index.get(bigrams[0], ()))
    for gram in bigrams[1:]:
        pool &= index.get(gram, set())
        if not pool:
            break
    return [sid for sid in pool if word in kor[sid]]


PARTICLE_ONE = set('은는이가을를과와에도만의')
PARTICLE_TWO = {'에서', '에게', '한테', '부터', '까지', '으로', '처럼', '보다', '하고', '에는', '로도'}


def attachment(form, text):
    """词两边接什么：独立成词或接助词 = 真用法；
    左边或右边粘着别的谚文 = 大概率同形异词（名词 가게 撞上动词 가+게，
    가요「歌曲」撞上 흥미로운+가+요），判负。"""
    best = None
    pos = text.find(form)
    while pos != -1:
        rest = text[pos + len(form):]
        prev = text[pos - 1] if pos else ''
        if prev and '가' <= prev <= '힣':
            v = -60
        elif not rest or not ('가' <= rest[0] <= '힣'):
            v = 10
        elif rest[:2] in PARTICLE_TWO:
            v = 25
        elif rest[0] in PARTICLE_ONE:
            v = 20
        else:
            v = -60
        best = v if best is None else max(best, v)
        pos = text.find(form, pos + 1)
    return best if best is not None else -60


def score(word, sid, text, zh_list, used, strict_attach):
    n = len(text)
    if n < MIN_LEN or n > MAX_LEN or text.strip() == word:
        return None
    attach = attachment(word, text)
    if strict_attach and attach < 0:
        return None          # 名词后面接了别的谚文 -> 大概率同形异词
    s = 100 - abs(n - IDEAL_LEN) + max(attach, 0)
    if zh_list:
        s += 500
    if sid in used:
        s -= 400
    return s


def fix_particle(text):
    """把模板里的 '을/를' 按前一个音节有无收音选一个"""
    def pick(m):
        before = text[:m.start()].rstrip()
        if before and 0xAC00 <= ord(before[-1]) <= 0xD7A3:
            return '을' if (ord(before[-1]) - 0xAC00) % 28 else '를'
        return '를'
    return re.sub('을/를', pick, text)


def best_sentence(word, index, kor, zh, used):
    """先按词典形整词匹配；动词/形容词匹配不到就退一步用词干（가르치다 -> 가르치）"""
    forms = [(word, not word.endswith('다'))]
    if word.endswith('다') and len(word) > 2:
        forms.append((word[:-1], False))   # 词干后面接活用词尾，不做助词强判
    for form, strict in forms:
        best = None
        for sid in candidates(form, index, kor):
            text = kor[sid]
            sc = score(form, sid, text, zh.get(sid), used, strict)
            if sc is not None and (best is None or sc > best[0]):
                best = (sc, sid, text)
        if best:
            return best
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--sample', type=int, default=10)
    args = ap.parse_args()

    kor, zh = load_corpus()
    index = build_index(kor)
    with open(WORDS, encoding='utf-8') as f:
        words = json.load(f)

    used = set()
    picked = {}
    stats = {'有译文': 0, '仅韩文': 0, '保留模板': 0, '原数据无效': 0}

    for entry in words:
        w = entry['word']
        best = best_sentence(w, index, kor, zh, used)
        if best:
            _, sid, text = best
            used.add(sid)
            picked[sid] = w
            entry['example'] = text
            entry['example_translation'] = zh[sid][0] if zh.get(sid) else ''
            stats['有译文' if zh.get(sid) else '仅韩文'] += 1
        else:
            old = entry['example'].strip()
            if old == w or len(old) < MIN_LEN:
                entry['example'] = ''          # 原数据里「例句」就是单词本身，丢掉
                entry['example_translation'] = ''
                stats['原数据无效'] += 1
            else:
                entry['example'] = fix_particle(entry['example'])
                entry['example_translation'] = fix_particle(entry['example_translation'])
                stats['保留模板'] += 1

    total = len(words)
    print('词数 %d：%s' % (total, '，'.join('%s %d (%.0f%%)'
          % (k, v, 100 * v / total) for k, v in sorted(stats.items(),
                                                       key=lambda kv: -kv[1]))))
    print('共用到 %d 个不同句子' % len(used))
    print('--- 抽样 ---')
    for entry in words[:args.sample]:
        print('  %-6s | %-30s | %s' % (entry['word'], entry['example'],
                                        entry['example_translation'] or '(无译文)'))

    if args.write:
        shutil.copyfile(WORDS, WORDS + '.bak')
        with open(WORDS, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=2)
        with open(ATTR, 'w', encoding='utf-8') as f:
            f.write('tatoeba_id\tused_by\tkorean\tchinese\n')
            for sid, w in sorted(picked.items(), key=lambda kv: int(kv[0])):
                f.write('%s\t%s\t%s\t%s\n' % (sid, w, kor[sid],
                                              (zh[sid][0] if zh.get(sid) else '')))
        print('已写入 %s（原件备份 words.json.bak）' % WORDS)
        print('CC-BY 署名清单 %s（%d 条）' % (ATTR, len(picked)))
    else:
        print('预览模式，未写文件。加 --write 生效。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
