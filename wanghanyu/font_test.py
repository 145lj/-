"""Verify Kivy [font=] markup switching works with the sdl2 provider."""
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window

KO = 'assets/fonts/malgun.ttf'
CN = 'assets/fonts/msyh.ttc'

ROWS = [
    ('CN plain', CN, '汪韩语 韩语学习，从汪开始！开始学习'),
    ('KO plain', KO, '가게 한국어'),
    ('markup base=CN', CN, f'[font={CN}]汪韩语[/font]  [font={KO}]가게[/font]'),
    ('markup base=KO', KO, f'[font={KO}]가게[/font]  [font={CN}]汪韩语[/font]'),
    ('nested', CN, f'[font={CN}]在（"[font={KO}]있다[/font]"的敬语）[/font]'),
    ('icon CN', CN, '●'),
    ('icon KO', KO, '▶'),
    ('icon KO2', KO, '♪'),
]


class Test(App):
    def build(self):
        Window.size = (760, 460)
        box = BoxLayout(orientation='vertical', padding='10dp', spacing='4dp')
        for name, font, text in ROWS:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height='46dp')
            row.add_widget(Label(text=name, size_hint_x=0.22, font_size='13sp',
                                 color=(0.3, 0.3, 0.3, 1)))
            row.add_widget(Label(text=text, font_name=font, font_size='20sp',
                                 markup=True, color=(0.1, 0.1, 0.15, 1)))
            box.add_widget(row)
        return box

    def on_start(self):
        Clock.schedule_once(lambda dt: self.shot(), 1.2)

    def shot(self):
        p = Window.screenshot(name='fonttest.png')
        print('SAVED', p)
        self.stop()


Test().run()
