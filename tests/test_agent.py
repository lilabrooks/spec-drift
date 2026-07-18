from spec_drift.agents.base import Agent
from spec_drift.providers.echo import EchoLanguageModel


def test_agent_runs_prompt_through_model() -> None:
    agent = Agent(
        name="test-agent",
        system_prompt="You are terse.",
        model=EchoLanguageModel(),
    )

    result = agent.run("hello")

    assert result.agent_name == "test-agent"
    assert result.text == "Echo provider received: hello"


def test_echo_provider_ignores_system_prompt() -> None:
    # Pins current behavior: the echo stub replies from the last user message
    # only. A real provider adapter is expected to use the system prompt.
    agent = Agent(
        name="test-agent",
        system_prompt="SENTINEL-SYSTEM-PROMPT",
        model=EchoLanguageModel(),
    )

    result = agent.run("hello")

    assert "SENTINEL-SYSTEM-PROMPT" not in result.text
    assert result.text == "Echo provider received: hello"
