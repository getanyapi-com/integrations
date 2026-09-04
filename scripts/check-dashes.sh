#!/usr/bin/env bash
# Reject em (U+2014) and en (U+2013) dash glyphs anywhere in this repository.
# AnyAPI copy uses ASCII "-" or a rephrase; see the root CLAUDE.md hard rules.
#
# This is deliberately NOT `grep -P`. BSD grep on macOS rejects -P outright, and
# an earlier version of this script hid that failure by sending stderr to
# /dev/null inside an `if`, so the non-zero exit skipped the failure branch and
# the guard reported "clean" on a file that did contain an em dash. A guard that
# cannot fail is worse than no guard, so the scan runs in Python, which is
# present wherever this runs and behaves the same on macOS and on CI.
#
# The banned characters are written as escapes so this file never contains the
# glyphs it rejects and can therefore scan itself.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - "$PWD" <<'PY'
import pathlib
import sys

BANNED = {"\u2013": "en dash (U+2013)", "\u2014": "em dash (U+2014)"}
SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".sh", ".cfg", ".txt"}
SKIP_DIRS = {
    ".git", ".venv", "venv", ".devenv", ".preflight", ".depcheck",
    "site-packages", "dist", "build", "__pycache__", ".mypy_cache",
    ".ruff_cache", ".pytest_cache", "node_modules",
}

root = pathlib.Path(sys.argv[1])
hits = []
scanned = 0
for path in root.rglob("*"):
    if not path.is_file() or path.suffix not in SUFFIXES:
        continue
    parts = set(path.relative_to(root).parts)
    if SKIP_DIRS & parts or any(p.endswith(".egg-info") for p in parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    scanned += 1
    for lineno, line in enumerate(text.splitlines(), 1):
        for glyph, label in BANNED.items():
            if glyph in line:
                hits.append(
                    f"{path.relative_to(root)}:{lineno}: {label}: {line.strip()}"
                )

if hits:
    print("em or en dash glyphs found; use ASCII '-' or rephrase:")
    for hit in hits:
        print(f"  {hit}")
    raise SystemExit(1)
print(f"dash guard: clean ({scanned} files scanned)")
PY
