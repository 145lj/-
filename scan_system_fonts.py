"""Scan all system fonts for one that covers BOTH simplified Chinese and Hangul."""
import os
import glob
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_fonts import font_chars  # noqa

CJK = '韩语学习开始认识记点击卡片翻转从万与东丽书写'
HANG = '가게한국어'
LAT = 'abcXYZ'

dirs = [r'C:\Windows\Fonts', r'C:\Users\李冠勋\AppData\Local\Microsoft\Windows\Fonts']
found = []
allf = []
for d in dirs:
    for p in glob.glob(os.path.join(d, '*')):
        if os.path.splitext(p)[1].lower() in ('.ttf', '.ttc', '.otf', '.ttc'):
            allf.append(p)

for p in allf:
    try:
        chars, err = font_chars(p)
    except Exception:
        continue
    if err or not chars:
        continue
    c_ok = sum(1 for ch in CJK if ord(ch) in chars)
    h_ok = sum(1 for ch in HANG if ord(ch) in chars)
    l_ok = sum(1 for ch in LAT if ord(ch) in chars)
    c_pct = c_ok / len(CJK)
    h_pct = h_ok / len(HANG)
    tag = ''
    if c_pct >= 0.999 and h_pct >= 0.999:
        tag = '  <<< BOTH FULL'
        found.append(p)
    elif c_pct >= 0.999:
        tag = '  [cjk]'
    elif h_pct >= 0.999:
        tag = '  [hangul]'
    if c_pct > 0.5 or h_pct > 0.5:
        print('%-60s cjk=%.0f%% hangul=%.0f%% lat=%.0f%%%s' % (
            os.path.basename(p), c_pct * 100, h_pct * 100, l_ok / len(LAT) * 100, tag))

print('\n=== fonts covering BOTH simplified Chinese AND Hangul ===')
if found:
    for p in found:
        print(' ', p)
else:
    print('  NONE')
