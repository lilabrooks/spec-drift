"""Tests for the deterministic replay provider (ADR 0002)."""

import json
from pathlib import Path

import pytest

from spec_drift.core.messages import Message
from spec_drift.core.models import CompletionRequest
from spec_drift.providers.registry import available_providers, create_provider
from spec_drift.providers.replay import REPLAY_FILE_ENV, ReplayLanguageModel


def _request(path: str) -> CompletionRequest:
    return CompletionRequest(
        messages=(Message(role="user", content=f"Changed file: {path}\n\n=== diff ==="),)
    )


def _replay_file(tmp_path: Path, mapping: dict[str, str]) -> str:
    file = tmp_path / "replay.json"
    file.write_text(json.dumps(mapping), encoding="utf-8")
    return str(file)


def test_replays_reply_keyed_by_changed_file(tmp_path: Path) -> None:
    model = ReplayLanguageModel(
        _replay_file(tmp_path, {"src/a.py": "REPLY-A", "src/b.py": "REPLY-B"})
    )
    assert model.complete(_request("src/a.py")).text == "REPLY-A"
    assert model.complete(_request("src/b.py")).text == "REPLY-B"


def test_falls_back_to_default_entry(tmp_path: Path) -> None:
    model = ReplayLanguageModel(_replay_file(tmp_path, {"_default": "FALLBACK"}))
    assert model.complete(_request("src/unlisted.py")).text == "FALLBACK"


def test_unlisted_change_without_default_is_insufficient(tmp_path: Path) -> None:
    model = ReplayLanguageModel(_replay_file(tmp_path, {"src/a.py": "REPLY-A"}))
    text = model.complete(_request("src/other.py")).text
    assert json.loads(text)["classification"] == "insufficient-evidence"


def test_reads_path_from_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(REPLAY_FILE_ENV, _replay_file(tmp_path, {"src/a.py": "FROM-ENV"}))
    model = ReplayLanguageModel()
    assert model.complete(_request("src/a.py")).text == "FROM-ENV"


def test_missing_file_reference_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(REPLAY_FILE_ENV, raising=False)
    with pytest.raises(ValueError, match=REPLAY_FILE_ENV):
        ReplayLanguageModel()


def test_unreadable_or_malformed_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="could not read"):
        ReplayLanguageModel(str(tmp_path / "missing.json"))

    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="could not read"):
        ReplayLanguageModel(str(bad))


def test_non_object_file_is_an_error(tmp_path: Path) -> None:
    array = tmp_path / "array.json"
    array.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a JSON object"):
        ReplayLanguageModel(str(array))


def test_registry_exposes_replay(tmp_path: Path) -> None:
    assert "replay" in available_providers()
    model = create_provider("replay", model=_replay_file(tmp_path, {"src/a.py": "VIA-REGISTRY"}))
    assert model.complete(_request("src/a.py")).text == "VIA-REGISTRY"
