"""
krdict（한국어기초사전 Open API）取数模块。

接口实测结论（2026-10-28）：
  必填参数是 q，num 只能取 10/20/30 这类值；
  translated=y 才返回译文，且一次把所有语言都带回来（不能按语言筛，
  传 trans_lang=eng 会直接 System error）；
  译文块里 trans_lang 是韩文语言名（중국어 / 영어 / 일본어 ...）。

key 从环境变量 KRDICT_KEY 或 data/krdict_key.txt 读，不写进代码。
"""
import html
import os
import re

import requests

API = 'https://krdict.korean.go.kr/api/search'
PROXY_URL = 'http://127.0.0.1:7890'
ZH_LANG = '중국어'

POS_CN = {
    '명사': '名词', '대명사': '代名词', '수사': '数词', '동사': '动词',
    '형용사': '形容词', '부사': '副词', '관형사': '冠形词', '감탄사': '感叹词',
    '보조용언': '辅助用言', '접두사': '前缀', '접미사': '后缀',
}
GRADE_CN = {'초급': '初级', '중급': '中级', '고급': '高级'}


def load_key():
    key = os.environ.get('KRDICT_KEY')
    if key:
        return key.strip()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, 'data', 'krdict_key.txt')
    if os.path.exists(path):
        return open(path, encoding='utf-8').read().strip()
    raise RuntimeError('未找到 krdict key（设 KRDICT_KEY 或写 data/krdict_key.txt）')


def _clean(text):
    return html.unescape(re.sub(r'\s+', ' ', text or '')).strip()


def _tag(block, name):
    m = re.search(r'<%s>(.*?)</%s>' % (name, name), block, re.S)
    return _clean(m.group(1)) if m else ''


def _zh_of(translation_block):
    """一个 <translation> 块里的中文译文 (trans_word, trans_dfn)，没有则 None"""
    if _tag(translation_block, 'trans_lang') != ZH_LANG:
        return None
    word = re.search(r'<trans_word><!\[CDATA\[(.*?)\]\]>', translation_block, re.S)
    dfn = re.search(r'<trans_dfn><!\[CDATA\[(.*?)\]\]>', translation_block, re.S)
    return (_clean(word.group(1)) if word else '',
            _clean(dfn.group(1)) if dfn else '')


def parse_item(item_xml):
    """一个 <item> -> dict"""
    senses = []
    for sense in re.findall(r'<sense>(.*?)</sense>', item_xml, re.S):
        zh = None
        for block in re.findall(r'<translation>(.*?)</translation>', sense, re.S):
            zh = _zh_of(block) or zh
        senses.append({
            'order': _tag(sense, 'sense_order'),
            'definition': _tag(sense, 'definition'),
            'zh_word': zh[0] if zh else '',
            'zh_defn': zh[1] if zh else '',
        })
    grade = _tag(item_xml, 'word_grade')
    return {
        'word': _tag(item_xml, 'word'),
        'pos': _tag(item_xml, 'pos'),
        'pos_cn': POS_CN.get(_tag(item_xml, 'pos'), _tag(item_xml, 'pos')),
        'grade': grade,
        'grade_cn': GRADE_CN.get(grade, grade),
        'pronunciation': _tag(item_xml, 'pronunciation'),
        'senses': senses,
    }


def lookup(word, session=None, timeout=25):
    """精确查一个词；找不到精确词条时返回 None"""
    params = {'key': load_key(), 'q': word, 'num': '10', 'translated': 'y'}
    getter = session or requests
    resp = getter.get(API, params=params, timeout=timeout,
                      proxies={'http': PROXY_URL, 'https': PROXY_URL},
                      headers={'User-Agent': 'Mozilla/5.0'})
    resp.raise_for_status()
    if '<error_code>' in resp.text:
        code = re.search(r'<error_code>(\d+)</error_code>', resp.text).group(1)
        raise RuntimeError('krdict 错误 %s: %s' % (
            code, _tag(resp.text, 'message')))
    for item in re.findall(r'<item>(.*?)</item>', resp.text, re.S):
        parsed = parse_item(item)
        if parsed['word'] == word:
            return parsed
    return None
