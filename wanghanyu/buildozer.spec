# buildozer 配置：在 wanghanyu/ 目录执行 `buildozer android debug`
# 路径均相对本文件所在的 wanghanyu/ 目录
#
# 免打包的字体：msyh.ttc / simsun.ttc 只是 font_test.py 的实验素材，
# utils/fonts.py 的桌面回退只用 simhei/malgun；Android 上运行时直接探测
# /system/fonts 里的系统 CJK 字体，这两个 19MB/18MB 的文件不进 APK。

[app]
title = 汪韩语
package.name = wanghanyu
package.domain = org.wanghanyu
version = 0.1.0

source.dir = .
source.include_exts = py,kv,json,png,ttf,mp3
source.exclude_exts = bak
source.exclude_dirs = tests, bin, __pycache__, data/lexicon, data/试听, tools
source.exclude_patterns = data/krdict_key.txt,data/progress.json,data/words.json.bak,data/words.json.pre-krdict.bak,data/attribution/used_sentences.tsv.html,data/tts/_failed.txt,_edge_0.mp3,fonttest*.png,assets/kv/main.kv.backup,assets/fonts/msyh.ttc,assets/fonts/simsun.ttc

# charset-normalizer 3.4+ 在 PyPI 发布了 android 二进制 wheel，
# p4a 会下载它但宿主 pip 拒绝安装（p4a issue #2755），钉到纯 Python 版本绕开
requirements = python3,kivy==2.3.1,charset-normalizer==3.3.2

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/assets/icon.png

android.archs = arm64-v8a
android.api = 34
android.minapi = 24
android.accept_sdk_license = True
android.permissions = INTERNET
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 0
