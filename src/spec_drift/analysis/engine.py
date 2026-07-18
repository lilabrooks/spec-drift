"""Turn a resolved ChangeSet into an AnalysisReport.

For each governed change the engine gathers the file's diff and its governing
documents, asks the model once (ADR 0001: one call per unit, no retry loop),
and validates the reply into a finding. Unmapped changes are recorded as
``unmapped`` without any model call — the engine never invents a contract for a
change the map does not govern. It is read-only and provider-neutral: any
`LanguageModel`, including an offline fixture, drives it.
"""

from __future__ import annotations

from pathlib import Path

from spec_drift.analysis.contract import GovernedInput, build_request, parse_finding
from spec_drift.analysis.finding import AnalysisReport, Classification, Finding
from spec_drift.core.ports import LanguageModel
from spec_drift.inputs import git
from spec_drift.inputs.model import ChangeSet, ResolvedChange


def _read_documents(root: Path, change: ResolvedChange) -> tuple[tuple[str, str], ...]:
    documents: list[tuple[str, str]] = []
    for doc in change.governing_docs:
        try:
            text = (root / doc).read_text(encoding="utf-8")
        except OSError:
            # A mapped document that is missing on disk is not evidence; skip it
            # so the model judges only against documents that actually exist.
            continue
        documents.append((doc, text))
    return tuple(documents)


def _judge(root: Path, base: str, change: ResolvedChange, model: LanguageModel) -> Finding:
    documents = _read_documents(root, change)
    if not documents:
        return Finding(
            path=change.file.path,
            classification=Classification.INSUFFICIENT_EVIDENCE,
            summary="governing documents could not be read",
        )
    governed = GovernedInput(
        path=change.file.path,
        diff=git.load_file_diff(root, base, change.file.path),
        documents=documents,
    )
    reply = model.complete(build_request(governed)).text
    return parse_finding(governed, reply)


def analyze(
    changeset: ChangeSet,
    model: LanguageModel,
    *,
    strict_coverage: bool = False,
) -> AnalysisReport:
    """Classify every retained change in ``changeset``.

    Governed changes are judged by ``model``; unmapped changes are recorded as
    ``unmapped``. Excluded paths never reach analysis.
    """
    root = Path(changeset.root)
    findings: list[Finding] = []
    for change in changeset.included:
        if change.is_unmapped:
            findings.append(
                Finding(
                    path=change.file.path,
                    classification=Classification.UNMAPPED,
                    summary="no governing document maps to this change",
                )
            )
        else:
            findings.append(_judge(root, changeset.base, change, model))
    return AnalysisReport(findings=tuple(findings), strict_coverage=strict_coverage)
