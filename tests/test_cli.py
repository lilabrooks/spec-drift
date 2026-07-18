import subprocess
import sys
from pathlib import Path

import pytest

from spec_drift import __version__
from spec_drift.cli import main


def test_hello_greets_the_world_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["hello"]) == 0

    assert capsys.readouterr().out == "Hello, world!\n"


def test_hello_greets_a_named_target(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["hello", "team"]) == 0

    assert capsys.readouterr().out == "Hello, team!\n"


def test_providers_lists_available_adapters(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["providers"]) == 0

    assert capsys.readouterr().out.splitlines() == ["anthropic", "echo", "openai"]


def test_ask_routes_through_the_echo_provider(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ask", "ping", "--provider", "echo"]) == 0

    assert capsys.readouterr().out == "Echo provider received: ping\n"


def test_ask_honors_provider_from_environment(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPEC_DRIFT_PROVIDER", "echo")

    assert main(["ask", "ping"]) == 0

    assert capsys.readouterr().out == "Echo provider received: ping\n"


def test_ask_with_unknown_provider_fails_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ask", "ping", "--provider", "missing"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Supported providers: anthropic, echo, openai" in captured.err


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
