from dataclasses import dataclass
from os import environ

from spec_drift.analysis.contract import DEFAULT_MAX_CONTEXT_CHARS

DEFAULT_PROVIDER = "echo"


def _read_positive_int(name: str, default: int) -> int:
    """Read a positive integer from the environment, or fall back to ``default``.

    A missing, non-numeric, or non-positive value uses the default rather than
    failing the run — the bound is a safety mechanism, not required input.
    """
    raw = environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True, slots=True)
class Settings:
    provider: str = DEFAULT_PROVIDER
    model: str | None = None
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS

    @classmethod
    def from_env(
        cls,
        provider_override: str | None = None,
        *,
        model_override: str | None = None,
    ) -> "Settings":
        provider = provider_override or environ.get("SPEC_DRIFT_PROVIDER", DEFAULT_PROVIDER)
        model = model_override or environ.get("SPEC_DRIFT_MODEL")
        max_context_chars = _read_positive_int(
            "SPEC_DRIFT_MAX_CONTEXT_CHARS", DEFAULT_MAX_CONTEXT_CHARS
        )
        return cls(provider=provider, model=model, max_context_chars=max_context_chars)
