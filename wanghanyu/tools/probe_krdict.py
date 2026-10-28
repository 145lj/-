"""复现 enrich_words 的高错误率：同一批词分别串行和并发查，打印真实异常。"""
import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from utils.krdict import lookup

words = json.load(open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8'))
todo = [w['word'] for w in words if not w.get('pos_cn')][:10]


def probe(word):
    try:
        hit = lookup(word)
        return word, 'ok' if hit else 'miss'
    except Exception as e:
        return word, '%s: %s' % (type(e).__name__, str(e)[:110])


print('--- 串行 ---')
for r in map(probe, todo):
    print(' ', r[0], r[1])

print('--- 并发 4 ---')
with ThreadPoolExecutor(max_workers=4) as pool:
    for r in pool.map(probe, todo):
        print(' ', r[0], r[1])
