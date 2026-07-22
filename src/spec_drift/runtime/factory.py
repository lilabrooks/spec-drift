from spec_drift.config.settings import Settings
from spec_drift.core.ports import LanguageModel
from spec_drift.providers.registry import create_provider


def build_model(settings: Settings) -> LanguageModel:
    return create_provider(settings.provider, model=settings.model)
