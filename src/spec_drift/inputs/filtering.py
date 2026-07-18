"""Exclude changed paths that must never reach analysis.

Four kinds of path are dropped before a model is ever invoked, in priority
order so the reported reason is the most security-relevant one:

1. ``.env`` files — may hold secrets; excluded by name regardless of ignore
   rules, so a mistakenly tracked ``.env`` is still kept out.
2. Paths outside the repository root — a defensive guard against traversal.
3. Ignored files — anything matching a ``.gitignore`` pattern.
4. Binary files — no reviewable text.

The check order matters: an ignored ``.env`` is reported as an env file, not
merely ignored, because that is the reason that matters most.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path, PurePosixPath

from spec_drift.inputs import git
from spec_drift.inputs.model import ChangedFile, ExcludedFile, ExclusionReason


def _is_env_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name == ".env" or name.startswith(".env.")


def _is_outside_root(path: str) -> bool:
    pure = PurePosixPath(path)
    return pure.is_absolute() or ".." in pure.parts


BinaryCheck = Callable[[Path, ChangedFile], bool]
IgnoreCheck = Callable[[Path, str], bool]


def classify_exclusion(
    root: Path,
    change: ChangedFile,
    *,
    is_binary: BinaryCheck = git.is_binary,
    is_ignored: IgnoreCheck = git.is_ignored,
) -> ExclusionReason | None:
    """Return the reason ``change`` should be excluded, or ``None`` to keep it.

    ``is_binary`` and ``is_ignored`` are injectable so filtering can be tested
    without a real repository.
    """
    if _is_env_file(change.path):
        return ExclusionReason.ENV_FILE
    if _is_outside_root(change.path):
        return ExclusionReason.OUTSIDE_ROOT
    if is_ignored(root, change.path):
        return ExclusionReason.IGNORED
    if is_binary(root, change):
        return ExclusionReason.BINARY
    return None


def partition(
    root: Path,
    changes: list[ChangedFile],
    *,
    is_binary: BinaryCheck = git.is_binary,
    is_ignored: IgnoreCheck = git.is_ignored,
) -> tuple[list[ChangedFile], list[ExcludedFile]]:
    """Split ``changes`` into the paths to keep and the paths excluded."""
    kept: list[ChangedFile] = []
    excluded: list[ExcludedFile] = []
    for change in changes:
        reason = classify_exclusion(root, change, is_binary=is_binary, is_ignored=is_ignored)
        if reason is None:
            kept.append(change)
        else:
            excluded.append(ExcludedFile(path=change.path, reason=reason))
    return kept, excluded
