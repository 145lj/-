"""
单词数据模型
"""
from dataclasses import dataclass

@dataclass
class Word:
    id: int
    word: str
    romanization: str
    meaning: str
    example: str
    example_translation: str
