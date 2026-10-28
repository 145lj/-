"""
学习界面 - 四选一背词

流程（用户选定的方案二）：
  出题：大字韩文词条 + 四个中文选项
  作答：点对/点错都立刻着色，半秒后自动揭晓
  揭晓：换成词典式词条页（词性＋释义／例句＋独立播放），并保留
        认识 / 模糊 / 忘记 三档自评来驱动 SRS 间隔
  也可以直接点「看答案」跳过作答。
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.metrics import dp

from models.srs import ReviewItem
from models.quiz import build_options, gloss
from utils.storage import Storage
from utils.audio import AudioPlayer, speakable
from utils.fonts import CN_FONT, KO_FONT
from screens.zh_button import ZhButton
from screens.entry_panel import EntryPanel, INK, SUBTLE

RIGHT = (0.25, 0.62, 0.28, 1)
WRONG = (0.78, 0.24, 0.24, 1)
IDLE_OPTION = (0.93, 0.93, 0.95, 1)
LETTERS = 'ABCD'
REVEAL_DELAY = 0.6


class StudyScreen(Screen):

    def __init__(self, words, **kwargs):
        kwargs['name'] = 'study'
        super().__init__(**kwargs)
        self.words = words
        self.current_index = 0
        self.stats = {'correct': 0, 'review': 0, 'wrong': 0}
        self.storage = Storage()
        self.review_items = {}
        self.options = []
        self.revealed = False
        self.answered_right = None

        self._build_ui()
        self._show_word()

    # ---------- 布局 ----------

    def _build_ui(self):
        self.clear_widgets()

        root = BoxLayout(orientation='vertical', padding='12dp', spacing='10dp')
        self.add_widget(root)

        top_bar = BoxLayout(orientation='horizontal', size_hint=(1, None), height='42dp')
        root.add_widget(top_bar)

        self.word_counter = Label(text='', font_name=CN_FONT, font_size='16sp',
                                  color=SUBTLE, halign='left', valign='middle')
        self.word_counter.size_hint = (1, 1)
        top_bar.add_widget(self.word_counter)

        self.speaker = ZhButton(text='发音', bg_color=(0.9, 0.9, 0.9, 1),
                                text_color=(0.25, 0.25, 0.3, 1), font_size='18sp',
                                size_hint=(None, 1), width='72dp')
        self.speaker._release_callback = lambda btn: self._speak_word()
        self.speaker.idle_text = '发音'
        self.speaker.busy_text = '合成中'
        top_bar.add_widget(self.speaker)
        AudioPlayer.on_status = self._on_tts_status

        self.word_label = Label(text='', font_name=KO_FONT, font_size='42sp',
                                color=INK, halign='center', valign='middle', markup=True)
        self.word_label.size_hint = (1, None)
        self.word_label.height = dp(86)
        root.add_widget(self.word_label)

        self._root = root
        self._build_question_stage()
        self._build_answer_stage()
        self._set_stage(False)

    def _build_question_stage(self):
        box = BoxLayout(orientation='vertical', spacing='8dp')
        self.question_box = box

        prompt = Label(text='请回想单词释义并选择，或直接「看答案」', font_name=CN_FONT,
                       font_size='14sp', color=SUBTLE, halign='center', valign='middle',
                       size_hint=(1, None), height=dp(24))
        box.add_widget(prompt)

        self.option_buttons = []
        for _ in LETTERS:
            btn = ZhButton(text='', bg_color=IDLE_OPTION, text_color=INK,
                           font_size='17sp', halign='left',
                           size_hint=(1, None), height=dp(56))
            btn._release_callback = self._on_option
            box.add_widget(btn)
            self.option_buttons.append(btn)

        skip = ZhButton(text='看答案', bg_color=(0.82, 0.82, 0.86, 1),
                        text_color=(0.3, 0.3, 0.35, 1), font_size='16sp',
                        size_hint=(1, None), height=dp(44))
        skip._release_callback = lambda btn: self._reveal()
        box.add_widget(skip)

        box.add_widget(Widget(size_hint_y=1))

    def _build_answer_stage(self):
        box = BoxLayout(orientation='vertical', spacing='10dp')
        self.answer_box = box

        self.entry = EntryPanel(size_hint=(1, None))
        self.entry.example_button._release_callback = lambda btn: self._speak_example()
        self.entry.example_button.idle_text = '听'
        self.entry.example_button.busy_text = '…'
        box.add_widget(self.entry)

        box.add_widget(Widget(size_hint_y=1))

        rating = BoxLayout(orientation='horizontal', spacing='8dp',
                           size_hint=(1, None), height=dp(52))
        box.add_widget(rating)
        self.rating_buttons = []
        for text, color, quality in (('认识', RIGHT, 5), ('模糊', (0.85, 0.65, 0.1, 1), 3),
                                     ('忘记', WRONG, 1)):
            btn = ZhButton(text=text, bg_color=color, font_size='19sp', size_hint=(1, 1))
            btn._release_callback = lambda b, q=quality: self._on_rating(q)
            rating.add_widget(btn)
            self.rating_buttons.append(btn)

    def _set_stage(self, revealed):
        """直接增删子件来切换状态，比用 size_hint_y=0 藏起来可靠。"""
        self.revealed = revealed
        showing = self.answer_box if revealed else self.question_box
        hiding = self.question_box if revealed else self.answer_box
        if hiding.parent is self._root:
            self._root.remove_widget(hiding)
        if showing.parent is not self._root:
            self._root.add_widget(showing, 0)

    # ---------- 出题 ----------

    def _show_word(self):
        if self.current_index >= len(self.words):
            self._show_summary()
            return

        entry = self.words[self.current_index]
        self.entry.word = entry['word']
        self.entry.pos_cn = entry.get('pos_cn', '')
        self.entry.meaning = entry.get('meaning_cn') or entry['meaning']
        self.entry.example = entry['example']
        self.entry.example_translation = entry['example_translation']

        self.word_label.text = entry['word']
        self.word_counter.text = '第 %d / %d 个' % (self.current_index + 1, len(self.words))

        self.options = build_options(entry, self.words, seed=self.current_index)
        for letter, btn, opt in zip(LETTERS, self.option_buttons, self.options):
            btn.text = '%s   %s' % (letter, opt['gloss'])
            btn.bg_color = IDLE_OPTION
            btn.disabled = False
        for btn in self.option_buttons[len(self.options):]:
            btn.text = ''
            btn.disabled = True

        self.answered_right = None
        self._set_stage(False)

        if entry['id'] not in self.review_items:
            self.review_items[entry['id']] = ReviewItem(word_id=entry['id'])

    # ---------- 作答 ----------

    def _on_option(self, btn):
        if self.revealed:
            return
        chosen = self.options[self.option_buttons.index(btn)]
        self.answered_right = bool(chosen['is_answer'])
        for other in self.option_buttons:
            other.disabled = True
            opt = self.options[self.option_buttons.index(other)]
            if opt['is_answer']:
                other.bg_color = RIGHT
            elif other is btn:
                other.bg_color = WRONG
        Clock.schedule_once(lambda dt: self._reveal(), REVEAL_DELAY)

    def _reveal(self):
        if self.revealed:
            return
        self._set_stage(True)

    def _on_rating(self, quality):
        entry = self.words[self.current_index]
        self.review_items[entry['id']].next_interval(quality)
        if quality >= 5:
            self.stats['correct'] += 1
        elif quality == 3:
            self.stats['review'] += 1
        else:
            self.stats['wrong'] += 1
        self.current_index += 1
        self._show_word()

    # ---------- 发音 ----------

    def _speak(self, text):
        if text:
            AudioPlayer.speak(text, lang='ko')

    def _speak_word(self):
        if self.current_index < len(self.words):
            self._speak(self.words[self.current_index]['word'])

    def _speak_example(self):
        if self.current_index < len(self.words):
            self._speak(self.words[self.current_index]['example'])

    def _tts_targets(self):
        if self.current_index >= len(self.words):
            return {}
        entry = self.words[self.current_index]
        targets = {speakable(entry['word']): self.speaker}
        if entry['example']:
            targets[speakable(entry['example'])] = self.entry.example_button
        return targets

    def _on_tts_status(self, text, state):
        btn = self._tts_targets().get(text)
        if btn is None:
            return
        busy = getattr(btn, 'busy_text', '合成中')
        idle = getattr(btn, 'idle_text', '发音')
        btn.text = {'synthesizing': busy, 'ready': idle, 'failed': '!'}.get(state, idle)
        if state == 'failed':
            Clock.schedule_once(lambda dt: setattr(btn, 'text', idle), 2.0)

    # ---------- 结算 ----------

    def _show_summary(self):
        self.clear_widgets()
        from kivy.uix.floatlayout import FloatLayout
        container = FloatLayout()
        self.add_widget(container)

        box = BoxLayout(orientation='vertical', spacing='20dp', padding='40dp',
                        size_hint=(0.85, 0.55))
        box.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        container.add_widget(box)

        def _lbl(text, color, font_size='20sp'):
            return Label(text=text, font_name=CN_FONT, font_size=font_size, color=color,
                         halign='center', valign='middle')

        box.add_widget(_lbl('学习完成！', (0.1, 0.1, 0.1, 1), '36sp'))
        box.add_widget(_lbl('认识: %d 个' % self.stats['correct'], (0.2, 0.6, 0.2, 1)))
        box.add_widget(_lbl('模糊: %d 个' % self.stats['review'], (0.7, 0.5, 0.1, 1)))
        box.add_widget(_lbl('忘记: %d 个' % self.stats['wrong'], (0.7, 0.2, 0.2, 1)))

        streak = self.storage.load_progress()['stats']['streak_days']
        box.add_widget(_lbl('连续学习: %d 天' % streak, (0.5, 0.5, 0.5, 1), '16sp'))

        back_btn = ZhButton(text='返回主页', bg_color=(0.6, 0.35, 0, 1), font_size='20sp',
                            size_hint=(0.5, None), height=dp(50))
        back_btn._release_callback = lambda b: self.manager.set_current('main')
        box.add_widget(back_btn)

    def reset(self):
        self.current_index = 0
        self.stats = {'correct': 0, 'review': 0, 'wrong': 0}
        self.review_items = {}
        self._build_ui()
        self._show_word()
