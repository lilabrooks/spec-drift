from typing import Protocol

from spec_drift.core.models import CompletionRequest, CompletionResponse


class ProviderError(RuntimeError):
    """A provider could not produce a completion.

    Raised by an adapter when its SDK is missing, unauthenticated, or the
    request fails. The CLI maps it to exit code 2 with an actionable message,
    so a provider outage never surfaces as a raw stack trace.
    """


class LanguageModel(Protocol):
    """Minimal interface every provider adapter must implement."""

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Return a text completion for the given request.

        Adapters raise :class:`ProviderError` on any failure to reach the
        model, so callers can convert it to the exit-code-2 contract.
        """
