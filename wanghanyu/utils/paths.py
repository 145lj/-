"""
路径解析 - 桌面与 Android 各一套

桌面：资源与可写数据都是项目目录，方便直接改 words.json、看 progress.json。
Android：APK 解包目录只读（字体、words.json、预生成音频都从那儿读），
         运行期产生的状态写到应用私有目录。
"""
import os

from kivy.utils import platform

ANDROID = platform == 'android'

# 项目根目录：utils/ 的上一级，与启动时的 cwd 无关
RESOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANDROID:
    # p4a 把整个应用解包到这里；环境变量缺失时退回项目根（仅桌面语义）
    RESOURCE_DIR = os.environ.get('ANDROID_APP_PATH', RESOURCE_DIR)

_writable = None


def resource(*parts):
    """随包分发的只读资源"""
    return os.path.join(RESOURCE_DIR, *parts)


def writable(*parts):
    """运行期可写目录，父目录按需创建"""
    global _writable
    if _writable is None:
        if ANDROID:
            from kivy.app import App
            app = App.get_running_app()
            _writable = app.user_data_dir if app else os.environ.get(
                'ANDROID_PRIVATE', RESOURCE_DIR)
        else:
            _writable = RESOURCE_DIR
    path = os.path.join(_writable, *parts)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path
