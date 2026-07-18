from dataclasses import dataclass, field

from spec_drift.core.messages import Message


@dataclass(frozen=True, slots=True)
class CompletionRequest:
    messages: tuple[Message, ...]
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompletionResponse:
    text: str
    model: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
