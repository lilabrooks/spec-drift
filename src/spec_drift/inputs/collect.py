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
from spec_drift.inputs.mapping import Mapping, load_mappings, resolve_governing_docs
from spec_drift.inputs.model import ChangedFile, ChangeSet, ResolvedChange


def _governing_docs(change: ChangedFile, mappings: list[Mapping]) -> tuple[str, ...]:
    """Governing documents for ``change``, unioning both ends of a rename.

    A rename carries its ``old_path``; resolving only the new path would leave a
    file renamed *out* of a governed area silently unmapped. The new-path
    documents come first, then any that only the old path mapped to.
    """
    docs: dict[str, None] = dict.fromkeys(resolve_governing_docs(change.path, mappings))
    if change.old_path is not None:
        for doc in resolve_governing_docs(change.old_path, mappings):
            docs.setdefault(doc, None)
    return tuple(docs)


def collect_changes(start: Path, base: str) -> ChangeSet:
    """Discover, diff, filter, and resolve the changes under ``start``.

    Raises ``git.RepositoryError`` when ``start`` is not in a repository,
    ``git.InvalidBaseError`` when ``base`` does not resolve, and
    ``mapping.MappingError`` when ``docs/okf-map.yml`` is malformed — all mapped
    by the CLI to exit code 2.
    """
    root = git.find_repository_root(start)
    git.verify_base(root, base)

    changed = git.load_changed_files(root, base)
    ignored = git.ignored_paths(root, [change.path for change in changed])
    binary = git.binary_paths(root, base)
    kept, excluded = partition(changed, ignored=ignored, binary=binary)

    mappings = load_mappings(root)
    resolved = tuple(
        ResolvedChange(file=change, governing_docs=_governing_docs(change, mappings))
        for change in kept
    )

    return ChangeSet(
        root=str(root),
        base=base,
        included=resolved,
        excluded=tuple(excluded),
    )
