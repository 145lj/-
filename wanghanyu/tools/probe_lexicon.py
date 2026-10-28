"""定位 pos_of 的 bug，并统计 X하다 类的可判定性。"""
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.pos_from_konlpy import load_lexicon, pos_of, LEXICON   # noqa

tags_of = defaultdict(set)
with open(LEXICON, encoding='utf-8', errors='replace') as f:
    for line in f:
        parts = line.rstrip('\n').split('\t')
        if len(parts) >= 2 and parts[1]:
            tags_of[parts[0]].add(parts[1])

table = load_lexicon(LEXICON)

print('=== pos_of 直接调用 ===')
for w in ['걷다', '깎다', '넣다', '높다', '굽다', '넓다']:
    stem = w[:-1]
    print('  %-5s table[stem]=%s  raw_tags=%s  pos_of=%s'
          % (w, sorted(table.get(stem) or []), sorted(tags_of.get(stem) or []),
             pos_of(w, table, {})))

words = json.load(open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8'))
un = [w for w in words if w['word'].endswith('다') and not w.get('pos_cn')]

ha = [w for w in un if w['word'].endswith('하다')]
print('\n=== X하다 类 %d 个（占未判 %d 的 %.0f%%）===' % (len(ha), len(un), 100 * len(ha) / len(un)))
noun_ok = 0
for w in ha:
    base = w['word'][:-2]          # 걱정하다 -> 걱정
    if tags_of.get(base):
        noun_ok += 1
print('  其中 X 本身在库里有词条的: %d' % noun_ok)
print('  样例:', ' '.join(w['word'] for w in ha[:15]))

polite = [w for w in un if w['word'].endswith(('습니다', 'ㅂ니다', '세요', '예요', '이에요'))]
print('\n=== 敬语/活用形（非词典形）%d 个 ===' % len(polite))
print('  ', ' '.join(w['word'] for w in polite))

rest = [w for w in un if not w['word'].endswith('하다')
        and w not in polite]
print('\n=== 其余 %d 个 ===' % len(rest))
print('  ', ' '.join(w['word'] for w in rest))
