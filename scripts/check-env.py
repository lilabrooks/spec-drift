#!/usr/bin/env python3
"""Preflight for file-sync damage (iCloud and similar) in this checkout.

Folder syncing corrupts tool-managed state in ways CI never sees: macOS
hidden flags land on files under .venv (Python 3.13+ skips hidden .pth
files, so editable installs and console scripts fail with import errors),
conflict copies appear as " 2"-suffixed files and directories, and evicted
content leaves ".icloud" placeholders. This check runs first in `make check`
and turns that damage into one actionable failure instead of a debugging
session. Pass an explicit root to check a tree other than this repository.
"""

from __future__ import annotations

import re
import stat
import sys
from pathlib import Path

SYNC_DUPLICATE = re.compile(r" \d+(\.[^/ ]+)?$")
TOOL_DIRS = (".venv", ".venv.nosync", ".mypy_cache", ".pytest_cache", ".ruff_cache")
VENV_DIRS = (".venv", ".venv.nosync")


def is_flag_hidden(path: Path) -> bool:
    st = path.lstat()
    hidden_flags = getattr(st, "st_flags", 0) & getattr(stat, "UF_HIDDEN", 0)
    hidden_attributes = getattr(st, "st_file_attributes", 0) & getattr(
        stat, "FILE_ATTRIBUTE_HIDDEN", 0
    )
    return bool(hidden_flags or hidden_attributes)


def unique_directories(root: Path, names: tuple[str, ...]) -> list[Path]:
    """Return existing directories once, preferring real paths over symlinks."""
    candidates = [root / name for name in names if (root / name).is_dir()]
    candidates.sort(key=lambda path: path.is_symlink())
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def hidden_pth_files(root: Path) -> list[Path]:
    flagged: list[Path] = []
    for venv in unique_directories(root, VENV_DIRS):
        flagged.extend(path for path in sorted(venv.rglob("*.pth")) if is_flag_hidden(path))
    return flagged


def is_tool_directory_copy(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any(re.fullmatch(rf"{re.escape(name)} \d+", path.name) for name in TOOL_DIRS)


def sync_duplicates(root: Path) -> list[Path]:
    found = [path for path in sorted(root.iterdir()) if is_tool_directory_copy(path)]
    for tool_dir in unique_directories(root, TOOL_DIRS):
        for current, dirnames, filenames in tool_dir.walk():
            found.extend(
                current / entry
                for entry in sorted(dirnames + filenames)
                if SYNC_DUPLICATE.search(entry)
            )
            dirnames[:] = [d for d in dirnames if not SYNC_DUPLICATE.search(d)]
    return found


def icloud_placeholders(root: Path) -> list[Path]:
    return [path for path in sorted(root.rglob("*.icloud")) if path.name.startswith(".")]


def describe(paths: list[Path], root: Path, limit: int = 5) -> str:
    shown = [str(path.relative_to(root)) for path in paths[:limit]]
    listing = "\n".join(f"    {entry}" for entry in shown)
    remaining = len(paths) - len(shown)
    if remaining > 0:
        listing += f"\n    … and {remaining} more"
    return listing


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parent.parent

    problems: list[str] = []

    hidden = hidden_pth_files(root)
    if hidden:
        venv_dirs = sorted({path.relative_to(root).parts[0] for path in hidden})
        problems.append(
            f"{len(hidden)} hidden .pth file(s) in the virtual environment — Python 3.13+\n"
            "  skips hidden .pth files, so editable installs and console scripts break\n"
            "  with import errors while pytest still passes:\n"
            f"{describe(hidden, root)}\n"
            f"  Fix: chflags -R nohidden {' '.join(venv_dirs)}  (or recreate the venv)"
        )

    duplicates = sync_duplicates(root)
    if duplicates:
        problems.append(
            f"{len(duplicates)} sync-conflict duplicate(s) in tool directories:\n"
            f"{describe(duplicates, root)}\n"
            "  Fix: delete and recreate the affected directories (.venv, caches)"
        )

    placeholders = icloud_placeholders(root)
    if placeholders:
        problems.append(
            f"{len(placeholders)} .icloud placeholder(s) — file contents were evicted\n"
            "  to the cloud and are not on disk:\n"
            f"{describe(placeholders, root)}\n"
            "  Fix: download the originals (open the folder in Finder), then move the\n"
            "  checkout out of the synced folder before .git objects get evicted"
        )

    if problems:
        sys.stderr.write(
            "Environment check failed: this checkout shows file-sync damage\n"
            "(iCloud or similar).\n\n"
        )
        for problem in problems:
            sys.stderr.write(f"- {problem}\n")
        sys.stderr.write(
            "\nDurable fix: keep working checkouts outside synced folders (e.g. ~/code,\n"
            "not an iCloud-synced ~/Documents). If that is temporarily impossible,\n"
            ".venv.nosync with a .venv symlink may reduce venv churn on some sync\n"
            "tools, but it is a best-effort fallback rather than a guarantee.\n"
        )
        return 1

    sys.stdout.write("environment ok\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
