"""Assemble the analysis input for one run.

``collect_changes`` is the input layer's single entry point: given a starting
directory and a base reference, it discovers the repository, loads the diff,
filters out paths that must not be analyzed, resolves the governing documents
for the rest, and returns an immutable :class:`ChangeSet`. It performs no model
calls and never writes to the repository.
"""

from __future__ import annotations

from pathlib import Path

from spec_drift.inputs import git
from spec_drift.inputs.filtering import partition
from spec_drift.inputs.mapping import load_mappings, resolve_governing_docs
from spec_drift.inputs.model import ChangeSet, ResolvedChange


def collect_changes(start: Path, base: str) -> ChangeSet:
    """Discover, diff, filter, and resolve the changes under ``start``.

    Raises ``git.RepositoryError`` when ``start`` is not in a repository and
    ``git.InvalidBaseError`` when ``base`` does not resolve — both mapped by the
    CLI to exit code 2.
    """
    root = git.find_repository_root(start)
    git.verify_base(root, base)

    changed = git.load_changed_files(root, base)
    kept, excluded = partition(root, changed)

    mappings = load_mappings(root)
    resolved = tuple(
        ResolvedChange(file=change, governing_docs=resolve_governing_docs(change.path, mappings))
        for change in kept
    )

    return ChangeSet(
        root=str(root),
        base=base,
        included=resolved,
        excluded=tuple(excluded),
    )
