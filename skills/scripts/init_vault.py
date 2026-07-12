#!/usr/bin/env python3
"""
Initialize an Obsidian vault for CET-4/6 English vocabulary notes.

Usage:
  python init_english_vault.py --vault-dir <path> [--notes-dir <path>]

Creates the vault structure and imports CET-4/CET-6 wordlist notes.
"""

import argparse, os, shutil, sys
from pathlib import Path

HOME_NOTE = """# English Vocabulary

CET-4/6 英语词汇笔记库。

## 结构

- `CET4/` — 四级独有词笔记（按字母分文件）
- `CET6/` — 六级词笔记（按字母分文件）

## 使用方式

1. 浏览 `CET4/` 或 `CET6/` 目录查看各字母段词汇
2. 每个词条包含：词性、中文释义、搭配、例句
3. 文件末尾 `⚠ Checklist` 标注了需要人工审核的条目
"""

CET4_README = """# CET-4 四级独有词汇

> 四级考试大纲中超出高考考纲的独有词汇。

按字母浏览：
"""

CET6_README = """# CET-6 六级词汇

> 六级考试大纲词汇（含 ★ 标记词）。

按字母浏览：
"""


def init_vault(vault_dir: str, notes_dir: str | None = None) -> None:
    """Initialize the English vocabulary Obsidian vault."""
    vault = Path(vault_dir)
    os.makedirs(vault, exist_ok=True)

    # Create .obsidian for vault recognition
    obsidian_dir = vault / ".obsidian"
    os.makedirs(obsidian_dir, exist_ok=True)

    # Write vault home
    with open(vault / "README.md", "w", encoding="utf-8") as f:
        f.write(HOME_NOTE)

    # Create CET4/CET6 directories
    cet4_dir = vault / "CET4"
    cet6_dir = vault / "CET6"
    os.makedirs(cet4_dir, exist_ok=True)
    os.makedirs(cet6_dir, exist_ok=True)

    # Write directory readmes
    with open(cet4_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(CET4_README)
    with open(cet6_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(CET6_README)

    # --- Import notes if source directory provided ---
    if notes_dir:
        notes_path = Path(notes_dir)
        imported = 0
        for level in ["CET4", "CET6"]:
            src = notes_path / level
            dst = vault / level
            if src.exists():
                for fpath in src.glob("*_wordlist.md"):
                    # Rename: A_wordlist.md → A - Wordlist.md
                    letter = fpath.stem.replace("_wordlist", "")
                    dst_name = f"{letter} - Wordlist.md"
                    shutil.copy2(fpath, dst / dst_name)
                    imported += 1
                    print(f"  Imported: {level}/{dst_name}")
        print(f"\n  Total imported: {imported} files")

    print(f"\n  Vault created: {vault}")
    print(f"  Open in Obsidian: File → Open Vault → {vault}")


def main():
    p = argparse.ArgumentParser(description="Init English vocabulary Obsidian vault")
    p.add_argument("--vault-dir", required=True, help="Path for new Obsidian vault")
    p.add_argument("--notes-dir", help="Path to generated CET4/CET6 MD notes (output/notes)")
    args = p.parse_args()
    init_vault(args.vault_dir, args.notes_dir)


if __name__ == "__main__":
    main()
