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

from spec_drift.analysis.contract import (
    DEFAULT_MAX_CONTEXT_CHARS,
    GovernedInput,
    build_request,
    context_size,
    parse_finding,
)
from spec_drift.analysis.finding import AnalysisReport, Classification, Finding
from spec_drift.core.ports import LanguageModel
from spec_drift.inputs import git
from spec_drift.inputs.model import ChangeSet, ResolvedChange


def _insufficient(path: str, summary: str) -> Finding:
    return Finding(path=path, classification=Classification.INSUFFICIENT_EVIDENCE, summary=summary)


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


def _judge(
    root: Path,
    base: str,
    change: ResolvedChange,
    model: LanguageModel,
    *,
    max_context_chars: int,
) -> Finding:
    path = change.file.path
    documents = _read_documents(root, change)
    if not documents:
        return _insufficient(path, "governing documents could not be read")

    diff = git.load_file_diff(root, base, path, change.file.old_path)
    if not diff.strip():
        # A nonzero git exit or a genuinely empty diff: judge nothing unseen.
        return _insufficient(path, "no diff was available for the change")

    governed = GovernedInput(path=path, diff=diff, documents=documents)
    if context_size(governed) > max_context_chars:
        # Bounded mechanically (GOAL § Constraints): report insufficient
        # evidence rather than let the provider silently truncate the material.
        return _insufficient(
            path,
            f"evidence ({context_size(governed)} chars) exceeds the "
            f"{max_context_chars}-character context bound; cannot judge without truncating",
        )

    reply = model.complete(build_request(governed)).text
    return parse_finding(governed, reply)


def analyze(
    changeset: ChangeSet,
    model: LanguageModel,
    *,
    strict_coverage: bool = False,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> AnalysisReport:
    """Classify every retained change in ``changeset``.

    Governed changes are judged by ``model``; unmapped changes are recorded as
    ``unmapped``. Excluded paths never reach analysis. A governed change whose
    diff is unavailable, or whose evidence exceeds ``max_context_chars``, is
    reported as ``insufficient-evidence`` — never truncated silently.
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
            findings.append(
                _judge(
                    root,
                    changeset.base,
                    change,
                    model,
                    max_context_chars=max_context_chars,
                )
            )
    return AnalysisReport(
        findings=tuple(findings),
        strict_coverage=strict_coverage,
        excluded=changeset.excluded,
    )
