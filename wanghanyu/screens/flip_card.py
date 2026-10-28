"""
翻转卡片：正面大字韩文词条，背面复用 EntryPanel。

四选一背词界面（study_screen）已改用 EntryPanel 直接展示，这里保留翻转模式
作为「不想做题、只想翻卡过词」时的备选，排版只有一份。
"""
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty, BooleanProperty
from kivy.graphics import Color, Rectangle

from utils.fonts import KO_FONT, mixed
from screens.entry_panel import EntryPanel, INK

FORWARD = (0.97, 0.97, 1.0, 1)
BACKWARD = (0.98, 0.96, 0.90, 1)


class FlipCard(FloatLayout):
    word = StringProperty('')
    pos_cn = StringProperty('')
    meaning = StringProperty('')
    example = StringProperty('')
    example_translation = StringProperty('')
    is_flipped = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 0.45)

        self._front = FloatLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self._front._bg = FORWARD
        self._front.bind(pos=self._paint, size=self._paint)
        self._word_label = Label(
            font_name=KO_FONT, font_size='40sp', color=INK,
            halign='center', valign='middle', markup=True)
        self._word_label.size_hint = (0.9, 0.7)
        self._word_label.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self._front.add_widget(self._word_label)
        self.add_widget(self._front)

        self._back = FloatLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self._back._bg = BACKWARD
        self._back.bind(pos=self._paint, size=self._paint)
        self.entry = EntryPanel(size_hint=(1, None), pos_hint={'center_y': 0.5})
        self._back.add_widget(self.entry)
        self.add_widget(self._back)
        self._back.opacity = 0

        self.bind(word=self._push, pos_cn=self._push, meaning=self._push,
                  example=self._push, example_translation=self._push,
                  is_flipped=self._apply_flip)
        self._push()

    def _paint(self, widget, *args):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*widget._bg)
            Rectangle(pos=widget.pos, size=widget.size)

    def _push(self, *args):
        self._word_label.text = mixed(self.word)
        self.entry.word = self.word
        self.entry.pos_cn = self.pos_cn
        self.entry.meaning = self.meaning
        self.entry.example = self.example
        self.entry.example_translation = self.example_translation

    @property
    def example_button(self):
        return self.entry.example_button

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        # 先让当前可见面板吃掉事件，否则点「听」会连带翻转卡片
        panel = self._back if self.is_flipped else self._front
        if panel.dispatch('on_touch_down', touch):
            return True
        self.is_flipped = not self.is_flipped
        return True

    def _apply_flip(self, *args):
        self._front.opacity = 0 if self.is_flipped else 1
        self._back.opacity = 1 if self.is_flipped else 0
