"""Data model for the analysis inputs.

These types describe *what changed* and *what governs it*, resolved from a Git
diff before any model is invoked. They are deliberately plain and immutable:
downstream milestones (drift analysis, reporting) consume them, and keeping
them free of behavior makes the input layer easy to reason about and test.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ChangeStatus(Enum):
    """How a governed path changed between the base ref and HEAD."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ExclusionReason(Enum):
    """Why a changed path was kept out of analysis input."""

    IGNORED = "ignored"
    ENV_FILE = "env-file"
    BINARY = "binary"
    OUTSIDE_ROOT = "outside-root"


@dataclass(frozen=True, slots=True)
class ChangedFile:
    """A single path that changed, with repository-relative paths only."""

    path: str
    status: ChangeStatus
    old_path: str | None = None  # set only for RENAMED changes


@dataclass(frozen=True, slots=True)
class ExcludedFile:
    """A changed path removed from analysis input, with the reason."""

    path: str
    reason: ExclusionReason


@dataclass(frozen=True, slots=True)
class ResolvedChange:
    """A retained change and the governing documents resolved for it.

    ``governing_docs`` is empty when no mapping or convention governs the
    change; such a change is reported as ``unmapped`` rather than judged.
    """

    file: ChangedFile
    governing_docs: tuple[str, ...] = ()

    @property
    def is_unmapped(self) -> bool:
        return not self.governing_docs


@dataclass(frozen=True, slots=True)
class ChangeSet:
    """The complete, filtered, resolved input for one analysis run."""

    root: str
    base: str
    included: tuple[ResolvedChange, ...] = ()
    excluded: tuple[ExcludedFile, ...] = ()

    @property
    def governed(self) -> tuple[ResolvedChange, ...]:
        """Retained changes that have at least one governing document."""
        return tuple(change for change in self.included if not change.is_unmapped)

    @property
    def unmapped(self) -> tuple[ResolvedChange, ...]:
        """Retained changes with no governing document."""
        return tuple(change for change in self.included if change.is_unmapped)
