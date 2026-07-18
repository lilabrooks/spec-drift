import pytest

from spec_drift.config.settings import Settings


def test_settings_allow_provider_override() -> None:
    settings = Settings.from_env(provider_override="echo")

    assert settings.provider == "echo"


def test_settings_model_defaults_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_DRIFT_MODEL", raising=False)

    settings = Settings.from_env()

    assert settings.model is None


def test_settings_reads_model_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_DRIFT_MODEL", "claude-sonnet-5")

    settings = Settings.from_env()

    assert settings.model == "claude-sonnet-5"
