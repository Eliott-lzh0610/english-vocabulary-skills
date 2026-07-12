#!/usr/bin/env python3
"""Generate CET vocabulary MD notes via Youdao Dictionary (Collins priority)."""

import argparse, json, os, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

YOUDAO_URL = "https://dict.youdao.com/w/{word}/"
CACHE_FILE = "dict_cache.json"
REQUEST_DELAY = 0.8
CIRCLES = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
           "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳"]

_COLLINS_POS = {
    "V-T": ("verb", "vt."), "V-I": ("verb", "vi."),
    "V-RECIP": ("verb", "vti."), "V": ("verb", "vti."),
    "N-COUNT": ("noun", "n."), "N-UNCOUNT": ("noun", "n."),
    "N-VAR": ("noun", "n."), "N": ("noun", "n."),
    "ADJ": ("adjective", "adj."), "ADV": ("adverb", "adv."),
    "PREP": ("preposition", "prep."), "CONJ": ("conjunction", "conj."),
    "PRON": ("pronoun", "pron."), "PHRASE": ("verb", "vti."),
}
_COL_PREPS = ["to", "with", "by", "from", "in", "on", "at", "for", "of",
              "upon", "into", "onto", "out", "off", "over", "through", "against"]


# ======== Collins parser ========

def _extract_col_preps(en_def, word):
    preps = []
    w = word.lower().strip().split("/")[0]
    pat = re.compile(r"\b" + re.escape(w) + r"(?:ed|ing|s)?\s+("
                     + "|".join(_COL_PREPS) + r")\b", re.IGNORECASE)
    for m in pat.finditer(en_def):
        p = m.group(1).lower()
        if p not in preps:
            preps.append(p)
    return preps


