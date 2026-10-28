"""
中韩文按钮 - 用 Label 显示文字，canvas.before 画背景

单独成模块是为了避免 study_screen <-> flip_card 循环导入。
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty, ColorProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle

from utils.fonts import CN_FONT, mixed


class ZhButton(ButtonBehavior, BoxLayout):
    text = StringProperty('')
    bg_color = ColorProperty((1, 0.55, 0, 1))
    font_name = StringProperty(CN_FONT)
    font_size = StringProperty('20sp')
    text_color = ColorProperty((1, 1, 1, 1))
    halign = StringProperty('center')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        self._label = Label(
            text=mixed(self.text),
            font_name=self.font_name,
            font_size=self.font_size,
            color=self.text_color,
            halign=self.halign,
            valign='middle',
            markup=True,
        )
        self._label.size_hint = (1, 1)
        self.add_widget(self._label)

        self.bind(pos=self._update_bg, size=self._update_bg)
        self.bind(text=self._update_text, halign=self._update_align)
        self.bind(size=self._wrap_label)

    def _wrap_label(self, *args):
        """给 Label 定宽才能折行，否则长释义会直接溢出按钮边界"""
        self._label.text_size = (max(self.width - dp(16), 10), None)

    def _update_align(self, *args):
        self._label.halign = self.halign

    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            Rectangle(pos=self.pos, size=self.size)

    def _update_text(self, *args):
        self._label.text = mixed(self.text)

    def on_release(self, *args):
        callback = getattr(self, '_release_callback', None)
        if callback:
            callback(self)
