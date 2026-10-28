"""
字体管理 - 解决中韩文混排

背景：
  Windows 上没有一个字体同时覆盖「简体中文 + 韩文」。
    - malgun.ttf (malgun Gothic)  -> 韩文 100%，简体中文只有 27%（KS X 1001 传统汉字）
    - simhei.ttf (黑体)           -> 简体中文 100%，韩文 0%
  Kivy 的 Label 一个 widget 只能一个 font_name，且没有自动 fallback
  （text_pango 需要 kivy.core.text._text_pango 扩展，这里没装）。

方案：
  中文用 CN_FONT，韩文用 KO_FONT。
  同一段文字里混排时，用 Kivy 的 [font=...] 标记按语种切段，
  这样不需要把 Label 拆成多个，也不用改布局。
"""

# 韩文字体：Malgun Gothic，覆盖全量谚文 + 拉丁 + 少量汉字
# 中文字体：黑体，覆盖全量简体中文 + 拉丁（随项目打包，不依赖系统字体目录）
# 路径走 paths.resource：Android 上字体在 APK 解包目录，不在 cwd
import os

from utils.paths import ANDROID, resource

# Android 系统自带的 CJK 字体候选：AOSP 的 NotoSansCJK 即思源黑体（OFL），
# OEM ROM 一般也带全 CJK 字体。直接引用系统文件：不打包、不下载、无授权问题。
_ANDROID_CJK_CANDIDATES = (
    '/system/fonts/NotoSansCJK-Regular.ttc',
    '/system/fonts/NotoSansKR-Regular.otf',
    '/system/fonts/NotoSansSC-Regular.otf',
    '/system/fonts/MiSans.ttf',
    '/system/fonts/HarmonyOS_SansSC.ttf',
)

# 探测字形：谚文 + 简体 + 韩文常用汉字词用字
_PROBES = (0xD55C, 0xAD6D, 0x8BCD, 0x4E2D)   # 한 국 词 中

_BUNDLED_KO = resource('assets', 'fonts', 'malgun.ttf')
_BUNDLED_CN = resource('assets', 'fonts', 'simhei.ttf')


def _face_tables(fh, base):
    import struct
    fh.seek(base + 4)
    num = struct.unpack('>H', fh.read(2))[0]
    fh.seek(base + 12)
    tables = {}
    for _ in range(num):
        tag, _, off, _len = struct.unpack('>4sIII', fh.read(16))
        tables[tag.decode('latin1')] = off
    return tables


def _subtable_has(fh, off, cp):
    """cmap 子表里有没有这个码点，支持 format 4 和 12"""
    import struct
    fh.seek(off)
    fmt = struct.unpack('>H', fh.read(2))[0]
    if fmt == 12:
        fh.seek(off + 12)
        groups = struct.unpack('>I', fh.read(4))[0]
        for _ in range(groups):
            start, end, _ = struct.unpack('>III', fh.read(12))
            if start <= cp <= end:
                return True
        return False
    if fmt == 4:
        fh.seek(off + 6)
        segx2 = struct.unpack('>H', fh.read(2))[0]
        segs = segx2 // 2
        fh.seek(off + 14)
        ends = struct.unpack('>%dH' % segs, fh.read(segx2))
        fh.seek(off + 16 + segx2)
        starts = struct.unpack('>%dH' % segs, fh.read(segx2))
        for i in range(segs):
            if starts[i] <= cp <= ends[i]:
                return starts[i] != 0xFFFF
        return False
    return False


def _covers_cjk(path):
    """只读 cmap 表做探测，不把整个字体读进内存（系统 ttc 有几十 MB）"""
    import struct
    try:
        with open(path, 'rb') as fh:
            head = fh.read(12)
            bases = [0]
            if head[:4] == b'ttcf':
                n = struct.unpack('>I', head[8:12])[0]
                bases = [struct.unpack('>I', fh.read(4))[0] for _ in range(min(n, 8))]
            for base in bases:
                cmap = _face_tables(fh, base).get('cmap')
                if cmap is None:
                    continue
                fh.seek(cmap + 2)
                nrec = struct.unpack('>H', fh.read(2))[0]
                subs = []
                for _ in range(nrec):
                    pid, eid, soff = struct.unpack('>HHI', fh.read(8))
                    subs.append(cmap + soff)
                if all(any(_subtable_has(fh, s, cp) for s in subs)
                       for cp in _PROBES):
                    return True
            return False
    except OSError:
        return False


def _android_cjk_font():
    for path in _ANDROID_CJK_CANDIDATES:
        if os.path.exists(path) and _covers_cjk(path):
            return path
    return None


if ANDROID:
    _system = _android_cjk_font()
    if _system:
        # 系统字体同时覆盖中韩文，混排切段仍保留但两段同字体
        KO_FONT = CN_FONT = _system
    else:
        # 极端 ROM 没有 CJK 系统字体时退回随包字体，至少不比现在更差
        KO_FONT, CN_FONT = _BUNDLED_KO, _BUNDLED_CN
else:
    # 桌面仅本机开发运行，不随包分发
    KO_FONT, CN_FONT = _BUNDLED_KO, _BUNDLED_CN


def is_hangul(ch):
    """判断字符是否属于韩文（谚文 / 谚文字母 / 半角谚文）"""
    o = ord(ch)
    return (
        0xAC00 <= o <= 0xD7A3      # 谚文音节
        or 0x1100 <= o <= 0x11FF   # 谚文字母
        or 0x3130 <= o <= 0x318F   # 兼容谚文字母
        or 0xFFA0 <= o <= 0xFFDC   # 半角谚文
    )


def is_cjk(ch):
    """判断字符是否属于汉字（含扩展区、兼容汉字）"""
    o = ord(ch)
    return (
        0x3400 <= o <= 0x4DBF      # 扩展 A
        or 0x4E00 <= o <= 0x9FFF   # 基本区
        or 0xF900 <= o <= 0xFAFF   # 兼容汉字
        or 0x20000 <= o <= 0x2FA1F # 扩展 B-F
    )


def escape(text):
    """转义 Kivy markup 的方括号，防止正文里的 [ ] 被当成标签"""
    return text.replace('[', '&bl;').replace(']', '&br;')


def mixed(text, primary=CN_FONT):
    """
    把混排字符串按语种切段，用 [font=...] 标记逐段指定字体。

    primary: 该文本的主要语种字体（CN_FONT 或 KO_FONT）
    返回的每一段都带显式 [font=]，所以不依赖 Label 自身的 font_name。
    """
    if not text:
        return ''

    other = KO_FONT if primary == CN_FONT else CN_FONT

    # 先按语种切段
    segments = []
    for ch in text:
        if primary == CN_FONT:
            font = other if is_hangul(ch) else CN_FONT
        else:
            font = other if is_cjk(ch) else KO_FONT
        if segments and segments[-1][0] == font:
            segments[-1][1].append(ch)
        else:
            segments.append((font, [ch]))

    parts = []
    for font, chars in segments:
        body = escape(''.join(chars))
        parts.append('[font=%s]%s[/font]' % (font, body))
    return ''.join(parts)