def _parse_collins(html):
    m = re.search(r'id="collinsResult"[^>]*>(.*?)(?:<div id="authTrans|$)', html, re.DOTALL)
    if not m:
        return None
    content = m.group(1)
    content = re.sub(r"<(?:li|/li|p|/p|br)[^>]*>", "\n", content)
    content = re.sub(r"<[^>]+>", " ", content)
    content = re.sub(r"&nbsp;", " ", content)
    content = re.sub(r"&rarr;", "→", content)
    content = re.sub(r"\s+", " ", content).strip()
    if len(content) < 10:
        return None
    ph = ""
    pm = re.search(r"/([^/]+)/", content)
    if pm:
        ph = f"/{pm.group(1)}/"
    wm = re.match(r"([a-zA-Z/()]+)", content)
    cw = wm.group(1) if wm else ""
    ds = re.search(r"\d+\.\s*[A-Z-]+", content)
    if not ds:
        return None
    dt = content[ds.start():]
    entries = re.split(r"(?=\d+\.\s*[A-Z-]+\s)", dt)
    pos_defs, examples, checklist = [], [], []
    all_col = defaultdict(list)
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        pm2 = re.match(r"\d+\.\s*([A-Z-]+(?:\s+[A-Z-]+)?)\s+", entry)
        if not pm2:
            continue
        pos_raw = pm2.group(1).strip()
        rest = entry[pm2.end():].strip()
        pi = _COLLINS_POS.get(pos_raw)
        if not pi:
            for k, v in _COLLINS_POS.items():
                if pos_raw.startswith(k):
                    pi = v
                    break
        if not pi:
            continue
        pk, tt = pi
        cm = re.search(r"([一-鿿][^例]*)", rest)
        if cm:
            ed = rest[:cm.start()].strip()
            cd = cm.group(1).strip()
            while ed.endswith("("):
                cd = "(" + cd
                ed = ed[:-1].strip()
        else:
            ed = rest
            cd = ""
        cd = re.sub(r"\[[^\]]*\]", "", cd).strip()
        cd = re.sub(r"\s*\d+\s*$", "", cd).strip()
        for kw in ["同近义词", "同根词", "词组短语", "双语", "→ see", "→ short", "美国英语", "英国英语"]:
            idx = cd.find(kw)
            if idx > 0:
                cd = cd[:idx].strip()
        cd = re.sub(r"\]?\s*→\s*see\s+\S+.*$", "", cd).strip()
        cd = cd.lstrip("]").strip()
        if not cd or len(cd) < 1:
            cd = ed[:30]
            checklist.append({"w": cw, "issue": "cn_missing", "en": ed[:80]})
        for p in _extract_col_preps(ed, cw):
            if cd not in all_col[p]:
                all_col[p].append(cd)
        if cd and not re.match(r"^(美国英语|英国英语)$", cd):
            pos_defs.append((pk, tt, [cd]))
        # Cross-reference: →see X
        see_m = re.search(r"(?:\[(美国英语|英国英语)\])?\s*→\s*(?:see|also)\s+([A-Za-z][A-Za-z -]*?)(?:\s*[,.]|\s+(?:同|词|双|原|权|应|网|以|→|$))", entry)
        if see_m:
            region = see_m.group(1)
            target = see_m.group(2).strip()
            if target and len(target) <= 30:
                see_map = {"pocket money": "零花钱"}
                cn = see_map.get(target.lower(), f"[→{target}]")
                if region == "美国英语":
                    cn = f"[AmE]{cn}"
                elif region == "英国英语":
                    cn = f"[BrE]{cn}"
                pos_defs.append((pk, tt, [cn]))
        # Example
        em = re.search(r"例\s*[：:]\s*(.*)", entry, re.DOTALL)
        if em:
            er = em.group(1).strip()
            for kw in ["词组短语", "同近义词", "同根词", "词语辨析", "双语例句",
                       "原声例句", "权威例句", "以上来源于", "应用推荐", "→ see", "网络释义"]:
                idx = er.find(kw)
                if idx > 0:
                    er = er[:idx].strip()
            ep = re.split(r"([一-鿿])", er, 1)
            if len(ep) >= 2:
                ee = ep[0].strip()
                ec = "".join(ep[1:]).strip()
                for kw in ["词组短语", "同近义词", "同根词", "词语辨析", "双语例句",
                           "原声例句", "权威例句", "例：", "例:", "→ see", "以上来源于"]:
                    idx = ec.find(kw)
                    if idx > 0:
                        ec = ec[:idx].strip()
                if ee and ec:
                    examples.append((ee, ec))
        else:
            checklist.append({"w": cw, "issue": "example_missing", "cn": cd[:50]})
    if not pos_defs:
        return None
    seen = set()
    ud = []
    for item in pos_defs:
        key = (item[0], item[2][0] if item[2] else "")
        if key not in seen:
            seen.add(key)
            ud.append(item)
    return {"phonetic": ph, "pos_defs": ud, "collocations": dict(all_col),
            "examples": examples[:3], "checklist": checklist, "source": "collins"}


# ======== Basic dict fallback ========

def _parse_youdao_defs(raw):
    markers = [r"\badv\.", r"\badj\.", r"\babbr\.", r"\bprep\.", r"\bconj\.",
               r"\bpron\.", r"\binterj\.", r"\bvt\.", r"\bvi\.", r"\bv\.",
               r"\bn\.", r"\bint\.", r"\baux\.", r"\bart\.", r"\bnum\.", r"\bdet\."]
    split_re = re.compile(r"\s*(?=" + "|".join(markers) + r")")
    pos_map = {"v.": "verb", "vt.": "verb", "vi.": "verb", "n.": "noun",
               "adj.": "adjective", "adv.": "adverb", "prep.": "preposition",
               "conj.": "conjunction", "pron.": "pronoun", "abbr.": "abbreviation"}
    raw = raw.strip()
    parts = split_re.split(raw)
    result = []
    cur_tag = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(" + "|".join(markers) + r")\s*(.*)", part)
        if m:
            cur_tag = m.group(1)
            dt = m.group(2).strip()
        else:
            dt = part
        if not cur_tag:
            continue
        pk = pos_map.get(cur_tag, cur_tag.rstrip("."))
        defs = [d.strip(" ,，.") for d in re.split(r"[；;]", dt) if d.strip(" ,，.")]
        if defs:
            tt = cur_tag
            if pk == "verb":
                if cur_tag == "vt.":
                    tt = "vt."
                elif cur_tag == "vi.":
                    tt = "vi."
                else:
                    tt = "vti."
            result.append((pk, tt, defs))
    return result


