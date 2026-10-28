#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Offline checker: does each Korean headword (used_by) really correspond to its
example sentence (korean column)?

No network / no proxy / no external service: pure Unicode + Hangul morphology.

Method
------
1. Decompose every Hangul syllable into (initial, vowel, final) jamo.
2. Build the set of surface forms a dictionary lemma can take in running text
   (nouns: bare stem + particles; verbs/adjectives: stem variants x endings).
3. Apply the standard Korean spelling contractions on both sides.
4. Compare against the sentence tokens and classify the hit:
     exact  token == form
     prefix token starts with form        (normal for nouns: 김밥을)
     suffix token ends with form          (normal for verbs: 먹고, 도와주다니)
     inner  form sits strictly inside     (SUSPICIOUS: lemma swallowed by a
             a longer word: 정하다 inside 다정하다)
     none   no morphological trace at all  (BROKEN)
"""
import csv, re, sys, unicodedata, json
from collections import Counter

SRC = r"D:\Projects\WangHanyu\ko_align\used_sentences.tsv"

# ---------------------------------------------------------------- jamo table
def _build():
    name2cp = {}
    for cp in range(0x1100, 0x1200):
        try:
            name2cp[unicodedata.name(chr(cp))] = chr(cp)
        except ValueError:
            pass
    return name2cp

N2C = _build()

def J(kind, letter):
    """kind: CHO|JUNG|JONG ; letter: canonical jamo name tail"""
    key = f"HANGUL {kind} {letter}"
    if key not in N2C:
        raise KeyError(key)
    return N2C[key]

CHO = {c: J("CHOSEONG", c) for c in
       "KIYEOK NIEUN TIKEUT RIEUL MIEUM PIEUP SIOS IEUNG CIEUC CHIEUCH "
       "KIYEOK-SIOS TIEUT PHIEUPH HIEUH SSANGNIEUN".split()}
JUNG = {c: J("JUNGSEONG", c) for c in
        "A AE YA YAE EO E YEO YE O WA WAE OE YO U WEO WE WI YU EU I".split()}
JONG = {c: J("JONGSEONG", c) for c in
        "KIYEOK NIEUN TIKEUT RIEUL MIEUM PIEUP SIOS IEUNG CIEUC CHIEUCH "
        "KIYEOK-SIOS TIEUT PHIEUPH HIEUH SSANGNIEUN".split()}
# remove duplicates (KIYEOK appears twice) -> dict keeps last, fine
CHOS = set(CHO.values()); JUNGS = set(JUNG.values()); JONGS = set(JONG.values())

def is_hangul_syllable(ch):
    return 0xAC00 <= ord(ch) <= 0xD7A3

def decomp(ch):
    """Hangul syllable -> (cho, jung, jong) using NFD."""
    parts = unicodedata.normalize("NFD", ch)
    cho = jung = jong = ""
    for p in parts:
        if p in CHOS:
            cho = p
        elif p in JUNGS:
            jung = p
        elif p in JONGS:
            jong = p
    return cho, jung, jong

def compose(cho, jung, jong=""):
    return unicodedata.normalize("NFC", chr(0xAC00 + (CHO_IDX[cho] * 21 + JUNG_IDX[jung]) * 28 + JONG_IDX[jong]))

CHO_IDX = {v: k for k, v in CHO.items()}
JUNG_IDX = {v: k for k, v in JUNG.items()}
JONG_IDX = {v: k for k, v in JONG.items()}

# ------------------------------------------------------- syllable sequences
def sylls(text):
    """[(cho,jung,jong), ...] for Hangul syllables; other chars become ('',ch,'')."""
    out = []
    for ch in text:
        if is_hangul_syllable(ch):
            out.append(decomp(ch))
        else:
            out.append(("", ch, ""))
    return out

def contract(seq):
    """Apply Korean spelling contractions across syllable boundaries."""
    out = [list(s) for s in seq]
    i = 0
    while i < len(out) - 1:
        p, c = out[i], out[i + 1]
        pc, pj, pjong = p
        cc, cj, cjong = c
        # ㅎ-final + 어/오  ->  preceding ㅎ drops, vowel becomes ㅐ
        if pjong == JONG["HIEUH"] and cj in (JUNG["EO"], JUNG["O"]):
            p[2] = ""
            c[1] = JUNG["AE"] if cj == JUNG["EO"] else JUNG["WA"]
            i += 1
            continue
        # 하 + 어 -> 해   (ㅎ initial + ㅏ, next vowel ㅓ -> ㅐ)
        if pc == CHO["HIEUH"] and pj == JUNG["A"] and cj == JUNG["EO"]:
            p[1] = JUNG["AE"]
            c[0] = c[1] = c[2] = ""
            i += 1
            continue
        # ㅂ-final + 어 : ㅂ drops, ㅓ merges with the stem vowel
        if pjong == JONG["PIEUP"] and cj == JUNG["EO"]:
            p[2] = ""
            if pj == JUNG["O"]:
                c[1] = JUNG["WA"]
            elif pj in (JUNG["U"], JUNG["EO"]):
                c[1] = JUNG["WEO"]
            else:
                c[1] = JUNG["EO"]
            i += 1
            continue
        # ㅡ-final + 어 : ㅡ drops, ㅓ -> ㅏ
        if pjong == JONG["IEUNG"] and cj == JUNG["EO"]:
            p[2] = ""
            c[1] = JUNG["A"]
            i += 1
            continue
        # ㅣ-final + 어 : ㅣ drops  (시 + 어 -> 서)  [rare in lemmas]
        if pjong == JONG["IEUNG"] and cj == JUNG["EO"]:
            i += 1
            continue
        i += 1
    return [tuple(s) for s in out if not (s[0] == "" and s[1] == "" and s[2] == "")]

def key(seq):
    """Comparable string for a syllable sequence."""
    return "|".join(f"{a}{b}{c}" for a, b, c in seq)

def text_of(seq):
    return "".join(compose(a, b, c) if b else a for a, b, c in seq)

# --------------------------------------------------------- stem variations
def strip_da(word):
    return word[:-1] if word.endswith("다") else None

# irregular stem -> surface stem (base form that actually appears before endings)
IRREG = {
    "오": "와", "이": "예", "주": "줘", "보": "봐", "하": "해", "되": "돼",
    "그렇": "그래", "낫": "나", "걷": "걸", "잇": "이", "묻": "물", "듣": "들",
    "자": "잘", "벼": "벼", "살": "살", "알": "알", "말": "말", "털": "털",
    "낫": "나", "끄": "끄", "삼": "삼", "깎": "깎", "疑难": "疑难",
}
# stems whose ㅂ changes to 우/오 before 어/여
def b_irregular(stem):
    s = sylls(stem)
    if not s:
        return []
    cho, jung, jong = s[-1]
    if jong != JONG["PIEUP"]:
        return []
    base = stem[:-1]
    out = [base + "우"]
    if jung == JUNG["O"]:
        out.append(base + "우오")
    return out

def stem_variants(stem):
    out = [stem]
    s = sylls(stem)
    if s:
        cho, jung, jong = s[-1]
        out += b_irregular(stem)
        if jong == JONG["RIEUL"]:
            out.append(stem[:-1])
        if jong == JONG["IEUNG"]:
            out.append(stem[:-1])
        for k, v in IRREG.items():
            if stem.startswith(k) and len(stem) > len(k):
                out.append(stem[: len(k)] + v + stem[len(k):])
                break
    seen, uniq = set(), []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq

# ------------------------------------------------------------- the endings
V_END = ["아","어","어서","고","지","는","은","을","ㄴ","ㄹ","면","니까","지요","네",
         "군","자","야","소","시","았","었","겠","도","되","라","라고","나","며","거",
         "구나","요","ㅂ니다","는지","는데","든","으려고","으러","며","으로","로",
         "겠지","겠어","세","신","가","거나","거나","고","구나","게"]
C_END = ["아","어","어서","고","지","는","은","을","ㄴ","ㄹ","면","으면","니까","지요",
         "네","군","자","야","소","시","았","었","겠","도","되","라","라고","나","며",
         "거","구나","요","습니다","는지","는데","든","으려고","으러","며","으로",
         "로","겠지","겠어","세","신","가","거나","거나","게"]
JOSA = ["은","는","이","가","을","를","에","에서","에게","한테","도","만","의",
        "와","과","로","서","나","나","요","이","랑","이랑","에게서","한테서",
        "부터","까지","보다","처럼","만큼","께","게","뿐","커","야","여"]

def forms_for(lemma):
    """All plausible surface spellings of the lemma (normalised strings)."""
    lemma = lemma.strip()
    out = {lemma}
    stem = strip_da(lemma)
    if stem:
        s = sylls(stem)
        vowel_end = bool(s) and s[-1][2] == "" and s[-1][1] in (
            JUNG["A"], JUNG["AE"], JUNG["YA"], JUNG["YAE"], JUNG["EO"], JUNG["E"],
            JUNG["YEO"], JUNG["YE"], JUNG["O"], JUNG["WA"], JUNG["WAE"], JUNG["OE"],
            JUNG["YO"], JUNG["U"], JUNG["WEO"], JUNG["WE"], JUNG["WI"], JUNG["YU"],
            JUNG["EU"], JUNG["I"])
        for v in stem_variants(stem):
            ends = V_END if vowel_end else C_END
            for e in ends:
                out.add(v + e)
            # 합니까체
            out.add(v + "ㅂ니다")
            out.add(v + "습니다")
    else:
        for p in JOSA:
            out.add(lemma + p)
        # 이다 copula forms
        out.add(lemma + "이다")
        out.add(lemma + "이에요")
        out.add(lemma + "예요")
        out.add(lemma + "이야")
        out.add(lemma + "이야.")
        # 하다 / 되다 verbs built on the noun
        out.add(lemma + "하다")
        out.add(lemma + "되다")
    return out

TOKEN_RE = re.compile(r"\S+")
STRIP = ".,!?;:\"'()[]{}…、。！？，；：“”‘’「」『』・~"

def tokens(sentence):
    out = []
    for raw in TOKEN_RE.findall(sentence):
        core = raw.strip(STRIP)
        if core:
            out.append((raw, core))
    return out

def norm(seq):
    return key(contract(seq))

def classify(lemma, sentence):
    forms = forms_for(lemma)
    fkeys = {norm(sylls(f)) for f in forms if f}
    # multi-word lemmas: match against the whole sentence string
    if " " in lemma.strip():
        flat = norm(sylls(sentence))
        if norm(sylls(lemma.strip())) in flat:
            return "exact", sentence, lemma
        return "none", "", ""
    best, where, matched = "none", "", ""
    rank = {"exact": 4, "prefix": 3, "suffix": 3, "inner": 2, "none": 0}
    for raw, core in tokens(sentence):
        ck = norm(sylls(core))
        hit = None
        for f in fkeys:
            if not f:
                continue
            if ck == f:
                hit = ("exact", f); break
            if ck.startswith(f):
                hit = ("prefix", f); break
            if ck.endswith(f):
                hit = ("suffix", f); break
            if f in ck:
                hit = ("inner", f); break
        if hit and rank[hit[0]] > rank[best]:
            best, matched = hit[0], hit[1]
            where = raw
    return best, where, matched

def main():
    rows = []
    with open(SRC, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(reader)
        for r in reader:
            if not r:
                continue
            while len(r) < 4:
                r.append("")
            rows.append(r)

    results, counts = [], Counter()
    for r in rows:
        tid, lemma, ko, zh = r[0], r[1], r[2], r[3]
        kind, where, matched = classify(lemma, ko)
        counts[kind] += 1
        results.append({"id": tid, "word": lemma, "ko": ko, "zh": zh,
                        "kind": kind, "token": where, "match": matched})

    with open(r"D:\Projects\WangHanyu\ko_align\report_all.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)

    print("total rows:", len(rows))
    print("classification:", dict(counts))
    for kind in ("none", "inner", "suffix"):
        sel = [x for x in results if x["kind"] == kind]
        print(f"\n===== {kind} ({len(sel)}) =====")
        for x in sel:
            print(f'{x["id"]}\t{x["word"]}\t| {x["ko"]}\t| {x["zh"]}')

if __name__ == "__main__":
    main()
