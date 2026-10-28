"""对全部 1671 词跑选项生成，检查是否会出现「两个都对」或选项不足。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from models.quiz import build_options, gloss, tokens

words = json.load(open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8'))

short = 0
overlap = 0
dupgloss = 0
same_pos_total = 0
bad_examples = []
for i, entry in enumerate(words):
    opts = build_options(entry, words, seed=i)
    n = len(opts)
    if n < 4:
        short += 1
    if sum(1 for o in opts if o['is_answer']) != 1:
        bad_examples.append(('答案数不对', entry['word']))
    atk = tokens(entry)
    for o in opts:
        if o['is_answer']:
            continue
        if atk & tokens({'meaning': o['gloss']}):
            overlap += 1
            bad_examples.append(('与答案词元重叠', entry['word'], o['word'], o['gloss']))
    gl = [o['gloss'] for o in opts]
    if len(set(gl)) != len(gl):
        dupgloss += 1
    for a in range(len(opts)):
        for b in range(a + 1, len(opts)):
            if tokens({'meaning': opts[a]['gloss']}) & tokens({'meaning': opts[b]['gloss']}):
                overlap += 1
                bad_examples.append(('干扰项互撞', entry['word'], opts[a]['gloss'], opts[b]['gloss']))

print('词数 %d' % len(words))
print('选项不足 4 个的题: %d' % short)
print('任意两项词元重叠: %d' % overlap)
print('出现完全相同释义的题: %d' % dupgloss)
print('异常样例: %s' % (bad_examples[:5] or '无'))

print('\n--- 抽样题目 ---')
for w in ['가게', '먹다', '그것', '이것', '보다']:
    entry = next((x for x in words if x['word'] == w), None)
    if not entry:
        continue
    opts = build_options(entry, words, seed=7)
    print('%s [%s] 释义=%s' % (w, entry.get('pos_cn') or '无词性', gloss(entry)))
    for letter, o in zip('ABCD', opts):
        print('   %s. %s%s' % (letter, o['gloss'], '   <- 正确' if o['is_answer'] else ''))
