"""扫描 words.json 里 malgun+simhei 两种字体都覆盖不到的字符。"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

HANGUL = set(range(0x1100, 0x11FF)) | set(range(0x3130, 0x3190)) \
    | set(range(0xA960, 0xA980)) | set(range(0xAC00, 0xD7B0)) | set(range(0xFFA0, 0xFFDE))
CJK = set(range(0x3400, 0x4DC0)) | set(range(0x4E00, 0xA000)) | set(range(0xF900, 0xFAFF))
SAFE_LATIN = set(range(0x20, 0x7F))
SAFE_PUNCT = set('，。、！？：；（）「」『』…—·％℃°±×÷≤≥≠≈"\'-_/\\&@#*+=<>[]{}|^~$€£¥₩')


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    words = json.load(open(os.path.join(root, 'data', 'words.json'), encoding='utf-8'))
    bad = Counter()
    where = {}
    for entry in words:
        for field in ('word', 'meaning', 'example', 'example_translation', 'romanization'):
            for ch in entry.get(field) or '':
                o = ord(ch)
                if o in HANGUL or o in CJK or o in SAFE_LATIN or ch in SAFE_PUNCT or ch in '\n':
                    continue
                bad[ch] += 1
                where.setdefault(ch, '%s/%s' % (entry['word'], field))
    if not bad:
        print('全部字符都在两种字体覆盖范围内。')
        return 0
    print('发现 %d 种字体覆盖不到的字符：' % len(bad))
    for ch, n in bad.most_common(30):
        print('  %r U+%04X  %d 处  例: %s' % (ch, ord(ch), n, where[ch]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
