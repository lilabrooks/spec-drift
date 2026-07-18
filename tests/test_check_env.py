"""Smoke tests for scripts/check-env.py.

The preflight is the only place file-sync damage (iCloud and similar) can be
caught: CI runners never see macOS hidden flags, and the failure it prevents
(a console script that cannot import its own package while pytest passes) is
otherwise diagnosed three layers away from its cause. Each test builds a
damaged tree in tmp_path and asserts the script names the damage.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-env.py"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_clean_tree_passes(tmp_path: Path) -> None:
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / "src").mkdir()

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "environment ok" in result.stdout


def test_flags_sync_conflict_duplicates(tmp_path: Path) -> None:
    duplicate_dir = tmp_path / ".venv" / "lib 2"
    duplicate_dir.mkdir(parents=True)
    pycache = tmp_path / ".venv" / "lib" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "module.cpython-314 2.pyc").write_bytes(b"")

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "lib 2" in result.stderr
    assert "module.cpython-314 2.pyc" in result.stderr


def test_flags_conflict_copy_of_tool_directory(tmp_path: Path) -> None:
    (tmp_path / ".venv 2").mkdir()

    result = _run(tmp_path)

    assert result.returncode == 1
    assert ".venv 2" in result.stderr
    assert "best-effort fallback rather than a guarantee" in result.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="directory symlinks need extra privileges")
def test_deduplicates_symlinked_environment(tmp_path: Path) -> None:
    (tmp_path / ".venv.nosync" / "lib 2").mkdir(parents=True)
    (tmp_path / ".venv").symlink_to(".venv.nosync", target_is_directory=True)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "1 sync-conflict duplicate(s)" in result.stderr
    assert result.stderr.count("lib 2") == 1


def test_flags_icloud_placeholders(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / ".cli.py.icloud").write_bytes(b"")

    result = _run(tmp_path)

    assert result.returncode == 1
    assert ".cli.py.icloud" in result.stderr


@pytest.mark.skipif(sys.platform != "darwin", reason="UF_HIDDEN is a macOS file flag")
def test_flags_hidden_pth_files(tmp_path: Path) -> None:
    site_packages = tmp_path / ".venv" / "lib" / "python3.14" / "site-packages"
    site_packages.mkdir(parents=True)
    pth = site_packages / "_editable_impl_pkg.pth"
    pth.write_text("/nowhere\n", encoding="utf-8")
    subprocess.run(["chflags", "hidden", str(pth)], check=True)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "_editable_impl_pkg.pth" in result.stderr
    assert "chflags -R nohidden" in result.stderr


def test_ignores_project_files_with_spaced_names(tmp_path: Path) -> None:
    """Only tool-managed directories are scanned for duplicates: a user file
    like "notes 2.md" in a generated project must not fail the gate."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "notes 2.md").write_text("legit\n", encoding="utf-8")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
