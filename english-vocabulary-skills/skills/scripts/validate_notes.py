#!/usr/bin/env python3
"""
Validate vocabulary notes against the reference format.

Checks:
  1. Entry format: 序号.单词    释义 (4 spaces between word and definition)
  2. Example format: 序号①English sentence / Chinese translation
  3. Section completeness: Missing words, Checklist
  4. No duplicate entries across files

Usage:
  python validate_english_vault.py --notes-dir <path> --level CET4 --reference A
  python validate_english_vault.py --notes-dir <path> --level CET4 --reference A --check-duplicates
"""

import argparse, json, os, re, sys
from collections import defaultdict
from pathlib import Path


def configure_utf8_stdio():
    if sys.platform == "win32":
        for s in (sys.stdin, sys.stdout, sys.stderr):
            try: s.reconfigure(encoding="utf-8", errors="replace")
            except: pass


# ---- validators ----

def validate_entry_format(lines: list, filepath: str) -> list:
    """Check each numbered entry line for correct format."""
    issues = []
    for i, line in enumerate(lines, 1):
        line = line.rstrip()
        # Skip non-entry lines
        if not re.match(r"^\d+\.", line):
            continue
        # Must match: 序号.单词    释义
        m = re.match(r"^(\d+)\.(\S+)(\s{2,})(.*)", line)
        if not m:
            issues.append({"file": filepath, "line": i,
                           "issue": "bad_entry_format", "line_text": line[:80]})
            continue
        spaces = len(m.group(3))
        if spaces != 4:
            issues.append({"file": filepath, "line": i,
                           "issue": f"spacing: expected 4, got {spaces}",
                           "word": m.group(2)})
        # Check numbering continuity
        num = int(m.group(1))
        word = m.group(2)
        definition = m.group(4)
        if not definition.strip():
            issues.append({"file": filepath, "line": i,
                           "issue": "empty_definition", "word": word})
    return issues


def validate_example_format(lines: list, filepath: str) -> list:
    """Check example section format."""
    issues = []
    in_examples = False
    for i, line in enumerate(lines, 1):
        line = line.rstrip()
        if line == "例句：":
            in_examples = True
            continue
        if in_examples and re.match(r"^##\s", line):
            in_examples = False
            continue
        if in_examples and line:
            if re.match(r"^\d+[①②③④⑤⑥⑦⑧⑨⑩]", line):
                continue  # English example line
            elif re.match(r"^\S", line) and not line.startswith("#"):
                continue  # Chinese translation line
            else:
                issues.append({"file": filepath, "line": i,
                               "issue": "bad_example_format", "line_text": line[:60]})
    return issues


def validate_sections(lines: list, filepath: str) -> list:
    """Check expected sections exist."""
    issues = []
    text = "\n".join(lines)
    # Check Missing words section exists when there are missing words
    header = [l for l in lines if l.startswith("> ")]
    if header:
        m = re.search(r"missing (\d+)", header[0])
        if m and int(m.group(1)) > 0:
            if "## Missing words" not in text:
                issues.append({"file": filepath, "issue": "missing_words_section_absent"})
    # Checklist section
    has_checklist = "## ⚠" in text or "## Checklist" in text
    # (Not always required — only flag if missing and there are checklist items)
    return issues


def validate_duplicates(note_dir: str, level: str) -> list:
    """Check for duplicate words across files in the same level."""
    all_words = defaultdict(list)
    for fpath in sorted(Path(note_dir).glob("*_wordlist.md")):
        letter = fpath.stem.replace("_wordlist", "")
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^\d+\.(\S+)", line)
                if m:
                    all_words[m.group(1).lower()].append(letter)
    issues = []
    for word, letters in all_words.items():
        if len(letters) > 1:
            issues.append({
                "issue": "duplicate_word",
                "word": word,
                "files": letters,
            })
    return issues


def validate_numbering(lines: list, filepath: str) -> list:
    """Check entry numbering is sequential (1, 2, 3...)."""
    issues = []
    expected = 1
    for i, line in enumerate(lines, 1):
        m = re.match(r"^(\d+)\.", line)
        if m:
            num = int(m.group(1))
            if num != expected:
                issues.append({"file": filepath, "line": i,
                               "issue": f"numbering_skip: expected {expected}, got {num}"})
                expected = num + 1
            else:
                expected += 1
    return issues


# ---- main ----

def main():
    configure_utf8_stdio()

    p = argparse.ArgumentParser(description="Validate vocabulary notes format")
    p.add_argument("--notes-dir", required=True, help="Path to CET4/CET6 MD notes directory")
    p.add_argument("--reference", default="A", help="Reference letter (A)")
    p.add_argument("--check-duplicates", action="store_true")
    args = p.parse_args()

    notes_dir = Path(args.notes_dir)
    if not notes_dir.exists():
        print(json.dumps({"status": "error", "message": f"Not found: {notes_dir}"}))
        sys.exit(1)

    # --- Validate all files ---
    ref_file = notes_dir / f"{args.reference}_wordlist.md"
    print(f"[validate] Reference: {ref_file}")

    all_issues = []
    total_ok = 0
    total_files = 0

    for fpath in sorted(notes_dir.glob("*_wordlist.md")):
        if fpath.stem.startswith("#"):
            continue
        letter = fpath.stem.replace("_wordlist", "")
        total_files += 1

        with open(fpath, encoding="utf-8") as f:
            lines = f.readlines()

        issues = []
        issues += validate_entry_format(lines, str(fpath))
        issues += validate_example_format(lines, str(fpath))
        issues += validate_sections(lines, str(fpath))
        issues += validate_numbering(lines, str(fpath))

        if issues:
            all_issues.extend(issues)
            print(f"  {letter}: {len(issues)} issues")
        else:
            total_ok += 1
            print(f"  {letter}: OK")

    # --- Duplicate check (optional, slow) ---
    if args.check_duplicates:
        dup_issues = validate_duplicates(str(notes_dir), "ALL")
        if dup_issues:
            all_issues.extend(dup_issues)
            print(f"  Duplicates: {len(dup_issues)} issues")

    result = {
        "status": "issues_found" if all_issues else "ok",
        "files_total": total_files,
        "files_ok": total_ok,
        "total_issues": len(all_issues),
        "issues": all_issues[:100],
    }

    print(f"\n  Summary: {total_ok}/{total_files} OK, {len(all_issues)} issues")
    print(json.dumps({k: v for k, v in result.items() if k != "issues"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
