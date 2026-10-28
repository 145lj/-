"""Check CJK/Hangul glyph coverage of local fonts (pure-python cmap parser)."""
import struct
import sys
import os

FONTS = [
    r'D:\Projects\WangHanyu\wanghanyu\assets\fonts\malgun.ttf',
    r'D:\Projects\WangHanyu\wanghanyu\assets\fonts\msyh.ttc',
    r'D:\Projects\WangHanyu\wanghanyu\assets\fonts\simhei.ttf',
    r'D:\Projects\WangHanyu\wanghanyu\assets\fonts\simsun.ttc',
    r'C:\Windows\Fonts\malgun.ttf',
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\msyhbd.ttc',
    r'C:\Windows\Fonts\simhei.ttf',
    r'C:\Windows\Fonts\simsun.ttc',
    r'C:\Windows\Fonts\Deng.ttf',
]

PROBES = {
    'CJK_simp': '韩语学习开始认识记点击卡片翻转韩语学习从开始',
    'CJK_same': '汪始模糊忘汪始模糊忘',
    'HANGUL': '가게한국어',
    'HANGUL_JAMO': '한국',
    'LATIN': 'abcXYZ019',
    'PUNCT': '，。！、',
}


def read_tables(data, offset):
    num_tables = struct.unpack('>H', data[offset + 4:offset + 6])[0]
    tables = {}
    for i in range(num_tables):
        rec = offset + 12 + i * 16
        tag = data[rec:rec + 4].decode('latin-1')
        toff, tlen = struct.unpack('>II', data[rec + 8:rec + 16])
        tables[tag] = (toff, tlen)
    return tables


def parse_cmap(data, tables):
    if 'cmap' not in tables:
        return set()
    coff, _ = tables['cmap']
    n = struct.unpack('>H', data[coff + 2:coff + 4])[0]
    best = None
    for i in range(n):
        rec = coff + 4 + i * 8
        pid, eid, sub_off = struct.unpack('>HHI', data[rec:rec + 8])
        fmt = struct.unpack('>H', data[coff + sub_off:coff + sub_off + 2])[0]
        unicode_sub = (pid == 3 and eid in (1, 10)) or pid == 0
        if unicode_sub:
            if best is None or fmt == 12:
                best = coff + sub_off
    if best is None:
        return set()

    chars = set()
    fmt = struct.unpack('>H', data[best:best + 2])[0]
    if fmt == 4:
        seg_x2 = struct.unpack('>H', data[best + 6:best + 8])[0]
        seg = seg_x2 // 2
        ends = struct.unpack('>%dH' % seg, data[best + 14:best + 14 + seg_x2])
        sbase = best + 16 + seg_x2
        starts = struct.unpack('>%dH' % seg, data[sbase:sbase + seg_x2])
        dbase = sbase + seg_x2
        deltas = struct.unpack('>%dh' % seg, data[dbase:dbase + seg_x2])
        rbase = dbase + seg_x2
        ranges = struct.unpack('>%dH' % seg, data[rbase:rbase + seg_x2])
        for i in range(seg):
            for c in range(starts[i], min(ends[i], 0xFFFF) + 1):
                if c == 0xFFFF:
                    continue
                if ranges[i] == 0:
                    g = (c + deltas[i]) & 0xFFFF
                else:
                    gi = rbase + i * 2 + ranges[i] + (c - starts[i]) * 2
                    if gi + 2 > len(data):
                        continue
                    g = struct.unpack('>H', data[gi:gi + 2])[0]
                    if g:
                        g = (g + deltas[i]) & 0xFFFF
                if g:
                    chars.add(c)
    elif fmt == 12:
        ngroups = struct.unpack('>I', data[best + 12:best + 16])[0]
        for i in range(ngroups):
            rec = best + 16 + i * 12
            sc, ec, sg = struct.unpack('>III', data[rec:rec + 12])
            for c in range(sc, min(ec, sc + 0x20000) + 1):
                chars.add(c)
    return chars


def font_chars(path):
    with open(path, 'rb') as f:
        data = f.read()
    tag = data[:4]
    offsets = []
    if tag == b'ttcf':
        n = struct.unpack('>I', data[8:12])[0]
        offsets = list(struct.unpack('>%dI' % n, data[12:12 + n * 4]))
    else:
        offsets = [0]
    all_chars = set()
    for off in offsets:
        try:
            tables = read_tables(data, off)
            all_chars |= parse_cmap(data, tables)
        except Exception as e:
            return set(), str(e)
    return all_chars, None


for path in FONTS:
    if not os.path.exists(path):
        print('%-70s MISSING' % path)
        continue
    chars, err = font_chars(path)
    if err:
        print('%-70s ERROR %s' % (path, err))
        continue
    res = []
    for name, probe in PROBES.items():
        have = sum(1 for ch in probe if ord(ch) in chars)
        res.append('%s=%d/%d' % (name, have, len(probe)))
    size = os.path.getsize(path)
    print('%-70s %6.1fMB  %s' % (path, size / 1048576, '  '.join(res)))
