import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from repo_fixtures import build_clean_fixture, build_drift_fixture
from spec_drift import __version__
from spec_drift.cli import main

requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


def test_providers_lists_available_adapters(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["providers"]) == 0

    assert capsys.readouterr().out.splitlines() == ["anthropic", "echo", "openai", "replay"]


def test_version_flag_reports_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])

    assert excinfo.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_help_flag_exits_cleanly_and_names_the_program(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])

    assert excinfo.value.code == 0
    assert "spec-drift" in capsys.readouterr().out


def test_missing_command_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([])

    assert excinfo.value.code == 2


def test_check_with_unknown_provider_fails_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--base", "HEAD", "--provider", "missing"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Supported providers: anthropic, echo, openai" in captured.err


@requires_git
def test_check_warns_when_using_the_default_echo_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = build_clean_fixture(tmp_path)
    monkeypatch.chdir(fixture.path)

    code = main(["check", "--base", fixture.base_ref])

    assert code == 1  # echo cannot judge, so the governed change is insufficient-evidence
    assert "the 'echo' provider cannot analyze drift" in capsys.readouterr().err


@requires_git
def test_check_model_flag_selects_the_replay_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = build_drift_fixture(tmp_path)
    replay = tmp_path / "replies.json"
    reply = json.dumps(
        {
            "classification": "drift",
            "source_line": 7,
            "document_path": "docs/specs/refunds.md",
            "document_line": 6,
            "summary": "removes the required approval check",
        }
    )
    replay.write_text(json.dumps({"src/refunds.py": reply}), encoding="utf-8")
    monkeypatch.chdir(fixture.path)

    # --model doubles as the replay file path for the replay provider.
    args = ["check", "--base", fixture.base_ref, "--provider", "replay", "--model", str(replay)]
    code = main(args)

    assert code == 1


def test_installed_console_script_reports_version() -> None:
    suffix = ".exe" if sys.platform == "win32" else ""
    executable = Path(sys.executable).with_name(f"spec-drift{suffix}")
    assert executable.is_file(), f"console script is not installed: {executable}"

    result = subprocess.run(
        [str(executable), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"spec-drift {__version__}"
