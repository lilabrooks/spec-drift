from typing import TYPE_CHECKING

from spec_drift.core.models import CompletionRequest, CompletionResponse
from spec_drift.core.ports import ProviderError

if TYPE_CHECKING:
    from anthropic.types import MessageParam

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 1024


class AnthropicLanguageModel:
    """Provider adapter backed by the Anthropic Claude API.

    Requires the `anthropic` package (`pip install ".[anthropic]"`). The
    import is deferred to `complete()` so the rest of the CLI keeps working
    without it installed.
    """

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        try:
            import anthropic  # noqa: PLC0415 (kept optional; see module docstring)
        except ImportError as error:
            msg = (
                "the 'anthropic' provider needs the anthropic package: "
                "pip install 'spec-drift[anthropic]'"
            )
            raise ProviderError(msg) from error

        # Built with per-role branches so each dict matches the MessageParam
        # role literal ("user" | "assistant"); a shared dict[str, str] does not.
        messages: list[MessageParam] = []
        for message in request.messages:
            if message.role == "user":
                messages.append({"role": "user", "content": message.content})
            elif message.role == "assistant":
                messages.append({"role": "assistant", "content": message.content})
        system = "\n\n".join(
            message.content for message in request.messages if message.role == "system"
        )

        try:
            client = anthropic.Anthropic()
            # Two literal call shapes instead of a **kwargs expansion: the SDK's
            # overloads don't accept an untyped dict, and the "no system prompt"
            # contract is that the kwarg is absent, not None.
            if system:
                response = client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    messages=messages,
                    system=system,
                )
            else:
                response = client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    messages=messages,
                )
            text = "".join(block.text for block in response.content if block.type == "text")
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            return CompletionResponse(text=text, model=response.model, usage=usage)
        except Exception as error:  # any SDK/auth/network failure -> exit-code-2 contract
            raise ProviderError(f"anthropic request failed: {error}") from error
