"""
四选一的选项生成。

要点：
  1. 词库里 1671 条释义去重只剩 1555，有 106 组完全同义（那个/什么/决定 各 3-4 个词），
     随机抽干扰项会抽出「两个都对」的题，所以必须按词元重叠排除。
  2. 干扰项优先取同词性，题目难度更合理（不会一眼看出词性不符）。
  3. 传入 seed 可复现，方便测试。
"""
import random
import re

SPLIT = re.compile(r'[；;，,、。\s]+')
OPTION_COUNT = 4


def gloss(entry):
    """选项/答案统一用这个文本，保证和卡片背面显示的完全一致"""
    return (entry.get('meaning_cn') or entry.get('meaning') or '').strip()


def tokens(entry):
    return {t for t in SPLIT.split(gloss(entry)) if t}


def option_text(entry, max_parts=2):
    """选项只显示前 1-2 个核心词元。

    不能用完整合并释义：多义词会出现「胸；胸部；胸前；心；心情；内心；胸口；心口」
    这种 8 词元的长串，既撑破按钮，又能靠长度一眼认出答案。
    排除重叠时仍然用 tokens() 的全量词元，只有展示文本被截断。
    """
    parts = [t for t in SPLIT.split(gloss(entry)) if t]
    return '；'.join(parts[:max_parts])


def build_options(answer, pool, seed=None, count=OPTION_COUNT):
    """返回 count 个选项（含正确答案），每项为 {word, gloss, is_answer}。

    两层排除：
      1. 全量词元不得与已选项重叠 —— 防止「两个都对」和近义干扰项互撞
      2. 截断后的展示文本不得重复 —— 否则会出现两个一模一样的选项
    """
    rng = random.Random(seed)
    answer_pos = answer.get('pos_cn') or ''
    taken = set(tokens(answer))
    shown = {option_text(answer)}

    same_pos, other_pos = [], []
    for entry in pool:
        if entry is answer or not gloss(entry):
            continue
        toks = tokens(entry)
        if toks & taken:
            continue
        if (entry.get('pos_cn') or '') == answer_pos:
            same_pos.append((entry, toks))
        else:
            other_pos.append((entry, toks))

    rng.shuffle(same_pos)
    rng.shuffle(other_pos)

    picked = []
    for entry, toks in same_pos + other_pos:
        if toks & taken or option_text(entry) in shown:
            continue
        picked.append(entry)
        taken |= toks
        shown.add(option_text(entry))
        if len(picked) == count - 1:
            break

    options = [{'word': answer['word'], 'gloss': option_text(answer), 'is_answer': True}]
    options += [{'word': e['word'], 'gloss': option_text(e), 'is_answer': False}
                for e in picked]
    rng.shuffle(options)
    return options
