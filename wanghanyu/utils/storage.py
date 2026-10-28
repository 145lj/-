"""
本地存储工具 - 保存学习进度
"""
import json
import os
from datetime import datetime

from utils.paths import writable

class Storage:
    def __init__(self):
        self.progress_file = writable('data', 'progress.json')
    
    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'learned': [],
            'review_queue': [],
            'stats': {
                'total_studied': 0,
                'total_correct': 0,
                'streak_days': 0,
                'last_study_date': None
            }
        }
    
    def save_progress(self, progress):
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    
    def mark_learned(self, word_id):
        progress = self.load_progress()
        if word_id not in progress['learned']:
            progress['learned'].append(word_id)
            progress['stats']['total_studied'] += 1
        self.save_progress(progress)
    
    def update_streak(self):
        progress = self.load_progress()
        today = datetime.now().strftime('%Y-%m-%d')
        if progress['stats']['last_study_date'] == today:
            return
        last = progress['stats']['last_study_date']
        if last:
            last_date = datetime.strptime(last, '%Y-%m-%d')
            today_date = datetime.strptime(today, '%Y-%m-%d')
            if (today_date - last_date).days == 1:
                progress['stats']['streak_days'] += 1
            else:
                progress['stats']['streak_days'] = 1
        else:
            progress['stats']['streak_days'] = 1
        progress['stats']['last_study_date'] = today
        self.save_progress(progress)
