import sys
import types

import pytest

from spec_drift.core.messages import Message
from spec_drift.core.models import CompletionRequest
from spec_drift.providers.anthropic import AnthropicLanguageModel


class _FakeContentBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeMessage:
    def __init__(self, text: str, model: str) -> None:
        self.content = [_FakeContentBlock(text)]
        self.usage = _FakeUsage(input_tokens=10, output_tokens=5)
        self.model = model


class _FakeMessages:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> _FakeMessage:
        self.calls.append(kwargs)
        return _FakeMessage(text="hello from claude", model=str(kwargs["model"]))


class _FakeClient:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


def _install_fake_anthropic(monkeypatch: pytest.MonkeyPatch) -> _FakeClient:
    client = _FakeClient()
    fake_module = types.SimpleNamespace(Anthropic=lambda: client)
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    return client


def test_complete_splits_system_prompt_from_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_anthropic(monkeypatch)
    model = AnthropicLanguageModel()
    request = CompletionRequest(
        messages=(
            Message(role="system", content="You are terse."),
            Message(role="user", content="hello"),
        )
    )

    response = model.complete(request)

    call = client.messages.calls[0]
    assert call["system"] == "You are terse."
    assert call["messages"] == [{"role": "user", "content": "hello"}]
    assert response.text == "hello from claude"
    assert response.usage == {"input_tokens": 10, "output_tokens": 5}


def test_complete_omits_system_kwarg_when_no_system_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _install_fake_anthropic(monkeypatch)
    model = AnthropicLanguageModel()
    request = CompletionRequest(messages=(Message(role="user", content="hello"),))

    model.complete(request)

    assert "system" not in client.messages.calls[0]
