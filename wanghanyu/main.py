"""
汪韩语 - 入口文件
一款韩语背词 App，基于 Kivy
"""

import json
from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from screens.study_screen import StudyScreen
from utils.paths import resource

KV_FILE = resource('assets', 'kv', 'main.kv')


class WangHanyuApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = '汪韩语'
        self.words = []

    def build(self):
        Window.size = (400, 700)
        Window.clearcolor = (1, 1, 1, 1)

        self.load_words()

        sm = Builder.load_file(KV_FILE)
        self.study_screen = StudyScreen(self.words)
        sm.add_widget(self.study_screen)

        return sm

    def load_words(self):
        with open(resource('data', 'words.json'), 'r', encoding='utf-8') as f:
            self.words = json.load(f)

    def on_learn(self):
        self.study_screen.reset()
        self.root.current = 'study'

    def go_home(self):
        self.root.current = 'main'


if __name__ == '__main__':
    WangHanyuApp().run()
