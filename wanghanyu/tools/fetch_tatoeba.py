"""
下载 Tatoeba 韩语-普通话句对语料到 data/corpus/

  python tools/fetch_tatoeba.py

授权：CC BY 2.0 FR，App 里需要署名（见 ATTRIBUTION.txt）。
"""
import bz2
import os
import sys

import requests

BASE = 'https://downloads.tatoeba.org/exports/per_language'
FILES = {
    'kor_sentences.tsv': '%s/kor/kor_sentences.tsv.bz2' % BASE,
    'cmn_sentences.tsv': '%s/cmn/cmn_sentences.tsv.bz2' % BASE,
    'kor-cmn_links.tsv': '%s/kor/kor-cmn_links.tsv.bz2' % BASE,
}

ATTRIBUTION = (
    '例句语料来自 Tatoeba 项目 (https://tatoeba.org)，'
    '授权协议为 CC BY 2.0 FR (https://creativecommons.org/licenses/by/2.0/fr/deed)。\n'
    '每条句子保留其原始编号，可在 https://tatoeba.org/sentences/show/<id> 查到贡献者。\n'
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'data', 'corpus')
ATTRIBUTION_DIR = os.path.join(ROOT, 'data', 'attribution')


def proxy_from_registry():
    env = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
    if env:
        return {'http': env, 'https': env}
    try:
        import winreg
        key = r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
        h = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key)
        if not winreg.QueryValueEx(h, 'ProxyEnable')[0]:
            return None
        server = winreg.QueryValueEx(h, 'ProxyServer')[0]
    except OSError:
        return None
    if not server or '=' in server:
        return None
    url = server if '://' in server else 'http://' + server
    return {'http': url, 'https': url}


def main():
    os.makedirs(CORPUS, exist_ok=True)
    os.makedirs(ATTRIBUTION_DIR, exist_ok=True)
    with open(os.path.join(ATTRIBUTION_DIR, 'ATTRIBUTION.txt'), 'w', encoding='utf-8') as f:
        f.write(ATTRIBUTION)

    proxies = proxy_from_registry()
    if not proxies:
        print('未检测到可用代理，若要失败请手动开启代理后重试。')

    for name, url in FILES.items():
        out = os.path.join(CORPUS, name)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            print('已存在，跳过 %s' % name)
            continue
        r = requests.get(url, proxies=proxies, timeout=180,
                         headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
        with open(out, 'wb') as f:
            f.write(bz2.decompress(r.content))
        print('%s  %d 行' % (name, sum(1 for _ in open(out, encoding='utf-8'))))

    with open(os.path.join(CORPUS, 'SOURCES.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join('%s\t%s' % (k, v) for k, v in FILES.items()))
    print('完成，语料在 %s' % CORPUS)
    return 0


if __name__ == '__main__':
    sys.exit(main())
