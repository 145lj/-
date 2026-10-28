"""
间隔重复算法 (SRS - Spaced Repetition System)
基于 SM-2 算法简化版
"""
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class ReviewItem:
    word_id: int
    review_count: int = 0
    ease_factor: float = 2.5
    interval: int = 1
    next_review: str = ""
    last_review: str = ""
    status: str = 'new'

    def next_interval(self, quality):
        if quality < 3:
            self.review_count = 0
            self.interval = 1
            self.ease_factor = max(1.3, self.ease_factor - 0.2)
        else:
            self.review_count += 1
            if self.review_count == 1:
                self.interval = 1
            elif self.review_count == 2:
                self.interval = 3
            else:
                self.interval = round(self.interval * self.ease_factor)
            self.ease_factor = min(3.0, self.ease_factor + 0.15 - (5 - quality) * 0.08)
        
        self.last_review = datetime.now().strftime('%Y-%m-%d')
        self.next_review = (datetime.now() + timedelta(days=self.interval)).strftime('%Y-%m-%d')
        
        if quality >= 5 and self.review_count >= 3:
            self.status = 'mastered'
        elif self.review_count > 0:
            self.status = 'review'
        else:
            self.status = 'learning'

    def is_due(self):
        return datetime.now().strftime('%Y-%m-%d') >= self.next_review
