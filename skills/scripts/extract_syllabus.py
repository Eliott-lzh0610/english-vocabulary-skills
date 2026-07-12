#!/usr/bin/env python3
"""Extract CET-4/6 word lists from the official syllabus PDF (2016 edition)."""

import argparse, os, re, sys
from collections import defaultdict

import pdfplumber

_SKIP_RE = re.compile(r"全国大学英语|六级考试大纲|年修订版|词\s*表|^\d+$")
_FW_FIX = str.maketrans(
    "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
)
_SC_RE = re.compile(r"[ -‏ -  　Ｇ]")
_SP_MAP = str.maketrans("１２３４５６７８９０", "1234567890")


def extract_first_letter(word: str) -> str:
    w = word.strip()
    if not w:
        return ""
    if w[0] == "(" and len(w) > 1 and w[1].isalpha():
        return w[1].upper()
    if w[0].isalpha():
        return w[0].upper()
    return ""


def _clean(w: str) -> str:
    return _SC_RE.sub("", w.strip().translate(_FW_FIX).translate(_SP_MAP))


def _is_skip(t: str) -> bool:
    t = t.strip()
    return not t or _SKIP_RE.match(t)


def extract(pdf_path: str, start_page: int = 21):
    print(f"[extract] {pdf_path} from page {start_page}")
    c4, c6 = [], []
    with pdfplumber.open(pdf_path) as pdf:
        pw = None
        for pi in range(start_page - 1, len(pdf.pages)):
            page = pdf.pages[pi]
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue
            words.sort(key=lambda w: (w["top"], w["x0"]))
            left = [w for w in words if w["x0"] < 120
                    and not _is_skip(w.get("text", "").strip())
                    and w.get("text", "").strip() != "★"]
            long_s = sum(1 for w in left if len(w.get("text", "").strip()) > 30)
            if long_s > 5 and len(left) < 20:
                print(f"  Stop at page {pi + 1} (left={len(left)}, long={long_s})")
                break
            for w in words:
                t = w.get("text", "").strip()
                if not t:
                    continue
                x0 = w["x0"]
                if t == "★" and x0 < 120:
                    if pw:
                        c6.append(pw)
                        pw = None
                    continue
                if x0 >= 120:
                    continue
                if _is_skip(t):
                    continue
                cl = _clean(t)
                if not cl or len(cl) < 2:
                    continue
                if len(cl) > 30 and " " in cl:
                    continue
                if pw:
                    c4.append(pw)
                pw = cl
        if pw:
            c4.append(pw)
    print(f"  Raw: CET4={len(c4)}, CET6={len(c6)}")

    # Dedup
    def _dedup(lst):
        seen, r = set(), []
        for x in lst:
            if x.lower() not in seen:
                seen.add(x.lower())
                r.append(x)
        return r

    c4, c6 = _dedup(c4), _dedup(c6)

    def _grp(lst):
        g = defaultdict(list)
        for x in lst:
            f = extract_first_letter(x)
            g[f if f and "A" <= f <= "Z" else "#"].append(x)
        return dict(g)

    return _grp(c4), _grp(c6)


def main():
    p = argparse.ArgumentParser(description="Extract CET syllabus word list")
    p.add_argument("pdf_path", help="Path to syllabus PDF")
    p.add_argument("-o", "--output-dir", default="output/syllabus")
    p.add_argument("--start-page", type=int, default=21)
    args = p.parse_args()

    g4, g6 = extract(args.pdf_path, args.start_page)

    for lvl, groups in [("CET4", g4), ("CET6", g6)]:
        d = os.path.join(args.output_dir, lvl)
        os.makedirs(d, exist_ok=True)
        for lt in sorted(groups):
            fp = os.path.join(d, f"{lt}_wordlist.txt")
            with open(fp, "w", encoding="utf-8") as f:
                for w in groups[lt]:
                    f.write(w + "\n")
            print(f"  {lvl}/{lt}_wordlist.txt ({len(groups[lt])} words)")

    t4 = sum(len(v) for v in g4.values())
    t6 = sum(len(v) for v in g6.values())
    print(f"  Total: {t4} CET4 + {t6} CET6")


if __name__ == "__main__":
    main()
