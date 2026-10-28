"""Analyze data layout + Kivy font capabilities. Writes UTF-8 report."""
import json
import os
import re
import sys
import kivy

OUT = []
def p(*a):
    OUT.append(' '.join(str(x) for x in a))

# ---------- 1. Kivy label capabilities ----------
kdir = os.path.dirname(kivy.__file__)
label_py = os.path.join(kdir, 'widgets', 'label.py')
p('kivy dir:', kdir)
p('label.py exists:', os.path.exists(label_py))
if os.path.exists(label_py):
    src = open(label_py, encoding='utf-8').read()
    for kw in ('font_family', 'font_context', 'font_name', 'fallback'):
        hits = [ln.strip() for ln in src.splitlines() if kw in ln]
        p('  %-14s -> %d hit(s)' % (kw, len(hits)))
        for h in hits[:4]:
            p('       ', h[:110])

# pango provider availability
try:
    import kivy.core.text.text_pango as tp
    p('pango module import: OK')
except Exception as e:
    p('pango module import: FAIL ->', type(e).__name__, str(e)[:120])

# ---------- 2. data layout ----------
root = r'D:\Projects\WangHanyu\wanghanyu'
words = json.load(open(os.path.join(root, 'data', 'words.json'), encoding='utf-8'))
p('')
p('words:', len(words), 'keys:', list(words[0].keys()))
p('sample[0]:', json.dumps(words[0], ensure_ascii=False))

han = re.compile(r'[\u3400-\u9fff]')
hang = re.compile(r'[\uac00-\ud7af]')
jamo = re.compile(r'[\u1100-\u11ff\u3130-\u318f]')

p('')
p('--- per-field language composition (over all %d words) ---' % len(words))
for k in ('word', 'romanization', 'meaning', 'example', 'example_translation'):
    vals = [w.get(k, '') or '' for w in words]
    c = sum(1 for v in vals if han.search(v))
    h = sum(1 for v in vals if hang.search(v))
    j = sum(1 for v in vals if jamo.search(v))
    both = sum(1 for v in vals if han.search(v) and (hang.search(v) or jamo.search(v)))
    p('  %-20s nonempty=%-5d cjk=%-5d hangul=%-5d jamo=%-4d MIXED_CJK+HANGUL=%d'
      % (k, sum(1 for v in vals if v.strip()), c, h, j, both))

p('')
p('--- fields whose value contains BOTH CJK and Hangul (sample 5) ---')
n = 0
for w in words:
    for k in ('word', 'meaning', 'example', 'example_translation'):
        v = w.get(k) or ''
        if han.search(v) and (hang.search(v) or jamo.search(v)):
            p('  %s / %s : %r' % (w.get('id'), k, v))
            n += 1
            break
    if n >= 5:
        break
if n == 0:
    p('  (none)')

# ---------- 3. full character inventory ----------
p('')
p('--- full charset needed ---')
allchars = set()
for w in words:
    for k in ('word', 'romanization', 'meaning', 'example', 'example_translation'):
        allchars |= set(w.get(k) or '')
ui_text = '汪韩语韩语学习，从汪开始！开始学习点击卡片翻转第个认识模糊忘记学习完成！连续学习：返回主页'
allchars |= set(ui_text)
cjk_all = {c for c in allchars if han.match(c)}
hang_all = {c for c in allchars if hang.match(c) or jamo.match(c)}
p('total distinct chars:', len(allchars), '| CJK:', len(cjk_all), '| Hangul/Jamo:', len(hang_all))
p('CJK sample:', ''.join(sorted(cjk_all))[:120])

# save charset for subsetting
with open(r'D:\Projects\WangHanyu\charset.txt', 'w', encoding='utf-8') as f:
    f.write(''.join(sorted(allchars)))

with open(r'D:\Projects\WangHanyu\report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(OUT))
print('report written')
