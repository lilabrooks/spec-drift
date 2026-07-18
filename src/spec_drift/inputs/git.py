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
# How many leading bytes to scan when deciding whether a blob is binary. Git's
# own heuristic checks for a NUL byte in a comparable window.
_BINARY_SCAN_BYTES = 8000


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


def is_binary(root: Path, change: ChangedFile) -> bool:
    """Whether the blob for ``change`` looks binary (contains a NUL byte).

    The blob at HEAD is inspected. A deleted file has no HEAD blob, so it is
    treated as non-binary — its content never reaches analysis anyway. A
    missing blob is likewise treated as non-binary.
    """
    if change.status is ChangeStatus.DELETED:
        return False
    result = _run(root, "show", f"HEAD:{change.path}")
    if result.returncode != 0:
        return False
    return b"\x00" in result.stdout[:_BINARY_SCAN_BYTES]


def is_ignored(root: Path, path: str) -> bool:
    """Whether ``path`` matches a ``.gitignore`` pattern, tracked or not."""
    result = _run(root, "check-ignore", "--no-index", "-q", "--", path)
    return result.returncode == 0


def load_file_diff(root: Path, base: str, path: str) -> str:
    """Return the unified diff of ``path`` between ``base`` and ``HEAD``.

    Read-only. An empty string means git produced no diff for the path.
    """
    result = _run(root, "diff", base, "HEAD", "--", path)
    return result.stdout.decode("utf-8", "surrogateescape")
