"""Contract tests for the git fixture repositories.

Later milestones point drift analysis at these repos, so their shape is
guarded here: each builds a real git repository with a resolvable ``base``
ref, a governed source change on ``main``, and the kit-convention knowledge
layout (``docs/specs/`` plus ``docs/okf-map.yml``). The drift fixture must
lose its approval check relative to base; the clean fixture must keep it.
Everything runs offline in a temporary directory.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from repo_fixtures import (
    BASE_REF,
    FixtureRepo,
    build_clean_fixture,
    build_drift_fixture,
)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _show(fixture: FixtureRepo, ref: str, path: str) -> str:
    return _git(fixture.path, "show", f"{ref}:{path}")


@pytest.fixture(name="clean_repo")
def clean_repo_fixture(tmp_path: Path) -> FixtureRepo:
    return build_clean_fixture(tmp_path)


@pytest.fixture(name="drift_repo")
def drift_repo_fixture(tmp_path: Path) -> FixtureRepo:
    return build_drift_fixture(tmp_path)


def test_fixture_is_a_git_repo_with_resolvable_base(clean_repo: FixtureRepo) -> None:
    assert (clean_repo.path / ".git").is_dir()
    assert clean_repo.base_ref == BASE_REF
    base = _git(clean_repo.path, "rev-parse", BASE_REF).strip()
    head = _git(clean_repo.path, "rev-parse", "HEAD").strip()
    assert base and head and base != head


def test_fixture_carries_kit_convention_knowledge(clean_repo: FixtureRepo) -> None:
    assert (clean_repo.path / "docs" / "specs" / "refunds.md").is_file()
    map_text = (clean_repo.path / "docs" / "okf-map.yml").read_text(encoding="utf-8")
    assert "src/refunds.py" in map_text
    assert "docs/specs/refunds.md" in map_text


def test_change_touches_only_the_governed_source(clean_repo: FixtureRepo) -> None:
    changed = _git(clean_repo.path, "diff", "--name-only", BASE_REF, "HEAD").split()
    assert changed == ["src/refunds.py"]


def test_clean_fixture_keeps_the_required_approval_check(clean_repo: FixtureRepo) -> None:
    base_source = _show(clean_repo, BASE_REF, "src/refunds.py")
    head_source = _show(clean_repo, "HEAD", "src/refunds.py")
    assert "manager_approved" in base_source
    assert "PermissionError" in head_source, "clean change must preserve the approval check"
    assert "logger.info" in head_source, "clean change should still be a real change"


def test_drift_fixture_removes_the_required_approval_check(drift_repo: FixtureRepo) -> None:
    base_source = _show(drift_repo, BASE_REF, "src/refunds.py")
    head_source = _show(drift_repo, "HEAD", "src/refunds.py")
    assert "PermissionError" in base_source
    assert "PermissionError" not in head_source, "drift change must drop the approval check"
    spec = _show(drift_repo, "HEAD", "docs/specs/refunds.md")
    assert "manager approval" in spec, "the governing spec still requires approval"


def test_fixture_builds_are_deterministic(tmp_path: Path) -> None:
    first = build_drift_fixture(tmp_path / "a")
    second = build_drift_fixture(tmp_path / "b")
    assert _git(first.path, "rev-parse", "HEAD") == _git(second.path, "rev-parse", "HEAD")
