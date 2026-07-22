"""Deterministic, offline model providers for analysis tests.

A real provider is a network call to a vendor; these stand in for it so tests
reproduce golden classifications without a key or a network. Each implements
the ``LanguageModel`` protocol (``complete``) and returns canned reply text.

``ScriptedModel`` routes by the changed-file path that ``contract.build_request``
places in the user message, so one instance can drive a multi-change fixture —
returning drift for one file, clean for another — exactly as a real run would.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from spec_drift.core.models import CompletionRequest, CompletionResponse


@dataclass
class ScriptedModel:
    """Return a preset reply per changed-file path; a default for the rest."""

    replies: dict[str, str] = field(default_factory=dict)
    default: str = '{"classification": "clean", "summary": "no drift"}'
    calls: list[str] = field(default_factory=list)

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        user = next((message.content for message in request.messages if message.role == "user"), "")
        for marker, reply in self.replies.items():
            if f"Changed file: {marker}\n" in user:
                self.calls.append(marker)
                return CompletionResponse(text=reply, model="scripted")
        self.calls.append("<default>")
        return CompletionResponse(text=self.default, model="scripted")


def drift_reply(*, source_line: int, document_path: str, document_line: int) -> str:
    return (
        '{"classification": "drift", '
        f'"source_line": {source_line}, '
        f'"document_path": "{document_path}", '
        f'"document_line": {document_line}, '
        '"summary": "the change removes a required approval check"}'
    )


def clean_reply() -> str:
    return '{"classification": "clean", "source_line": null, "summary": "consistent with the spec"}'


def decision_required_reply(*, source_line: int, document_path: str, document_line: int) -> str:
    return (
        '{"classification": "decision-required", '
        f'"source_line": {source_line}, '
        f'"document_path": "{document_path}", '
        f'"document_line": {document_line}, '
        '"summary": "alters an architecture boundary with no decision record"}'
    )


def insufficient_reply() -> str:
    return '{"classification": "insufficient-evidence", "summary": "cannot judge from the docs"}'
