# -*- coding: utf-8 -*-
"""Minimal pure Kivy test - no KivyMD, just to verify Chinese font works"""
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window

class TestApp(App):
    def build(self):
        Window.clearcolor = (1, 1, 1, 1)  # White background
        layout = BoxLayout(orientation='vertical')
        
        lbl = Label(
            text='汪韩语',
            font_name='assets/fonts/malgun.ttf',
            font_size=48,
            color=(0, 0, 0, 1)  # Black text
        )
        layout.add_widget(lbl)
        
        lbl2 = Label(
            text='开始学习',
            font_name='assets/fonts/malgun.ttf',
            font_size=30,
            color=(0, 0, 0, 1)
        )
        layout.add_widget(lbl2)
        
        return layout

if __name__ == '__main__':
    TestApp().run()
