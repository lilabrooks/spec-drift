"""Milestone 3 verification: the drift-analysis engine and finding model.

Golden tests drive ``analyze`` against real fixture repositories with a
deterministic scripted provider, reproducing each classification with valid
citations, and confirm ``--strict-coverage`` flips the unmapped fixture's exit
code. Focused tests cover the untrusted-output validation from ADR 0001.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from repo_fixtures import build_clean_fixture, build_drift_fixture
from scripted_model import (
    ScriptedModel,
    clean_reply,
    decision_required_reply,
    drift_reply,
    insufficient_reply,
)
from spec_drift.analysis import AnalysisReport, Classification, Finding, analyze
from spec_drift.analysis.contract import GovernedInput, build_request, parse_finding
from spec_drift.inputs import collect_changes

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")

REFUNDS = "src/refunds.py"
REFUNDS_SPEC = "docs/specs/refunds.md"


def _analyze(tmp_path, build, model, *, strict_coverage=False):  # type: ignore[no-untyped-def]
    fixture = build(tmp_path)
    changeset = collect_changes(fixture.path, fixture.base_ref)
    return analyze(changeset, model, strict_coverage=strict_coverage)


def _finding(report: AnalysisReport, path: str) -> Finding:
    for finding in report.findings:
        if finding.path == path:
            return finding
    raise AssertionError(f"no finding for {path}")


# --- golden classifications ----------------------------------------------------


def test_drift_is_reproduced_with_both_citations(tmp_path: Path) -> None:
    model = ScriptedModel(
        replies={REFUNDS: drift_reply(source_line=7, document_path=REFUNDS_SPEC, document_line=6)}
    )
    report = _analyze(tmp_path, build_drift_fixture, model)

    finding = _finding(report, REFUNDS)
    assert finding.classification is Classification.DRIFT
    assert finding.source is not None and finding.source.path == REFUNDS
    assert finding.source.line == 7
    assert finding.document is not None and finding.document.path == REFUNDS_SPEC
    assert finding.document.line == 6
    assert report.exit_code() == 1
    assert model.calls == [REFUNDS]  # exactly one model call for the one governed change


def test_clean_is_reproduced(tmp_path: Path) -> None:
    model = ScriptedModel(replies={REFUNDS: clean_reply()})
    report = _analyze(tmp_path, build_clean_fixture, model)

    finding = _finding(report, REFUNDS)
    assert finding.classification is Classification.CLEAN
    assert report.exit_code() == 0


def test_decision_required_is_reproduced(tmp_path: Path) -> None:
    model = ScriptedModel(
        replies={
            REFUNDS: decision_required_reply(
                source_line=7, document_path=REFUNDS_SPEC, document_line=6
            )
        }
    )
    report = _analyze(tmp_path, build_drift_fixture, model)

    assert _finding(report, REFUNDS).classification is Classification.DECISION_REQUIRED
    assert report.exit_code() == 1


def test_insufficient_evidence_is_reproduced(tmp_path: Path) -> None:
    model = ScriptedModel(replies={REFUNDS: insufficient_reply()})
    report = _analyze(tmp_path, build_drift_fixture, model)

    assert _finding(report, REFUNDS).classification is Classification.INSUFFICIENT_EVIDENCE
    assert report.exit_code() == 1


def test_unmapped_change_is_recorded_without_a_model_call(tmp_path: Path) -> None:
    # The clean fixture governs only src/refunds.py; add an unmapped change.
    fixture = build_clean_fixture(tmp_path)
    (fixture.path / "src" / "extra.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(fixture.path), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(fixture.path), "commit", "-q", "-m", "add unmapped file"], check=True
    )

    model = ScriptedModel(replies={REFUNDS: clean_reply()})
    changeset = collect_changes(fixture.path, fixture.base_ref)
    report = analyze(changeset, model)

    assert _finding(report, "src/extra.py").classification is Classification.UNMAPPED
    assert model.calls == [REFUNDS]  # unmapped change triggered no model call


# --- the strict-coverage exit-code flip ---------------------------------------


def test_unmapped_alone_does_not_fail_by_default() -> None:
    report = AnalysisReport(
        findings=(Finding(path="a.py", classification=Classification.UNMAPPED, summary="x"),)
    )
    assert report.exit_code() == 0


def test_strict_coverage_flips_unmapped_exit_code() -> None:
    findings = (Finding(path="a.py", classification=Classification.UNMAPPED, summary="x"),)
    assert AnalysisReport(findings, strict_coverage=False).exit_code() == 0
    assert AnalysisReport(findings, strict_coverage=True).exit_code() == 1


def test_counts_tallies_every_classification() -> None:
    report = AnalysisReport(
        findings=(
            Finding(path="a.py", classification=Classification.CLEAN, summary="x"),
            Finding(path="b.py", classification=Classification.DRIFT, summary="x"),
            Finding(path="c.py", classification=Classification.DRIFT, summary="x"),
        )
    )
    counts = report.counts()
    assert counts[Classification.DRIFT] == 2
    assert counts[Classification.CLEAN] == 1
    assert counts[Classification.UNMAPPED] == 0


# --- untrusted-output validation (ADR 0001) -----------------------------------


def _governed() -> GovernedInput:
    return GovernedInput(
        path=REFUNDS,
        diff="--- a\n+++ b\n",
        documents=((REFUNDS_SPEC, "spec text"),),
    )


def test_build_request_includes_diff_and_documents() -> None:
    request = build_request(_governed())
    user = next(m.content for m in request.messages if m.role == "user")
    assert f"Changed file: {REFUNDS}" in user
    assert "unified diff" in user
    assert REFUNDS_SPEC in user


def test_unparseable_reply_becomes_insufficient() -> None:
    finding = parse_finding(_governed(), "not json at all")
    assert finding.classification is Classification.INSUFFICIENT_EVIDENCE


def test_unknown_classification_becomes_insufficient() -> None:
    finding = parse_finding(_governed(), '{"classification": "totally-made-up"}')
    assert finding.classification is Classification.INSUFFICIENT_EVIDENCE


def test_model_may_not_self_assign_unmapped() -> None:
    finding = parse_finding(_governed(), '{"classification": "unmapped"}')
    assert finding.classification is Classification.INSUFFICIENT_EVIDENCE


def test_drift_without_citations_is_downgraded() -> None:
    finding = parse_finding(_governed(), '{"classification": "drift", "summary": "bad"}')
    assert finding.classification is Classification.INSUFFICIENT_EVIDENCE


def test_drift_citing_a_document_outside_the_map_is_downgraded() -> None:
    reply = drift_reply(source_line=3, document_path="docs/specs/other.md", document_line=1)
    finding = parse_finding(_governed(), reply)
    assert finding.classification is Classification.INSUFFICIENT_EVIDENCE


def test_code_fenced_json_is_accepted() -> None:
    reply = "```json\n" + clean_reply() + "\n```"
    finding = parse_finding(_governed(), reply)
    assert finding.classification is Classification.CLEAN
