#!/usr/bin/env python3
"""
Export auto-generated wordlist notes to a local directory.

Usage:
  python export_notes.py --notes-dir ./output/notes --target "D:/CET-Wordlists"

Creates the target directory and copies CET4/CET6 MD files into it.
Existing files are overwritten (this is the initial version, not the edited vault).
"""

import argparse, os, shutil, sys
from pathlib import Path


def export(notes_dir: str, target_dir: str) -> None:
    src = Path(notes_dir)
    dst = Path(target_dir)

    if not src.exists():
        print(f"Error: source not found: {src}")
        sys.exit(1)

    os.makedirs(dst, exist_ok=True)
    copied = 0

    for level in ["CET4", "CET6"]:
        level_src = src / level
        if not level_src.exists():
            print(f"  Skip: {level} (not found)")
            continue
        level_dst = dst / level
        os.makedirs(level_dst, exist_ok=True)

        for fpath in sorted(level_src.glob("*_wordlist.md")):
            letter = fpath.stem.replace("_wordlist", "")
            dst_name = f"{letter} - Wordlist.md"
            shutil.copy2(fpath, level_dst / dst_name)
            copied += 1
            print(f"  {level}/{dst_name}")

        # Also copy any checklist or meta files
        for extra in level_src.glob("*.json"):
            shutil.copy2(extra, level_dst / extra.name)
            print(f"  {level}/{extra.name}")

    print(f"\n  Exported {copied} files to {dst}")


def main():
    p = argparse.ArgumentParser(description="Export wordlist notes to local directory")
    p.add_argument("--notes-dir", required=True, help="Source notes directory (output/notes)")
    p.add_argument("--target", required=True, help="Target directory for wordlist files")
    args = p.parse_args()
    export(args.notes_dir, args.target)


if __name__ == "__main__":
    main()