def _parse_html(html):
    col = _parse_collins(html)
    if col and col.get("pos_defs"):
        return col
    td = re.findall(r'<div class="trans-container">(.*?)</div>', html, re.DOTALL)
    if not td:
        return None
    raw = re.sub(r"<[^>]+>", " ", td[0])
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = re.sub(r"\[\s*[^\[\]]*\s*\]", "", raw).strip()
    raw = re.sub(r"【名】.*?(?:（人名）|$)", "", raw).strip()
    raw = re.sub(r"\s*以上来源于:.*$", "", raw).strip()
    if not raw or len(raw) < 2:
        return None
    pd = _parse_youdao_defs(raw)
    if not pd:
        return None
    return {"phonetic": "", "pos_defs": pd, "collocations": {},
            "examples": [], "checklist": [], "source": "basic"}


# ======== Fallback & lookup ========

def _gen_fallbacks(word):
    w = word.lower().strip()
    variants = []
    if " " in w:
        variants += [w.replace(" ", ""), w.replace(" ", "-")]
    paren = re.findall(r"\(([a-z]+)\)", w)
    if paren:
        base = re.sub(r"\([a-z]+\)", "", w)
        variants.append(base)
        for p in paren:
            variants.append(base + p)
    if "/" in w:
        parts = [p.strip() for p in w.split("/")]
        variants.extend(parts)
    return variants


def _try_fetch(word):
    url = YOUDAO_URL.format(word=urllib.parse.quote(word))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="replace")
    except Exception:
        return None


def lookup_word(word, cache):
    is_acronym = word.isupper() and len(word) >= 2
    wl = word.strip() if is_acronym else word.lower().strip()
    if wl in cache:
        return cache[wl]
    candidates = [wl]
    if not is_acronym:
        candidates += _gen_fallbacks(wl)
    tried = set()
    best = None
    for c in candidates:
        if c in tried:
            continue
        tried.add(c)
        if c in cache:
            r = cache[c]
            if r is not None and (best is None or r.get("source") == "collins"):
                best = r
                if r.get("source") == "collins":
                    break
            continue
        html = _try_fetch(c)
        if html:
            parsed = _parse_html(html)
            cache[c] = parsed
            if parsed is not None and (best is None or parsed.get("source") == "collins"):
                best = parsed
                if parsed.get("source") == "collins":
                    break
        else:
            cache[c] = None
    if best:
        result = {"word": word, "phonetic": best["phonetic"],
                  "pos_defs": best["pos_defs"],
                  "collocations": best.get("collocations", {}),
                  "examples": best.get("examples", []),
                  "checklist": best.get("checklist", []),
                  "source": best.get("source", "basic")}
        cache[wl] = result
        return result
    cache[wl] = None
    return None


# ======== Formatting ========

def _fmt_defs(defs):
    if not defs:
        return ""
    if len(defs) == 1:
        return defs[0]
    return "；".join(f"{CIRCLES[i]}{d}" for i, d in enumerate(defs) if i < len(CIRCLES))


def _build_line(trans, defs, colls):
    if not colls:
        return trans + _fmt_defs(defs)
    if len(defs) <= 1:
        return trans + _fmt_defs(defs) + " " + "/".join(f"+{p}" for p in colls)
    coll_map = defaultdict(list)
    for pp, meanings in colls.items():
        for m in meanings:
            if len(m) < 2:
                continue
            for i, d in enumerate(defs):
                clean = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", d)
                clean = re.sub(r"[（(][^)）]*[)）]", "", clean)
                if m in clean:
                    coll_map[i].append(f"+{pp}")
                    break
    if coll_map and len(coll_map) == len(defs) and \
       len(set(tuple(v) for v in coll_map.values())) == 1:
        return trans + "/".join(coll_map[0]) + _fmt_defs(defs)
    if coll_map:
        parts = []
        for i, d in enumerate(defs):
            c = CIRCLES[i] if i < len(CIRCLES) else f"({i + 1})"
            tags = " " + "/".join(coll_map.get(i, [])) if i in coll_map else ""
            parts.append(f"{c}{d}{tags}")
        return trans + "；".join(parts)
    return trans + "/".join(f"+{p}" for p in colls) + _fmt_defs(defs)


