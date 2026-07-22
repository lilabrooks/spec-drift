"""Read-only Git access via the ``git`` command line.

Git is the source of changed-file and diff information (a project constraint),
and the CLI must never modify the working tree, so every call here is a
read-only plumbing command run through ``git`` in a subprocess. Using the
command line rather than a library keeps the runtime dependency-free.

Errors are surfaced as typed exceptions the CLI maps to exit code 2: a
directory that is not a Git repository, or a base reference Git cannot resolve.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from spec_drift.inputs.model import ChangedFile, ChangeStatus

# git reports rename/copy status as the letter plus a similarity score (R100).
_RENAME_PREFIX = "R"
_COPY_PREFIX = "C"
_STATUS_LETTERS = {
    "A": ChangeStatus.ADDED,
    "M": ChangeStatus.MODIFIED,
    "D": ChangeStatus.DELETED,
    "T": ChangeStatus.MODIFIED,  # type change (e.g. file <-> symlink): treat as modified
}


class RepositoryError(ValueError):
    """The target path is not inside a Git repository."""


class InvalidBaseError(ValueError):
    """The base reference could not be resolved to a commit."""


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
    )


def find_repository_root(start: Path) -> Path:
    """Return the top level of the Git repository containing ``start``.

    Raises ``RepositoryError`` when ``start`` is not inside a repository.
    """
    result = _run(start, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        msg = f"not a Git repository: {start}"
        raise RepositoryError(msg)
    return Path(result.stdout.decode("utf-8", "surrogateescape").strip())


def verify_base(root: Path, base: str) -> None:
    """Ensure ``base`` resolves to a commit, raising ``InvalidBaseError`` if not."""
    result = _run(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if result.returncode != 0:
        msg = f"invalid base reference: {base!r}"
        raise InvalidBaseError(msg)


def load_changed_files(root: Path, base: str) -> list[ChangedFile]:
    """Return the files that changed between ``base`` and ``HEAD``.

    Renames are detected and reported with both paths. Paths are
    repository-relative. NUL-delimited output keeps unusual file names intact.
    """
    result = _run(root, "diff", "--name-status", "--find-renames", "-z", base, "HEAD")
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "surrogateescape").strip()
        msg = f"git diff failed for base {base!r}: {detail}"
        raise InvalidBaseError(msg)
    return _parse_name_status(result.stdout.decode("utf-8", "surrogateescape"))


def _parse_name_status(payload: str) -> list[ChangedFile]:
    tokens = [token for token in payload.split("\0") if token != ""]
    changes: list[ChangedFile] = []
    index = 0
    while index < len(tokens):
        code = tokens[index]
        index += 1
        if code[:1] in (_RENAME_PREFIX, _COPY_PREFIX):
            old_path, new_path = tokens[index], tokens[index + 1]
            index += 2
            changes.append(
                ChangedFile(path=new_path, status=ChangeStatus.RENAMED, old_path=old_path)
            )
            continue
        status = _STATUS_LETTERS.get(code[:1])
        path = tokens[index]
        index += 1
        if status is not None:
            changes.append(ChangedFile(path=path, status=status))
    return changes


def ignored_paths(root: Path, paths: list[str]) -> set[str]:
    """The subset of ``paths`` matching a ``.gitignore`` pattern, tracked or not.

    Batched into a single ``check-ignore --stdin`` call instead of one process
    per path. ``--no-index`` reports a path as ignored even when it is tracked,
    so a force-added ignored file is still excluded.
    """
    if not paths:
        return set()
    stdin = "\0".join(paths).encode("utf-8", "surrogateescape")
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--no-index", "--stdin", "-z"],
        input=stdin,
        capture_output=True,
        check=False,
    )
    out = result.stdout.decode("utf-8", "surrogateescape")
    return {token for token in out.split("\0") if token}


def binary_paths(root: Path, base: str) -> set[str]:
    """Paths git reports as binary between ``base`` and ``HEAD``.

    One ``git diff --numstat`` pass classifies the whole change set — git marks
    a binary file with ``-`` added/deleted counts — instead of reading each
    blob. Rename records carry the new path after the counts.
    """
    result = _run(root, "diff", "--numstat", "-z", "--find-renames", base, "HEAD")
    if result.returncode != 0:
        return set()
    return _parse_numstat_binaries(result.stdout.decode("utf-8", "surrogateescape"))


def _parse_numstat_binaries(payload: str) -> set[str]:
    tokens = payload.split("\0")
    binaries: set[str] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "":
            index += 1
            continue
        parts = token.split("\t")
        if len(parts) < 3:  # not a numstat record
            index += 1
            continue
        added, deleted, path = parts[0], parts[1], parts[2]
        is_binary = added == "-" and deleted == "-"
        if path == "":  # rename/copy: old path, then new path, follow as tokens
            new_path = tokens[index + 2] if index + 2 < len(tokens) else ""
            if is_binary:
                binaries.add(new_path)
            index += 3
        else:
            if is_binary:
                binaries.add(path)
            index += 1
    return binaries


def load_file_diff(root: Path, base: str, path: str, old_path: str | None = None) -> str:
    """Return the unified diff of ``path`` between ``base`` and ``HEAD``.

    For a rename, pass ``old_path`` so both names enter the pathspec and git
    reports the rename delta rather than a wholesale add of the new path.
    Read-only. A nonzero git exit yields ``""`` — the caller treats an empty
    diff as insufficient evidence rather than judging a change it cannot see.
    """
    pathspec = [path] if old_path is None else [old_path, path]
    result = _run(root, "diff", "--find-renames", base, "HEAD", "--", *pathspec)
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", "surrogateescape")
