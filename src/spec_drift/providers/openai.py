from typing import TYPE_CHECKING

from spec_drift.core.models import CompletionRequest, CompletionResponse
from spec_drift.core.ports import ProviderError

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 1024


class OpenAILanguageModel:
    """Provider adapter backed by the OpenAI Chat Completions API.

    Requires the `openai` package (`pip install ".[openai]"`). The import is
    deferred to `complete()` so the rest of the CLI keeps working without it
    installed.
    """

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        try:
            import openai  # noqa: PLC0415 (kept optional; see module docstring)
        except ImportError as error:
            msg = "the 'openai' provider needs the openai package: pip install 'spec-drift[openai]'"
            raise ProviderError(msg) from error

        # Built with per-role branches so each dict matches its member of the
        # ChatCompletion*MessageParam union (a shared dict[str, str] does not).
        messages: list[ChatCompletionMessageParam] = []
        for message in request.messages:
            if message.role == "system":
                messages.append({"role": "system", "content": message.content})
            elif message.role == "user":
                messages.append({"role": "user", "content": message.content})
            elif message.role == "assistant":
                messages.append({"role": "assistant", "content": message.content})

        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=messages,
            )
            text = response.choices[0].message.content or ""
            usage = {}
            if response.usage is not None:
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                }
            return CompletionResponse(text=text, model=response.model, usage=usage)
        except Exception as error:  # any SDK/auth/network failure -> exit-code-2 contract
            raise ProviderError(f"openai request failed: {error}") from error