def format_entry(data):
    if not data or not data.get("pos_defs"):
        return "", []
    pd = data["pos_defs"]
    vd = [(t, d) for p, t, d in pd if p == "verb"]
    nv = [(p, t, d) for p, t, d in pd if p != "verb"]
    colls = data.get("collocations", {})
    all_lines = []
    if vd:
        merged_v = defaultdict(list)
        for t, d in vd:
            merged_v[t].extend(d)
        for t, defs in merged_v.items():
            all_lines.append(_build_line(t, defs, colls))
    mnv = defaultdict(list)
    for p, t, d in nv:
        mnv[(p, t)].extend(d)
    for (p, t), defs in mnv.items():
        all_lines.append(_build_line(t, defs, colls))
    return "；".join(all_lines), data.get("examples", [])


def _fmt_examples(entries):
    all_ex = []
    for idx, (_, _, examples) in enumerate(entries, 1):
        for ei, (en, cn) in enumerate(examples):
            c = CIRCLES[ei] if ei < len(CIRCLES) else f"({ei + 1})"
            all_ex.append((idx, c, en, cn))
    if not all_ex:
        return ""
    lines = ["\n例句："]
    for idx, c, en, cn in all_ex:
        lines.append(f"{idx}{c}{en}")
        lines.append(cn)
    return "\n".join(lines)


# ======== Main ========

def generate_notes(txt_dir, output_dir, cache):
    os.makedirs(output_dir, exist_ok=True)
    groups = {}
    for fp in sorted(Path(txt_dir).glob("*_wordlist.txt")):
        lt = fp.stem.replace("_wordlist", "")
        with open(fp, encoding="utf-8") as f:
            groups[lt] = [l.strip() for l in f if l.strip()]

    for letter in sorted(groups):
        words = groups[letter]
        out_path = os.path.join(output_dir, f"{letter}_wordlist.md")
        print(f"\n[lookup] {letter} ({len(words)} words) → {out_path}")
        entries = []
        missing = []
        found = 0
        checklist = []

        for wi, w in enumerate(words, 1):
            print(f"  [{wi}/{len(words)}] {w}", end="", flush=True)
            data = lookup_word(w, cache)
            if data is None:
                print(" [MISS]")
                missing.append(w)
            else:
                line, ex = format_entry(data)
                if line:
                    entries.append((w, line, ex))
                    found += 1
                    print(" [OK]")
                else:
                    print(" [?]")
                    missing.append(w)
                checklist.extend(data.get("checklist", []))
            time.sleep(REQUEST_DELAY)

        ts = time.strftime("%Y-%m-%d %H:%M")
        md = [f"# {letter}\n",
              f"> {len(words)} words | generated {ts} | found {found} | missing {len(missing)}\n"]
        for idx, (w, line, ex) in enumerate(entries, 1):
            md.append(f"{idx}.{w}    {line}\n")
        eb = _fmt_examples([(w, l, e) for w, l, e in entries])
        if eb:
            md.append(eb)
        if missing:
            md.append("\n## Missing words (no API result)\n")
            for mw in missing:
                md.append(f"- {mw}\n")
        if checklist:
            md.append("\n## ⚠ Checklist (manual review needed)\n")
            for ci in checklist:
                md.append(f"- {ci.get('w', '?')}: {ci.get('issue', '?')} | "
                          f"{ci.get('en', '')}{ci.get('cn', '')}\n")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
        print(f"  → {out_path}")


def main():
    p = argparse.ArgumentParser(description="Generate CET vocab MD notes via Youdao")
    p.add_argument("--txt-dir", help="Directory with *_wordlist.txt files")
    p.add_argument("-o", "--output-dir", default="output/notes")
    p.add_argument("--cache-dir", help="Cache directory")
    args = p.parse_args()

    if not args.txt_dir:
        print("Error: --txt-dir required")
        sys.exit(1)

    # Default cache: skills-CET/dict_cache.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cd = args.cache_dir or os.path.dirname(script_dir)
    os.makedirs(cd, exist_ok=True)
    cp = os.path.join(cd, CACHE_FILE)
    cache = {}
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            cache = json.load(f)
    try:
        generate_notes(args.txt_dir, args.output_dir, cache)
    finally:
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"\n  Cache: {cp}")


if __name__ == "__main__":
    main()
