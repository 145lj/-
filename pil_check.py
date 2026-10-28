"""Cross-check glyph availability by RENDERING (PIL) instead of parsing cmap.
A char is 'missing' if it renders identically to a private-use char (.notdef box).
"""
import os
from PIL import Image, ImageDraw, ImageFont

FONTS = {
    'malgun': r'D:\Projects\WangHanyu\wanghanyu\assets\fonts\malgun.ttf',
    'msyh':   r'D:\Projects\WangHanyu\wanghanyu\assets\fonts\msyh.ttc',
    'simhei': r'D:\Projects\WangHanyu\wanghanyu\assets\fonts\simhei.ttf',
    'simsun': r'D:\Projects\WangHanyu\wanghanyu\assets\fonts\simsun.ttc',
}

CHARS = [
    ('한글', '\uac00'),   # 가
    ('한글', '\uac8c'),   # 게
    ('한글', '\ud55c'),   # 한
    ('简体', '\u6c49'),   # 汉
    ('简体', '\u4e60'),   # 习
    ('简体', '\u5b66'),   # 学
    ('繁體', '\u6f22'),   # 漢
    ('emoji', '\U0001f50a'),  # speaker
    ('音符', '\u266a'),   # ♪
    ('播放', '\u25b6'),   # ▶
    ('圆点', '\u25cf'),   # ●
    ('箭頭', '\u2192'),   # →
]

PUA = '\ue123'  # private use -> guaranteed .notdef


def render_sig(font, ch):
    m = font.getmask(ch, mode='L')
    return (m.size, bytes(m))


out = []
for name, path in FONTS.items():
    if not os.path.exists(path):
        out.append('%s MISSING' % name)
        continue
    try:
        f = ImageFont.truetype(path, 48)
    except Exception as e:
        out.append('%s LOAD FAIL: %s' % (name, e))
        continue
    notdef = render_sig(f, PUA)
    row = []
    for label, ch in CHARS:
        try:
            sig = render_sig(f, ch)
        except Exception as e:
            row.append('%s:%s=ERR' % (label, ch))
            continue
        is_td = (sig[0] == notdef[0] and sig[1] == notdef[1])
        row.append('%s%s=%s' % (label, ch, 'TOFU' if is_td else 'ok'))
    out.append('%-7s %s' % (name, '  '.join(row)))

with open(r'D:\Projects\WangHanyu\pil_check.txt', 'w', encoding='utf-8') as fp:
    fp.write('\n'.join(out))
print('done')
