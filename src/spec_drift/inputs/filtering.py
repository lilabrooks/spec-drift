"""Exclude changed paths that must never reach analysis.

Five kinds of path are dropped before a model is ever invoked, in priority
order so the reported reason is the most security-relevant one:

1. ``.env`` files — may hold secrets; excluded by name regardless of ignore
   rules, so a mistakenly tracked ``.env`` is still kept out.
2. Credential files — private keys, keystores, ``.netrc`` and the like, by
   name, so a committed secret never enters model context or report output.
3. Paths outside the repository root — a defensive guard against traversal.
4. Ignored files — anything matching a ``.gitignore`` pattern.
5. Binary files — no reviewable text.

The check order matters: an ignored ``.env`` is reported as an env file, not
merely ignored, because that is the reason that matters most.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from spec_drift.inputs.model import ChangedFile, ExcludedFile, ExclusionReason

# Well-known secret-bearing files, matched by name so a mistakenly committed
# credential is excluded regardless of ignore rules. Public certificates
# (``.crt``/``.cert``) are intentionally absent — they carry no secret.
_CREDENTIAL_NAMES = frozenset(
    {".netrc", ".pgpass", ".htpasswd", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
)
_CREDENTIAL_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore", ".jks", ".ppk")


def _is_env_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name == ".env" or name.startswith(".env.")


def _is_credential(path: str) -> bool:
    name = PurePosixPath(path).name
    return name in _CREDENTIAL_NAMES or name.endswith(_CREDENTIAL_SUFFIXES)


def _is_outside_root(path: str) -> bool:
    pure = PurePosixPath(path)
    return pure.is_absolute() or ".." in pure.parts


def classify_exclusion(
    change: ChangedFile,
    *,
    ignored: frozenset[str] | set[str] = frozenset(),
    binary: frozenset[str] | set[str] = frozenset(),
) -> ExclusionReason | None:
    """Return the reason ``change`` should be excluded, or ``None`` to keep it.

    ``ignored`` and ``binary`` are the precomputed path sets from one batched
    git call each, so classification touches no subprocess.
    """
    if _is_env_file(change.path):
        return ExclusionReason.ENV_FILE
    if _is_credential(change.path):
        return ExclusionReason.CREDENTIAL
    if _is_outside_root(change.path):
        return ExclusionReason.OUTSIDE_ROOT
    if change.path in ignored:
        return ExclusionReason.IGNORED
    if change.path in binary:
        return ExclusionReason.BINARY
    return None


def partition(
    changes: list[ChangedFile],
    *,
    ignored: frozenset[str] | set[str] = frozenset(),
    binary: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[ChangedFile], list[ExcludedFile]]:
    """Split ``changes`` into the paths to keep and the paths excluded."""
    kept: list[ChangedFile] = []
    excluded: list[ExcludedFile] = []
    for change in changes:
        reason = classify_exclusion(change, ignored=ignored, binary=binary)
        if reason is None:
            kept.append(change)
        else:
            excluded.append(ExcludedFile(path=change.path, reason=reason))
    return kept, excluded
