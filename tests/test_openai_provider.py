import sys
import types

import pytest

from spec_drift.core.messages import Message
from spec_drift.core.models import CompletionRequest
from spec_drift.providers.openai import OpenAILanguageModel


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeCompletion:
    def __init__(self, text: str, model: str) -> None:
        self.choices = [_FakeChoice(text)]
        self.usage = _FakeUsage(prompt_tokens=8, completion_tokens=4)
        self.model = model


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> _FakeCompletion:
        self.calls.append(kwargs)
        return _FakeCompletion(text="hello from gpt", model=str(kwargs["model"]))


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeClient:
    def __init__(self) -> None:
        self.chat = _FakeChat()


def _install_fake_openai(monkeypatch: pytest.MonkeyPatch) -> _FakeClient:
    client = _FakeClient()
    fake_module = types.SimpleNamespace(OpenAI=lambda: client)
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    return client


def test_complete_sends_system_and_user_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_openai(monkeypatch)
    model = OpenAILanguageModel()
    request = CompletionRequest(
        messages=(
            Message(role="system", content="You are terse."),
            Message(role="user", content="hello"),
        )
    )

    response = model.complete(request)

    call = client.chat.completions.calls[0]
    assert call["messages"] == [
        {"role": "system", "content": "You are terse."},
        {"role": "user", "content": "hello"},
    ]
    assert response.text == "hello from gpt"
    assert response.usage == {"input_tokens": 8, "output_tokens": 4}
