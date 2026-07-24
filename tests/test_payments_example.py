"""The payments example: two classifications from one change set.

Drives the documented worked example through the shipped `replay` provider
(ADR 0002), so the pipeline the example claims — mapping, diff loading, reply
validation, citation checking, exit code — is asserted deterministically and
offline. The replay provider supplies the verdicts; what it proves is that a
real reply of that shape survives validation and renders as documented, not
that a model would produce it. Only the live run recorded in
`docs/case-studies/payments-idempotency.md` speaks to the model's judgment.
"""

import json
import shutil
from pathlib import Path

import pytest

from repo_fixtures import build_conflicting_docs_fixture, build_payments_fixture
from spec_drift.checker import CheckOptions, run_check
from spec_drift.inputs import collect_changes, git
from spec_drift.providers.replay import ReplayLanguageModel
from spec_drift.report import ReportFormat

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")

RETRY = "src/payments/retry.py"
WORKER = "src/payments/worker.py"
SPEC = "docs/specs/payment-execution.md"
ADR = "docs/adr/0002-payment-execution.md"


def _reply(classification: str, source_line: int, document: str, document_line: int, summary: str):
    return json.dumps(
        {
            "classification": classification,
            "source_line": source_line,
            "document_path": document,
            "document_line": document_line,
            "summary": summary,
        }
    )


def _replay_file(tmp_path: Path) -> str:
    path = tmp_path / "payments-replay.json"
    path.write_text(
        json.dumps(
            {
                RETRY: _reply(
                    "drift",
                    15,
                    SPEC,
                    20,
                    "Each attempt mints a fresh idempotency key; the spec requires reusing "
                    "the stored key so a retry is not charged as a new payment.",
                ),
                WORKER: _reply(
                    "decision-required",
                    6,
                    SPEC,
                    33,
                    "Introduces a background retry queue, an execution boundary no "
                    "governing document decides.",
                ),
            }
        ),
        encoding="utf-8",
    )
    return str(path)


def test_both_payment_files_are_governed_by_the_map(tmp_path: Path) -> None:
    fixture = build_payments_fixture(tmp_path)
    changeset = collect_changes(fixture.path, fixture.base_ref)
    governed = {change.file.path: change.governing_docs for change in changeset.governed}

    assert set(governed) == {RETRY, WORKER}  # both reach the model via src/payments/**
    for docs in governed.values():
        assert docs == (SPEC, ADR)
    assert changeset.unmapped == ()


def test_example_yields_drift_and_decision_required(tmp_path: Path) -> None:
    fixture = build_payments_fixture(tmp_path)
    model = ReplayLanguageModel(_replay_file(tmp_path))

    code = run_check(fixture.path, fixture.base_ref, model, CheckOptions(ReportFormat.JSON))
    assert code == 1


def test_rendered_report_carries_both_paired_citations(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    fixture = build_payments_fixture(tmp_path)
    model = ReplayLanguageModel(_replay_file(tmp_path))

    run_check(fixture.path, fixture.base_ref, model, CheckOptions(ReportFormat.JSON))
    report = json.loads(capsys.readouterr().out)

    findings = {finding["path"]: finding for finding in report["findings"]}
    assert findings[RETRY]["classification"] == "drift"
    assert findings[RETRY]["source"] == {"path": RETRY, "line": 15}
    assert findings[RETRY]["document"] == {"path": SPEC, "line": 20}

    assert findings[WORKER]["classification"] == "decision-required"
    assert findings[WORKER]["document"]["path"] == SPEC
    assert report["summary"]["drift"] == 1
    assert report["summary"]["decision-required"] == 1


def test_the_drifted_line_is_actually_in_the_diff(tmp_path: Path) -> None:
    # Guards the example's honesty: spec-drift only judges what the diff shows,
    # so the offending line must be part of the change, not pre-existing code.
    fixture = build_payments_fixture(tmp_path)
    diff = git.load_file_diff(Path(fixture.path), fixture.base_ref, RETRY)
    assert "+                idempotency_key=str(uuid.uuid4())," in diff
    assert "-                idempotency_key=payment.idempotency_key," in diff


# --- contradictory governing documents (ADR 0007) -----------------------------


def test_conflicting_docs_fixture_puts_both_sides_in_front_of_the_model(
    tmp_path: Path,
) -> None:
    """The property that makes the live conflict result meaningful.

    Both documents must reach the model, and they must actually disagree — a
    fixture where only one side is mapped, or where the texts happen to agree,
    would prove nothing about ADR 0007.
    """
    fixture = build_conflicting_docs_fixture(tmp_path)
    changeset = collect_changes(fixture.path, fixture.base_ref)

    governed = {change.file.path: change.governing_docs for change in changeset.governed}
    assert governed == {
        "src/exports/storage.py": (
            "docs/specs/export-delivery.md",
            "docs/adr/0003-signed-link-expiry.md",
        )
    }

    root = Path(changeset.root)
    spec = (root / "docs/specs/export-delivery.md").read_text(encoding="utf-8")
    adr = (root / "docs/adr/0003-signed-link-expiry.md").read_text(encoding="utf-8")
    assert "expires 24 hours" in spec  # the PR edited the spec to permit itself
    assert "**15 minutes**" in adr  # the accepted ADR was left untouched


def test_a_conflict_reply_round_trips_as_insufficient_evidence(tmp_path: Path) -> None:
    fixture = build_conflicting_docs_fixture(tmp_path)
    replay = tmp_path / "conflict-replay.json"
    replay.write_text(
        json.dumps(
            {
                "src/exports/storage.py": json.dumps(
                    {
                        "classification": "insufficient-evidence",
                        "source_line": 3,
                        "document_path": None,
                        "document_line": None,
                        "summary": "The spec (24 hours) and the accepted ADR (15 minutes) "
                        "disagree on link expiry, so the change cannot be judged.",
                    }
                )
            }
        ),
        encoding="utf-8",
    )
    model = ReplayLanguageModel(str(replay))

    code = run_check(fixture.path, fixture.base_ref, model, CheckOptions(ReportFormat.JSON))
    assert code == 1  # a conflict is actionable, not a pass
