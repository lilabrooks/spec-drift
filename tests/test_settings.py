import pytest

from spec_drift.analysis.contract import DEFAULT_MAX_CONTEXT_CHARS
from spec_drift.config.settings import Settings


def test_settings_allow_provider_override() -> None:
    settings = Settings.from_env(provider_override="echo")

    assert settings.provider == "echo"


def test_model_override_beats_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_DRIFT_MODEL", "env-model")

    assert Settings.from_env(model_override="flag-model").model == "flag-model"


def test_max_context_chars_reads_a_positive_int(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_DRIFT_MAX_CONTEXT_CHARS", "12345")

    assert Settings.from_env().max_context_chars == 12345


@pytest.mark.parametrize("bad", ["not-a-number", "0", "-5"])
def test_max_context_chars_falls_back_on_invalid_values(
    bad: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPEC_DRIFT_MAX_CONTEXT_CHARS", bad)

    assert Settings.from_env().max_context_chars == DEFAULT_MAX_CONTEXT_CHARS


def test_max_context_chars_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_DRIFT_MAX_CONTEXT_CHARS", raising=False)

    assert Settings.from_env().max_context_chars == DEFAULT_MAX_CONTEXT_CHARS


def test_settings_model_defaults_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_DRIFT_MODEL", raising=False)

    settings = Settings.from_env()

    assert settings.model is None


def test_settings_reads_model_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_DRIFT_MODEL", "claude-sonnet-5")

    settings = Settings.from_env()

    assert settings.model == "claude-sonnet-5"
