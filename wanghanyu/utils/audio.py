"""
语音播放 - 后台线程合成，主线程只播放，绝不阻塞界面

要点：
  1. TTS 是同步网络请求，直接在 Kivy 主线程里调会把事件循环卡死，
     所以合成一律丢到 daemon 线程，缓存好了再回主线程播放。
  2. 缓存文件名用 sha1，不用内置 hash()——后者每进程随机化，缓存等于没有。
  3. 优先 edge-tts（微软 neural，语速可调），失败再退回 gTTS。
     两者都要联网；命中 data/tts/ 缓存则完全离线。
  4. requests 只读 HTTP(S)_PROXY，aiohttp 连环境变量都不读，
     所以代理一律从 Windows 注册表取，显式传给两边。
  5. Android 上只播放随包分发的缓存音频：APK 内只读、不联网合成，
     解码用系统 MediaPlayer（mp3 是 Android 原生格式），避免 SDL2_mixer
     在部分机型上解不了 mp3 导致 SoundLoader.load 返回 None。
"""
import hashlib
import os
import re
import threading

from kivy.clock import Clock
from kivy.core.audio import SoundLoader

from utils.paths import ANDROID, resource

CACHE_DIR = resource('data', 'tts')

# 语速：edge-tts 的 rate，'+0%' 即该 neural 声音的自然语速
TTS_RATE = '+0%'
# 每种语言用哪个 neural 声音；不在表里的语言直接走 gTTS
TTS_VOICES = {'ko': 'ko-KR-SunHiNeural'}

_busy = set()         # 正在后台合成的 key
_lock = threading.Lock()


if ANDROID:
    from jnius import autoclass
    _MediaPlayer = autoclass('android.media.MediaPlayer')

    class _Backend:
        """系统 MediaPlayer：硬件解码，不往 APK 里塞 ffmpeg"""

        def __init__(self):
            self._player = None

        def play(self, path):
            self.stop()
            try:
                player = _MediaPlayer()
                player.setDataSource(path)
                player.prepare()
                player.start()
            except Exception as e:
                print('MediaPlayer 失败(%s): %r' % (path, e))
                self.stop()
                return False
            self._player = player
            return True

        def stop(self):
            if self._player is None:
                return
            for method in ('stop', 'release'):
                try:
                    getattr(self._player, method)()
                except Exception:
                    pass
            self._player = None
else:
    class _Backend:
        """桌面走 Kivy SoundLoader，同一条音频复用已解码对象"""

        def __init__(self):
            self._sound = None
            self._path = None

        def play(self, path):
            if self._sound is None or self._path != path:
                self.stop()
                self._sound = SoundLoader.load(path)
                self._path = path
                if self._sound is None:
                    return False
            if self._sound.state == 'play':
                self._sound.stop()
            self._sound.play()
            return True

        def stop(self):
            if self._sound is not None:
                try:
                    self._sound.stop()
                    self._sound.unload()
                except Exception:
                    pass
            self._sound = None
            self._path = None


_backend = _Backend()


def system_proxy_url():
    """从注册表读系统代理，返回 http://host:port 或 None"""
    env = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
    if env:
        return env
    try:
        import winreg
        key = r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
        h = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key)
        if not winreg.QueryValueEx(h, 'ProxyEnable')[0]:
            return None
        server = winreg.QueryValueEx(h, 'ProxyServer')[0]
    except (OSError, ImportError):
        return None
    if not server or '=' in server:
        return None
    return server if '://' in server else 'http://' + server


def cache_path(text, lang):
    """文件名把语速编进哈希：改 TTS_RATE 会生成另一套缓存而不是覆盖，便于试听对比"""
    key = hashlib.sha1(('%s\x00%s\x00%s' % (lang, text, TTS_RATE)).encode('utf-8'))
    return os.path.join(CACHE_DIR, '%s_%s.mp3' % (lang, key.hexdigest()[:16]))


_PARTICLE = re.compile('을/를')


def _has_batchim(ch):
    """谚文音节是否带收音"""
    o = ord(ch)
    return 0xAC00 <= o <= 0xD7A3 and (o - 0xAC00) % 28 != 0


def speakable(text):
    """把 '을/를' 按前一个音节的收音选成正确的那一个，否则 TTS 会照念斜杠"""
    def pick(m):
        before = text[:m.start()].rstrip()
        return '을' if before and _has_batchim(before[-1]) else '를'
    return _PARTICLE.sub(pick, text)


def _edge_synth(text, lang, tmp):
    import asyncio
    import edge_tts
    proxy = system_proxy_url()
    kwargs = {'proxy': proxy} if proxy else {}

    async def stream():
        communicate = edge_tts.Communicate(
            text, voice=TTS_VOICES[lang], rate=TTS_RATE, **kwargs)
        with open(tmp, 'wb') as f:
            async for chunk in communicate.stream():
                if chunk.get('type') == 'audio':
                    f.write(chunk['data'])

    asyncio.run(stream())


def _gtts_synth(text, lang, tmp):
    os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = system_proxy_url() or ''
    from gtts import gTTS
    gTTS(text=text, lang=lang).save(tmp)


def fetch(text, lang='ko'):
    """同步合成并写入缓存，返回文件路径；失败返回 None。
    只能在工作线程里调用（会阻塞）。批量预生成脚本也用它。"""
    path = cache_path(text, lang)
    if os.path.exists(path):
        return path
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = path + '.part'
    engines = []
    if lang in TTS_VOICES:
        engines.append(_edge_synth)
    engines.append(_gtts_synth)
    for engine in engines:
        try:
            engine(text, lang, tmp)
            if os.path.getsize(tmp) > 0:
                os.replace(tmp, path)
                return path
        except Exception as e:
            print('%s 失败(%s): %r' % (engine.__name__, text, e))
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    return None


def _synthesize(text, lang):
    """后台线程入口：合成完成后回主线程加载播放"""
    ok = fetch(text, lang) is not None
    Clock.schedule_once(lambda dt: _on_synthesized(text, lang, ok), 0)


def _on_synthesized(text, lang, ok):
    _busy.discard((text, lang))
    if not ok:
        AudioPlayer._notify(text, 'failed')
        return
    AudioPlayer._notify(text, 'ready')
    if AudioPlayer.autoplay and AudioPlayer.last_requested == (text, lang):
        if not _backend.play(cache_path(text, lang)):
            AudioPlayer._notify(text, 'failed')


class AudioPlayer:
    autoplay = True
    last_requested = None
    on_status = None      # (text, state) -> None，state: synthesizing / ready / failed

    @classmethod
    def speak(cls, text, lang='ko'):
        text = speakable(text)
        if not text:
            return
        cls.last_requested = (text, lang)

        path = cache_path(text, lang)
        if os.path.exists(path):
            if not _backend.play(path):
                cls._notify(text, 'failed')
            return

        if ANDROID:
            # 手机上不联网合成：既没有网络保证，注册表代理探测也不存在
            cls._notify(text, 'failed')
            return

        with _lock:
            start = (text, lang) not in _busy
            if start:
                _busy.add((text, lang))
        if start:
            threading.Thread(target=_synthesize, args=(text, lang),
                             daemon=True).start()
            cls._notify(text, 'synthesizing')

    @classmethod
    def _notify(cls, text, state):
        if cls.on_status:
            cls.on_status(text, state)
