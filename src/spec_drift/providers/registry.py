"""Single source of truth for provider adapters.

The factory, the unknown-provider error, and the `providers` command all read
from `_PROVIDERS`. Add a real vendor by importing its adapter and adding one
entry here.
"""

from collections.abc import Callable

from spec_drift.core.ports import LanguageModel
from spec_drift.providers.anthropic import AnthropicLanguageModel
from spec_drift.providers.echo import EchoLanguageModel
from spec_drift.providers.openai import OpenAILanguageModel
from spec_drift.providers.replay import ReplayLanguageModel


def _create_echo(model: str | None) -> LanguageModel:
    del model  # echo has no underlying model to select
    return EchoLanguageModel()


def _create_replay(model: str | None) -> LanguageModel:
    # `model` is the replay-file path when given; otherwise the env var is used.
    return ReplayLanguageModel(replay_file=model)


def _create_anthropic(model: str | None) -> LanguageModel:
    return AnthropicLanguageModel(model=model) if model else AnthropicLanguageModel()


def _create_openai(model: str | None) -> LanguageModel:
    return OpenAILanguageModel(model=model) if model else OpenAILanguageModel()


_PROVIDERS: dict[str, Callable[[str | None], LanguageModel]] = {
    "echo": _create_echo,
    "replay": _create_replay,
    "anthropic": _create_anthropic,
    "openai": _create_openai,
}


def available_providers() -> list[str]:
    return sorted(_PROVIDERS)


def create_provider(name: str, *, model: str | None = None) -> LanguageModel:
    try:
        factory = _PROVIDERS[name]
    except KeyError:
        supported = ", ".join(available_providers())
        msg = f"Unknown provider {name!r}. Supported providers: {supported}."
        raise ValueError(msg) from None
    return factory(model)
