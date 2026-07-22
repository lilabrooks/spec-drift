#!/usr/bin/env python3
"""Fail if a tracked file contains a hardcoded credential (ADR 0004).

Dependency-free by design: reads the tracked file set from ``git ls-files`` and
matches known key/token prefixes, private-key blocks, and long secrets assigned
to key-like names. Placeholder values and any line carrying the marker
``# pragma: allowlist secret`` are ignored. This is a first line of defense, not
a guarantee — see ADR 0004 for the tradeoff and the revisit trigger.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_MARKER = "pragma: allowlist secret"

# Values that are obviously not real secrets, so a match on them is a false
# positive rather than a leak.
_PLACEHOLDER_RE = re.compile(
    r"your[-_].*here|example|placeholder|changeme|dummy|redacted|sample|"
    r"fake|xxxx|<[^>]*>|\.\.\.|\{[a-z_]+\}",
    re.IGNORECASE,
)

# Known credential shapes. Each requires enough key material after the prefix
# that the pattern text below cannot match itself.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anthropic/openai key", re.compile(r"sk-(?:ant-)?[A-Za-z0-9]{20,}")),
    ("aws access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github token", re.compile(r"gh[posru]_[A-Za-z0-9]{36}")),
    ("github pat", re.compile(r"github_pat_[A-Za-z0-9_]{22,}")),
    ("slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google api key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("private key block", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
)

# A long literal assigned to a key-like name: KEY = "…", token: "…", etc.
_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    \b(?:api[_-]?key|secret|token|password|passwd|access[_-]?key|client[_-]?secret)\b
    \s*[:=]\s*
    ["']([A-Za-z0-9/_+=.\-]{16,})["']
    """
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    payload = result.stdout.decode("utf-8", "surrogateescape")
    return [Path(name) for name in payload.split("\0") if name]


def scan_text(text: str) -> list[tuple[int, str]]:
    """Return ``(line number, reason)`` for each suspected secret in ``text``."""
    findings: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOWLIST_MARKER in line:
            continue
        for label, pattern in _PATTERNS:
            if pattern.search(line):
                findings.append((lineno, label))
        match = _ASSIGNMENT_RE.search(line)
        if match and not _PLACEHOLDER_RE.search(match.group(1)):
            findings.append((lineno, "hardcoded secret assignment"))
    return findings


def main() -> int:
    errors: list[str] = []
    for path in tracked_files():
        try:
            text = (REPO_ROOT / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable file carries no reviewable text
        for lineno, label in scan_text(text):
            errors.append(f"{path}:{lineno}: possible {label}")

    if errors:
        sys.stderr.write(
            "secret scan failed — remove the hardcoded secret, or mark a genuine "
            "false positive with '# pragma: allowlist secret':\n"
        )
        for error in errors:
            sys.stderr.write(f"- {error}\n")
        return 1

    sys.stdout.write("no hardcoded secrets found\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
