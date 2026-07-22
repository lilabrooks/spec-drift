"""A deterministic, offline provider that replays canned model replies.

Given a JSON file mapping a changed-file path to the reply the model should
give for it, ``ReplayLanguageModel`` returns those replies without any network
call. It exists so the real ``check`` command can be exercised reproducibly —
in ``make ci-fixture``, in an example workflow, or by a user testing their CI
wiring — without a vendor key (ADR 0002). It speaks the same JSON contract as a
real provider (ADR 0001); the engine validates its output like any other.

The replay file is ``{"<repo-relative path>": "<reply text>", ...}`` with an
optional ``"_default"`` entry for changes not listed. Its path comes from the
provider ``model`` argument or the ``SPEC_DRIFT_REPLAY_FILE`` environment
variable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from spec_drift.core.models import CompletionRequest, CompletionResponse

REPLAY_FILE_ENV = "SPEC_DRIFT_REPLAY_FILE"
_DEFAULT_KEY = "_default"
_NO_ENTRY = (
    '{"classification": "insufficient-evidence", "summary": "no replay entry for this change"}'
)


class ReplayLanguageModel:
    """Replay canned JSON replies keyed by the changed file in the request."""

    def __init__(self, replay_file: str | None = None) -> None:
        path = replay_file or os.environ.get(REPLAY_FILE_ENV)
        if not path:
            msg = f"replay provider needs a file via --model or {REPLAY_FILE_ENV}"
            raise ValueError(msg)
        try:
            loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            msg = f"could not read replay file {path!r}: {error}"
            raise ValueError(msg) from error
        if not isinstance(loaded, dict):
            msg = f"replay file {path!r} must be a JSON object of path -> reply"
            raise ValueError(msg)
        self._replies: dict[str, str] = {str(key): str(value) for key, value in loaded.items()}

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        user = next((message.content for message in request.messages if message.role == "user"), "")
        for key, reply in self._replies.items():
            # Anchor on the trailing newline so key ``src/a.py`` cannot match a
            # changed file ``src/a.py.bak`` by unanchored substring.
            if key != _DEFAULT_KEY and f"Changed file: {key}\n" in user:
                return CompletionResponse(text=reply, model="replay")
        return CompletionResponse(text=self._replies.get(_DEFAULT_KEY, _NO_ENTRY), model="replay")
