"""
词条块：词性＋中文释义（左侧竖色条）/ 分隔线 / 例句小节 / 韩文例句＋独立播放按钮 / 中文译文

从 flip_card 里抽出来，是为了让「翻转卡片」和「四选一背词」共用同一份词条视图，
不至于两处各写一遍排版。
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, ColorProperty
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle

from utils.fonts import CN_FONT, KO_FONT, mixed
from screens.zh_button import ZhButton

ACCENT = (0.85, 0.55, 0.13, 1)      # 释义块左侧竖条
DIVIDER = (0.86, 0.84, 0.78, 1)
INK = (0.12, 0.12, 0.16, 1)
SUBTLE = (0.45, 0.45, 0.5, 1)


class WrapLabel(Label):
    """按宽度折行、高度随内容自适应，用于左对齐的多行文本"""

    def __init__(self, **kwargs):
        kwargs.setdefault('halign', 'left')
        kwargs.setdefault('valign', 'top')
        kwargs.setdefault('markup', True)
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.bind(size=self._sync, texture_size=self._sync)

    def _sync(self, *args):
        self.text_size = (self.width, None)
        self.height = max(self.texture_size[1], 18)


class AccentBar(Widget):
    """释义块左侧那条竖线，高度跟随所在行"""
    color = ColorProperty(ACCENT)

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (None, 1))
        kwargs.setdefault('width', '3dp')
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*self.color)
            Rectangle(pos=self.pos, size=self.size)


class Divider(Widget):
    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', '1dp')
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*DIVIDER)
            Rectangle(pos=self.pos, size=self.size)


class EntryPanel(BoxLayout):
    word = StringProperty('')
    pos_cn = StringProperty('')
    meaning = StringProperty('')
    example = StringProperty('')
    example_translation = StringProperty('')

    def __init__(self, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('spacing', '10dp')
        kwargs.setdefault('padding', '16dp')
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))

        self._meaning_row = BoxLayout(orientation='horizontal', spacing='10dp',
                                      size_hint_y=None, height=dp(26))
        self._meaning_row.add_widget(AccentBar())
        self._meaning_label = WrapLabel(font_name=CN_FONT, font_size='19sp', color=INK)
        self._meaning_label.bind(height=self._sync_meaning_row)
        self._meaning_row.add_widget(self._meaning_label)
        self.add_widget(self._meaning_row)

        self._divider = Divider()
        self.add_widget(self._divider)

        self._header = WrapLabel(text=mixed('例句'), font_name=CN_FONT,
                                 font_size='13sp', color=SUBTLE)
        self.add_widget(self._header)

        self._example_row = BoxLayout(orientation='horizontal', spacing='8dp',
                                      size_hint_y=None, height=dp(40))
        self._example_label = WrapLabel(font_name=KO_FONT, font_size='17sp', color=INK)
        self._example_label.bind(height=self._sync_example_row)
        self.example_button = ZhButton(
            text='听', bg_color=(0.90, 0.86, 0.76, 1), text_color=(0.30, 0.26, 0.16, 1),
            font_size='15sp', size_hint=(None, None), size=('34dp', '34dp'))
        self.example_button.idle_text = '听'
        self.example_button.busy_text = '…'
        self._example_row.add_widget(self._example_label)
        self._example_row.add_widget(self.example_button)
        self.add_widget(self._example_row)

        self._trans_label = WrapLabel(font_name=CN_FONT, font_size='14sp', color=SUBTLE)
        self.add_widget(self._trans_label)

        self.bind(word=self._refresh, pos_cn=self._refresh, meaning=self._refresh,
                  example=self._refresh, example_translation=self._refresh)
        self._refresh()

    def _sync_meaning_row(self, *args):
        self._meaning_row.height = max(self._meaning_label.height, dp(26))

    def _sync_example_row(self, *args):
        self._example_row.height = max(self._example_label.height, dp(34))

    def _refresh(self, *args):
        gloss = ('[%s]  %s' % (self.pos_cn, self.meaning)) if self.pos_cn else self.meaning
        self._meaning_label.text = mixed(gloss)
        self._example_label.text = mixed(self.example)
        self._trans_label.text = mixed(self.example_translation)
        has_example = bool(self.example)
        for widget in (self._divider, self._header, self._example_row):
            widget.opacity = 1 if has_example else 0
        self._example_row.size_hint_y = None if has_example else 0
        self._trans_label.opacity = 1 if self.example_translation else 0
