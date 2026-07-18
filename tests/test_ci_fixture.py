"""Milestone 6 verification: the ci-fixture demonstration.

Runs ``scripts/ci-fixture.py`` — the same script ``make ci-fixture`` and the
example workflow run — and confirms it drives the real ``check`` command to
fail on a drift fixture and pass on a clean one, printing both Markdown reports.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "ci-fixture.py"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


def test_ci_fixture_demonstration_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "drift exit code: 1" in result.stdout
    assert "clean exit code: 0" in result.stdout
    assert "| src/refunds.py | drift |" in result.stdout  # the drift report is Markdown
    assert "demonstration passed" in result.stdout
