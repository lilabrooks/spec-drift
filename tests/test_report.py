"""Milestone 4 verification: terminal, Markdown, and JSON reports; the JSON
report validates against the committed schema; the check command's exit codes
match the documented contract.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from repo_fixtures import build_clean_fixture, build_drift_fixture
from schema_check import SchemaError, validate
from scripted_model import ScriptedModel, drift_reply
from spec_drift.analysis import AnalysisReport, Citation, Classification, Finding
from spec_drift.checker import CheckOptions, run_check
from spec_drift.core.ports import ProviderError
from spec_drift.inputs.model import ExcludedFile, ExclusionReason
from spec_drift.report import ReportFormat, render, render_json, report_to_dict

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((REPO_ROOT / "schemas" / "report.schema.json").read_text(encoding="utf-8"))


def _sample_report() -> AnalysisReport:
    return AnalysisReport(
        findings=(
            Finding(
                path="src/refunds.py",
                classification=Classification.DRIFT,
                summary="removes the required approval check",
                source=Citation("src/refunds.py", 7),
                document=Citation("docs/specs/refunds.md", 6),
            ),
            Finding(
                path="src/newfeature.py",
                classification=Classification.UNMAPPED,
                summary="no governing document",
            ),
        )
    )


# --- all three formats describe the same findings ------------------------------


@pytest.mark.parametrize("report_format", list(ReportFormat))
def test_every_format_names_every_finding(report_format: ReportFormat) -> None:
    output = render(_sample_report(), report_format)
    for finding in _sample_report().findings:
        assert finding.path in output
        assert finding.classification.value in output


def test_terminal_reports_the_exit_summary() -> None:
    output = render(_sample_report(), ReportFormat.TERMINAL)
    assert "1 drift" in output and "1 unmapped" in output
    assert "exit 1" in output


def test_empty_report_renders_in_every_format() -> None:
    empty = AnalysisReport()
    assert render(empty, ReportFormat.TERMINAL) == "No governed or unmapped changes found."
    assert "No governed or unmapped changes found." in render(empty, ReportFormat.MARKDOWN)
    assert json.loads(render(empty, ReportFormat.JSON))["findings"] == []


# --- JSON validates against the committed schema -------------------------------


def test_json_output_validates_against_committed_schema() -> None:
    document = json.loads(render_json(_sample_report()))
    validate(document, SCHEMA)  # raises SchemaError on mismatch


def test_empty_and_strict_reports_validate() -> None:
    validate(json.loads(render_json(AnalysisReport())), SCHEMA)
    strict = AnalysisReport(_sample_report().findings, strict_coverage=True)
    document = json.loads(render_json(strict))
    validate(document, SCHEMA)
    assert document["exit_code"] == 1


# --- excluded paths are surfaced in every format -------------------------------


def _report_with_exclusions() -> AnalysisReport:
    return AnalysisReport(
        findings=(Finding(path="src/app.py", classification=Classification.CLEAN, summary="ok"),),
        excluded=(
            ExcludedFile(path=".env", reason=ExclusionReason.ENV_FILE),
            ExcludedFile(path="deploy/server.pem", reason=ExclusionReason.CREDENTIAL),
        ),
    )


@pytest.mark.parametrize("report_format", [ReportFormat.TERMINAL, ReportFormat.MARKDOWN])
def test_excluded_paths_appear_in_text_formats(report_format: ReportFormat) -> None:
    output = render(_report_with_exclusions(), report_format)
    assert "deploy/server.pem" in output
    assert "credential" in output
    assert ".env" in output


def test_excluded_paths_appear_in_json_and_validate() -> None:
    document = json.loads(render_json(_report_with_exclusions()))
    assert document["excluded"] == [
        {"path": ".env", "reason": "env-file"},
        {"path": "deploy/server.pem", "reason": "credential"},
    ]
    validate(document, SCHEMA)


def test_empty_report_has_an_empty_excluded_array() -> None:
    document = json.loads(render_json(AnalysisReport()))
    assert document["excluded"] == []
    validate(document, SCHEMA)


def test_schema_validator_rejects_bad_documents() -> None:
    good = report_to_dict(_sample_report())
    validate(good, SCHEMA)

    missing = {k: v for k, v in good.items() if k != "findings"}
    with pytest.raises(SchemaError):
        validate(missing, SCHEMA)

    bad_classification = report_to_dict(_sample_report())
    findings = bad_classification["findings"]
    assert isinstance(findings, list)
    findings[0]["classification"] = "made-up"
    with pytest.raises(SchemaError):
        validate(bad_classification, SCHEMA)

    extra = report_to_dict(_sample_report())
    extra["unexpected"] = True
    with pytest.raises(SchemaError):
        validate(extra, SCHEMA)


# --- the check command's exit-code contract ------------------------------------

pytestmark_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


@pytestmark_git
def test_check_exit_zero_when_nothing_changed(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    fixture = build_clean_fixture(tmp_path)
    code = run_check(fixture.path, "HEAD", ScriptedModel(), CheckOptions(ReportFormat.TERMINAL))
    assert code == 0
    assert "No governed or unmapped changes" in capsys.readouterr().out


@pytestmark_git
def test_check_exit_one_on_drift(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    fixture = build_drift_fixture(tmp_path)
    model = ScriptedModel(
        replies={
            "src/refunds.py": drift_reply(
                source_line=7, document_path="docs/specs/refunds.md", document_line=6
            )
        }
    )
    code = run_check(fixture.path, fixture.base_ref, model, CheckOptions(ReportFormat.JSON))
    assert code == 1
    document = json.loads(capsys.readouterr().out)
    validate(document, SCHEMA)
    assert document["exit_code"] == 1


@pytestmark_git
def test_check_exit_two_on_invalid_base(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    fixture = build_clean_fixture(tmp_path)
    code = run_check(
        fixture.path, "no-such-ref", ScriptedModel(), CheckOptions(ReportFormat.TERMINAL)
    )
    assert code == 2
    assert "error:" in capsys.readouterr().err


@pytestmark_git
def test_check_exit_two_outside_repository(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = run_check(tmp_path, "HEAD", ScriptedModel(), CheckOptions(ReportFormat.TERMINAL))
    assert code == 2
    assert "error:" in capsys.readouterr().err


class _RaisingModel:
    """A provider that fails to reach the model, like a missing API key would."""

    def complete(self, request: object) -> object:  # noqa: ARG002
        raise ProviderError("anthropic request failed: missing ANTHROPIC_API_KEY")


@pytestmark_git
def test_check_exit_two_on_provider_failure(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    fixture = build_drift_fixture(tmp_path)
    code = run_check(
        fixture.path, fixture.base_ref, _RaisingModel(), CheckOptions(ReportFormat.TERMINAL)
    )
    assert code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "missing ANTHROPIC_API_KEY" in captured.err  # actionable message, no traceback


@pytestmark_git
def test_check_exit_two_on_malformed_map(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    fixture = build_clean_fixture(tmp_path)
    (fixture.path / "docs" / "okf-map.yml").write_text("mappings:\n  garbage\n", encoding="utf-8")
    code = run_check(
        fixture.path, fixture.base_ref, ScriptedModel(), CheckOptions(ReportFormat.TERMINAL)
    )
    assert code == 2
    assert "error:" in capsys.readouterr().err


def test_installed_check_command_runs_end_to_end(tmp_path: Path) -> None:
    """The console script drives the whole path with the default echo provider,
    which cannot judge, so a governed change becomes insufficient-evidence."""
    if shutil.which("git") is None:
        pytest.skip("git is required")
    fixture = build_drift_fixture(tmp_path)
    executable = Path(sys.executable).with_name("spec-drift")
    result = subprocess.run(
        [str(executable), "check", "--base", fixture.base_ref, "--format", "json"],
        cwd=fixture.path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    document = json.loads(result.stdout)
    validate(document, SCHEMA)
    classifications = {finding["classification"] for finding in document["findings"]}
    assert classifications == {"insufficient-evidence"}
