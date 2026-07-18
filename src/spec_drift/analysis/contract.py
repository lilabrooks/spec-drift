"""Build the model request for one governed change and validate the reply.

This module *is* the provider contract from ADR 0001: the prompt wording and
the JSON keys are a compatibility surface. Model output is untrusted, so
``parse_finding`` never raises on bad input — it downgrades anything it cannot
verify to ``insufficient-evidence``, which is the safe, non-inventing outcome.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from spec_drift.analysis.finding import JUDGED, Citation, Classification, Finding
from spec_drift.core.messages import Message
from spec_drift.core.models import CompletionRequest

SYSTEM_PROMPT = (
    "You classify whether a source change has drifted from the documentation "
    "that governs it. You are given a unified diff for one file and the full "
    "text of the governing specifications and architecture decision records "
    "(ADRs). Accepted ADRs override the implementation when they disagree.\n\n"
    "Classify the change as exactly one of:\n"
    "- clean: the change is consistent with the governing documents.\n"
    "- drift: the change contradicts a specification or accepted ADR.\n"
    "- decision-required: the change alters an architecture boundary "
    "(dependency, persistence, auth, public API, deployment) with no "
    "corresponding decision record.\n"
    "- insufficient-evidence: the governing documents do not let you judge "
    "the change.\n\n"
    "Reply with ONLY a JSON object and no prose:\n"
    '{"classification": "...", "source_line": <int or null>, '
    '"document_path": "<repo-relative path or null>", '
    '"document_line": <int or null>, "summary": "<one sentence>"}\n'
    "For drift and decision-required you MUST cite source_line and a "
    "document_path/document_line drawn from the documents provided."
)


@dataclass(frozen=True, slots=True)
class GovernedInput:
    """Everything the model needs to judge one governed change."""

    path: str
    diff: str
    documents: tuple[tuple[str, str], ...]  # (repo-relative path, full text)

    @property
    def document_paths(self) -> frozenset[str]:
        return frozenset(path for path, _ in self.documents)


def build_request(governed: GovernedInput) -> CompletionRequest:
    """Assemble the single completion request for a governed change."""
    documents = "\n\n".join(
        f"=== document: {path} ===\n{text}" for path, text in governed.documents
    )
    user = f"Changed file: {governed.path}\n\n=== unified diff ===\n{governed.diff}\n\n{documents}"
    return CompletionRequest(
        messages=(
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=user),
        )
    )


def _insufficient(path: str, summary: str) -> Finding:
    return Finding(
        path=path,
        classification=Classification.INSUFFICIENT_EVIDENCE,
        summary=summary,
    )


def _coerce_line(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def parse_finding(governed: GovernedInput, reply: str) -> Finding:
    """Validate an untrusted model reply into a Finding for ``governed``.

    Anything that cannot be verified — unparseable JSON, an unknown
    classification, a document citation outside the governing set, or a
    judged classification missing its required evidence — becomes
    ``insufficient-evidence`` rather than a trusted verdict.
    """
    text = _strip_code_fence(reply.strip())
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return _insufficient(governed.path, "model output was not valid JSON")
    if not isinstance(payload, dict):
        return _insufficient(governed.path, "model output was not a JSON object")

    raw = payload.get("classification")
    try:
        classification = Classification(raw)
    except ValueError:
        return _insufficient(governed.path, f"model returned unknown classification {raw!r}")
    if classification not in JUDGED:
        return _insufficient(governed.path, "model may not assign this classification")

    summary = payload.get("summary")
    summary_text = (
        summary if isinstance(summary, str) and summary.strip() else "no summary provided"
    )

    source_line = _coerce_line(payload.get("source_line"))
    document_path = payload.get("document_path")
    document_line = _coerce_line(payload.get("document_line"))

    document: Citation | None = None
    if isinstance(document_path, str) and document_path in governed.document_paths:
        document = Citation(path=document_path, line=document_line)

    requires_evidence = classification in {Classification.DRIFT, Classification.DECISION_REQUIRED}
    if requires_evidence and (source_line is None or document is None):
        return _insufficient(
            governed.path,
            "model classified drift without citing both the change and a governing document",
        )

    source = Citation(path=governed.path, line=source_line) if source_line is not None else None
    return Finding(
        path=governed.path,
        classification=classification,
        summary=summary_text,
        source=source,
        document=document,
    )


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    # Drop the opening fence (optionally ```json) and a trailing fence.
    body = lines[1:]
    if body and body[-1].strip() == "```":
        body = body[:-1]
    return "\n".join(body)
