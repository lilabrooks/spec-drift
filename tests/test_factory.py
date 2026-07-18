import pytest

from spec_drift.config.settings import Settings
from spec_drift.providers.anthropic import DEFAULT_MODEL as ANTHROPIC_DEFAULT_MODEL
from spec_drift.providers.anthropic import AnthropicLanguageModel
from spec_drift.providers.registry import available_providers, create_provider
from spec_drift.runtime.factory import build_model


def test_unknown_provider_fails_with_supported_provider_names() -> None:
    with pytest.raises(ValueError, match="Supported providers: anthropic, echo, openai, replay"):
        build_model(Settings(provider="missing"))


def test_registry_lists_available_providers() -> None:
    assert available_providers() == ["anthropic", "echo", "openai", "replay"]


def test_create_provider_returns_working_adapter() -> None:
    model = create_provider("echo")

    assert model.__class__.__name__ == "EchoLanguageModel"


def test_create_provider_passes_model_override_through() -> None:
    model = create_provider("anthropic", model="claude-sonnet-5")

    assert isinstance(model, AnthropicLanguageModel)
    assert model._model == "claude-sonnet-5"


def test_create_provider_falls_back_to_adapter_default_model() -> None:
    model = create_provider("anthropic")

    assert isinstance(model, AnthropicLanguageModel)
    assert model._model == ANTHROPIC_DEFAULT_MODEL


def test_create_provider_ignores_model_override_for_echo() -> None:
    model = create_provider("echo", model="claude-sonnet-5")

    assert model.__class__.__name__ == "EchoLanguageModel"
