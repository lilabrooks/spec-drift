#!/usr/bin/env python3
"""Demonstrate the CI integration locally (ADR 0002).

Builds two throwaway git repositories — one whose change drifts from its
governing spec, one whose change is clean — and runs the real ``spec-drift
check`` command against each with the deterministic ``replay`` provider. The
drift repository must fail (exit 1), the clean one must pass (exit 0). Both
Markdown reports are printed. This is the same sequence the example workflow
runs, so ``make ci-fixture`` and CI stay in lock-step. Offline: no network, no
vendor key.

Exit status: 0 when both repositories behave as expected, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SPEC = """\
---
type: Spec
title: Refund processing
---

# Refund processing

- Refunds above 100 USD require manager approval before they are issued.
"""

OKF_MAP = 'mappings:\n  - source: "src/refunds.py"\n    docs:\n      - "docs/specs/refunds.md"\n'

BASE_SOURCE = '''\
"""Refund processing governed by docs/specs/refunds.md."""


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    if amount_usd > 100 and not manager_approved:
        raise PermissionError("manager approval required")
    return f"refunded {amount_usd} to {user}"
'''

DRIFT_SOURCE = '''\
"""Refund processing governed by docs/specs/refunds.md."""


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    return f"refunded {amount_usd} to {user}"
'''

CLEAN_SOURCE = '''\
"""Refund processing governed by docs/specs/refunds.md."""

import logging

logger = logging.getLogger(__name__)


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    if amount_usd > 100 and not manager_approved:
        raise PermissionError("manager approval required")
    logger.info("refund issued")
    return f"refunded {amount_usd} to {user}"
'''

DRIFT_REPLY = json.dumps(
    {
        "classification": "drift",
        "source_line": 5,
        "document_path": "docs/specs/refunds.md",
        "document_line": 7,
        "summary": "the change removes the required manager-approval check",
    }
)
CLEAN_REPLY = json.dumps(
    {"classification": "clean", "source_line": None, "summary": "consistent with the spec"}
)

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "CI Fixture",
    "GIT_AUTHOR_EMAIL": "ci@example.invalid",
    "GIT_COMMITTER_NAME": "CI Fixture",
    "GIT_COMMITTER_EMAIL": "ci@example.invalid",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
}


def _git(repo: Path, *args: str) -> None:
    # Pass a fixed identity so commits work in CI, where no global git user is
    # configured; GIT_CONFIG_GLOBAL=/dev/null keeps the run hermetic.
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={**os.environ, **_GIT_ENV},
    )


def _write(repo: Path, relative: str, text: str) -> None:
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def build_repo(root: Path, name: str, changed_source: str) -> Path:
    repo = root / name
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _write(repo, "docs/specs/refunds.md", SPEC)
    _write(repo, "docs/okf-map.yml", OKF_MAP)
    _write(repo, "src/refunds.py", BASE_SOURCE)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "branch", "base")
    _write(repo, "src/refunds.py", changed_source)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "change")
    return repo


def run_check(repo: Path, reply: str) -> int:
    replay_file = repo / "replay.json"
    replay_file.write_text(json.dumps({"src/refunds.py": reply}), encoding="utf-8")
    executable = Path(sys.executable).with_name("spec-drift")
    result = subprocess.run(
        [
            str(executable),
            "check",
            "--base",
            "base",
            "--provider",
            "replay",
            "--format",
            "markdown",
        ],
        cwd=repo,
        env={**os.environ, **_GIT_ENV, "SPEC_DRIFT_REPLAY_FILE": str(replay_file)},
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        drift = build_repo(root, "drift", DRIFT_SOURCE)
        clean = build_repo(root, "clean", CLEAN_SOURCE)

        sys.stdout.write("=== drift fixture (must fail the build) ===\n")
        drift_code = run_check(drift, DRIFT_REPLY)
        sys.stdout.write(f"\ndrift exit code: {drift_code}\n\n")

        sys.stdout.write("=== clean fixture (must pass the build) ===\n")
        clean_code = run_check(clean, CLEAN_REPLY)
        sys.stdout.write(f"\nclean exit code: {clean_code}\n\n")

    ok = drift_code == 1 and clean_code == 0
    if ok:
        sys.stdout.write("CI fixture demonstration passed: drift failed, clean passed.\n")
        return 0
    sys.stderr.write(
        f"CI fixture demonstration FAILED: expected drift=1/clean=0, got "
        f"drift={drift_code}/clean={clean_code}.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
