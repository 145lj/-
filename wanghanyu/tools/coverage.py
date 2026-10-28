"""
量一下 Tatoeba 语料对现有 1671 词的覆盖率，决定例句替换策略。
"""
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'data', 'corpus')


def read_tsv(name):
    with open(os.path.join(CORPUS, name), encoding='utf-8') as f:
        for line in f:
            yield line.rstrip('\n').split('\t')


kor_text = {sid: text for sid, lang, text in read_tsv('kor_sentences.tsv')}
cmn_text = {sid: text for sid, lang, text in read_tsv('cmn_sentences.tsv')}
pairs = [(s, t) for s, t in read_tsv('kor-cmn_links.tsv') if s in kor_text]

with_zh = defaultdict(list)
for s, t in pairs:
    if t in cmn_text:
        with_zh[s].append(cmn_text[t])

words = [w['word'] for w in json.load(open(os.path.join(ROOT, 'data', 'words.json'),
                                           encoding='utf-8'))]

all_kor = list(kor_text.values())
zh_kor = {s: kor_text[s] for s in with_zh}

hit_any = hit_zh = 0
for w in words:
    if any(w in s for s in all_kor):
        hit_any += 1
    if any(w in s for s in zh_kor.values()):
        hit_zh += 1

print('词数 %d' % len(words))
print('能被任意韩语句覆盖: %d (%.0f%%)' % (hit_any, 100 * hit_any / len(words)))
print('能被「带普通话译文」的句子覆盖: %d (%.0f%%)' % (hit_zh, 100 * hit_zh / len(words)))
print('韩语句总数 %d，其中有中文译文的 %d' % (len(kor_text), len(zh_kor)))
