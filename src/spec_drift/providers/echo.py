from spec_drift.core.models import CompletionRequest, CompletionResponse


class EchoLanguageModel:
    """Local provider used for development, demos, and tests."""

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        user_messages = [message.content for message in request.messages if message.role == "user"]
        text = user_messages[-1] if user_messages else ""
        return CompletionResponse(text=f"Echo provider received: {text}", model="echo")
