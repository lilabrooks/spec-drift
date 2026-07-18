"""Milestone 5 verification: safe report-file output.

``--output`` writes the report to a file that stays within the working
directory, refuses traversal, preserves an existing file without ``--force``,
and — when forced — replaces only the selected report. Driven through
``run_check`` with a scripted model against a real fixture repository.
"""

import shutil
from pathlib import Path

import pytest

from repo_fixtures import build_clean_fixture
from scripted_model import ScriptedModel, clean_reply
from spec_drift.checker import CheckOptions, run_check
from spec_drift.report import ReportFormat

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")

REFUNDS = "src/refunds.py"


def _model() -> ScriptedModel:
    return ScriptedModel(replies={REFUNDS: clean_reply()})


def test_output_writes_the_report_and_keeps_stdout_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    fixture = build_clean_fixture(tmp_path)
    code = run_check(
        fixture.path,
        fixture.base_ref,
        _model(),
        CheckOptions(ReportFormat.JSON, output="report.json"),
    )
    assert code == 0
    captured = capsys.readouterr()
    assert captured.out == ""  # stdout stays clean when writing a file
    assert "wrote report.json" in captured.err
    written = (fixture.path / "report.json").read_text(encoding="utf-8")
    assert '"exit_code": 0' in written


def test_output_stays_within_the_working_directory(tmp_path: Path) -> None:
    fixture = build_clean_fixture(tmp_path)
    (fixture.path / "reports").mkdir()
    code = run_check(
        fixture.path,
        fixture.base_ref,
        _model(),
        CheckOptions(ReportFormat.JSON, output="reports/out.json"),
    )
    assert code == 0
    assert (fixture.path / "reports" / "out.json").is_file()


def test_traversal_path_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    fixture = build_clean_fixture(tmp_path)
    code = run_check(
        fixture.path,
        fixture.base_ref,
        _model(),
        CheckOptions(ReportFormat.JSON, output="../escape.json"),
    )
    assert code == 2
    assert "refusing to write outside" in capsys.readouterr().err
    assert not (tmp_path / "escape.json").exists()  # never created outside the repo


def test_absolute_path_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    fixture = build_clean_fixture(tmp_path)
    outside = tmp_path / "outside.json"  # an absolute path outside the repo
    code = run_check(
        fixture.path,
        fixture.base_ref,
        _model(),
        CheckOptions(ReportFormat.JSON, output=str(outside)),
    )
    assert code == 2
    assert "refusing to write outside" in capsys.readouterr().err
    assert not outside.exists()


def test_existing_file_is_preserved_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    fixture = build_clean_fixture(tmp_path)
    target = fixture.path / "report.json"
    target.write_text("ORIGINAL", encoding="utf-8")

    code = run_check(
        fixture.path,
        fixture.base_ref,
        _model(),
        CheckOptions(ReportFormat.JSON, output="report.json"),
    )
    assert code == 2
    assert "already exists" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "ORIGINAL"  # untouched


def test_force_replaces_only_the_selected_report(tmp_path: Path) -> None:
    fixture = build_clean_fixture(tmp_path)
    target = fixture.path / "report.json"
    target.write_text("ORIGINAL", encoding="utf-8")
    bystander = fixture.path / "keep.txt"
    bystander.write_text("KEEP", encoding="utf-8")

    code = run_check(
        fixture.path,
        fixture.base_ref,
        _model(),
        CheckOptions(ReportFormat.JSON, output="report.json", force=True),
    )
    assert code == 0
    assert target.read_text(encoding="utf-8") != "ORIGINAL"  # replaced
    assert '"exit_code": 0' in target.read_text(encoding="utf-8")
    assert bystander.read_text(encoding="utf-8") == "KEEP"  # only the report changed
