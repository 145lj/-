"""
用 konlpy 自带的 kE 系统词典（28.4 万条，Apache-2.0）给 words.json 补词性。

不联网，避开了 krdict 的 IP 限流。

  python tools/pos_from_konlpy.py --wheel /tmp/konlpy/konlpy-0.6.0-py2.py3-none-any.whl
  python tools/pos_from_konlpy.py --write
"""
import argparse
import json
import os
import sys
import zipfile
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = os.path.join(ROOT, 'data', 'words.json')
LEXICON = os.path.join(ROOT, 'data', 'lexicon', 'kE_dic_system.txt')

# KIBSTAGS 前缀 -> 中文词性，按优先级排列
TAG_CN = [
    ('pv', '动词'), ('pa', '形容词'), ('xa', '形容词'), ('xv', '动词'),
    ('mag', '副词'), ('mab', '副词'), ('maj', '副词'),
    ('np', '代名词'), ('num', '数词'), ('mm', '冠形词'),
    ('n', '名词'),
]


def tag_to_cn(tag):
    for prefix, cn in TAG_CN:
        if tag.startswith(prefix):
            return cn
    return ''


def ensure_lexicon(wheel):
    if os.path.exists(LEXICON):
        return LEXICON
    if not wheel or not os.path.exists(wheel):
        raise SystemExit('找不到词典，也没有 wheel 可解：%r' % wheel)
    os.makedirs(os.path.dirname(LEXICON), exist_ok=True)
    with zipfile.ZipFile(wheel) as z:
        data = z.read('konlpy/java/data/kE/dic_system.txt')
    with open(LEXICON, 'wb') as f:
        f.write(data)
    print('已解压词典 ->', LEXICON)
    return LEXICON


def load_lexicon(path):
    """词形 -> {中文词性, ...}"""
    table = defaultdict(set)
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 2 or not parts[1]:
                continue
            cn = tag_to_cn(parts[1])
            if cn:
                table[parts[0]].add(cn)
    return table


def pos_of(word, table):
    """kE 词典只存裸词干，不存 가다 这种词典形，所以 다 结尾要单独走。

    判定顺序（宁缺毋滥，猜错词性比不标更糟）：
      1. 词干带 pv/pa 标签 -> 动词/形容词（걷다->걷/pvg）
      2. 否则留空。整词查表对 다 词不可用：库里 오다/잡다/붓다 都是同形名词，
         바다 这类真名词又只有个位数，用整词形判名词错得多、对得少。
      3. 非 다 词直接查整词形。
    """
    if word.endswith('다') and len(word) > 1:
        stem = table.get(word[:-1]) or set()
        for prefer in ('动词', '形容词'):
            if prefer in stem:
                return prefer, 'stem'
        return '', ''
    hits = table.get(word)
    if hits:
        for _, cn in TAG_CN:
            if cn in hits:
                return cn, 'exact'
    return '', ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wheel', default='')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--sample', type=int, default=12)
    ap.add_argument('--all', action='store_true', help='重算所有词（含已标过词性的）')
    args = ap.parse_args()

    table = load_lexicon(ensure_lexicon(args.wheel))
    print('词典词形数 %d' % len(table))

    with open(WORDS, encoding='utf-8') as f:
        words = json.load(f)

    keep = {id(w) for w in words if w.get('pos_source', '').startswith('krdict')}
    if args.all:                      # 重算时先清掉旧结果，否则误标的会残留
        for w in words:
            if id(w) not in keep:
                w.pop('pos_cn', None)
                w.pop('pos_source', None)
    todo = [w for w in words if args.all or not w.get('pos_cn')]
    todo = [w for w in todo if id(w) not in keep]
    stats = defaultdict(int)
    shown = 0
    for entry in todo:
        cn, how = pos_of(entry['word'], table)
        if cn:
            entry['pos_cn'] = cn
            entry['pos_source'] = 'konlpy-kE:' + how
            stats['命中-' + how] += 1
            if shown < args.sample:
                print('  %-8s -> %s (%s)  释义=%s'
                      % (entry['word'], cn, how, entry['meaning']))
                shown += 1
        else:
            stats['未命中'] += 1

    print('待补 %d：%s，未命中 %d'
          % (len(todo), '，'.join('%s %d' % (k.replace('命中-', ''), v)
                                  for k, v in sorted(stats.items()) if k != '未命中'),
             stats['未命中']))
    if args.write:
        tmp = WORDS + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=2)
        os.replace(tmp, WORDS)
        print('已写回 %s' % WORDS)
    else:
        print('预览模式，加 --write 生效')
    return 0


if __name__ == '__main__':
    sys.exit(main())
