"""Builders for the git fixture repositories spec-drift's tests analyze.

Each builder creates a real, self-contained git repository under a caller
supplied directory (a pytest ``tmp_path``), emulating a target repo that
follows the claude-okf-repo-kit convention: Markdown specs under
``docs/specs/``, a ``docs/okf-map.yml`` mapping source globs to governing
documents, and source code the spec governs.

Every fixture commits a ``base`` state, marks it with the ``base`` branch,
then commits a change on ``main`` — so ``--base base`` is the canonical
invocation against a fixture, mirroring ``--base origin/main`` in a real
repository. Builders are deterministic and offline: fixed author identity,
fixed timestamps, no network.

The two fixtures established here mirror the goal's success criteria:

- clean: the change agrees with the governing spec (a log line is added,
  the required approval check stays intact).
- drift: the change silently removes the manager-approval check the
  governing spec requires.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

BASE_REF = "base"

_FIXED_ENV = {
    "GIT_AUTHOR_NAME": "Fixture Author",
    "GIT_AUTHOR_EMAIL": "fixtures@example.invalid",
    "GIT_COMMITTER_NAME": "Fixture Author",
    "GIT_COMMITTER_EMAIL": "fixtures@example.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    # Ignore the machine's git configuration so fixture builds are identical
    # everywhere (no hooksPath, templates, or defaultBranch surprises).
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}

_REFUNDS_SPEC = """\
---
type: Spec
title: Refund processing
description: Contract for issuing refunds, including the approval boundary.
---

# Refund processing

- Refunds at or below 100 USD are issued immediately.
- Refunds above 100 USD require manager approval before they are issued.
- Every refund records the requesting user and amount.
"""

_OKF_MAP = """\
map:
  - source: "src/refunds.py"
    docs:
      - docs/specs/refunds.md
"""

_REFUNDS_BASE = '''\
"""Refund processing governed by docs/specs/refunds.md."""

APPROVAL_THRESHOLD_USD = 100


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    if amount_usd > APPROVAL_THRESHOLD_USD and not manager_approved:
        raise PermissionError("refunds above the threshold require manager approval")
    return f"refunded {amount_usd} USD to {user}"
'''

_REFUNDS_CLEAN_CHANGE = '''\
"""Refund processing governed by docs/specs/refunds.md."""

import logging

APPROVAL_THRESHOLD_USD = 100

logger = logging.getLogger(__name__)


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    if amount_usd > APPROVAL_THRESHOLD_USD and not manager_approved:
        raise PermissionError("refunds above the threshold require manager approval")
    logger.info("refund issued", extra={"user": user, "amount_usd": amount_usd})
    return f"refunded {amount_usd} USD to {user}"
'''

_REFUNDS_DRIFT_CHANGE = '''\
"""Refund processing governed by docs/specs/refunds.md."""

APPROVAL_THRESHOLD_USD = 100


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    return f"refunded {amount_usd} USD to {user}"
'''


@dataclass(frozen=True)
class FixtureRepo:
    """A built fixture repository and the ref its change should be diffed against."""

    path: Path
    base_ref: str


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **_FIXED_ENV},
    )
    return result.stdout


def _write(repo: Path, relative: str, content: str) -> None:
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _build(root: Path, name: str, changed_source: str) -> FixtureRepo:
    repo = root / name
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", _FIXED_ENV["GIT_AUTHOR_NAME"])
    _git(repo, "config", "user.email", _FIXED_ENV["GIT_AUTHOR_EMAIL"])

    _write(repo, "docs/specs/refunds.md", _REFUNDS_SPEC)
    _write(repo, "docs/okf-map.yml", _OKF_MAP)
    _write(repo, "src/refunds.py", _REFUNDS_BASE)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "Base: refund policy implemented per spec")
    _git(repo, "branch", BASE_REF)

    _write(repo, "src/refunds.py", changed_source)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "Change refund processing")
    return FixtureRepo(path=repo, base_ref=BASE_REF)


def build_clean_fixture(root: Path) -> FixtureRepo:
    """A repo whose change agrees with its governing spec."""
    return _build(root, "clean-repo", _REFUNDS_CLEAN_CHANGE)


def build_drift_fixture(root: Path) -> FixtureRepo:
    """A repo whose change removes the approval check its spec requires."""
    return _build(root, "drift-repo", _REFUNDS_DRIFT_CHANGE)
