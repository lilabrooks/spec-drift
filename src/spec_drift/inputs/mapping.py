"""Resolve the specs and ADRs that govern a changed path.

The claude-okf-repo-kit convention records a source-to-knowledge map at
``docs/okf-map.yml``: a ``mappings:`` list where each entry pairs a
repository-relative source glob with the governing document paths. This module
reads that file with a small, purpose-built parser — the map is a fixed, simple
shape, so a dependency-free reader keeps the tool's zero-runtime-dependency
promise — and matches changed paths against the globs.

Only the ``mappings:`` block is interpreted here; the optional ``layout:``
block and comments are ignored. A change matching no glob is left unresolved so
the caller can report it as ``unmapped`` rather than invent a contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAP_PATH = Path("docs") / "okf-map.yml"


class MappingError(ValueError):
    """The map file exists but could not be parsed."""


@dataclass(frozen=True, slots=True)
class Mapping:
    source: str
    docs: tuple[str, ...]


def _strip_inline_comment(value: str) -> str:
    # Comments only outside quotes; the map keeps globs quoted for exactly this.
    if value.startswith(('"', "'")):
        quote = value[0]
        end = value.find(quote, 1)
        if end != -1:
            return value[: end + 1]
        return value
    hash_index = value.find("#")
    return value[:hash_index] if hash_index != -1 else value


def _unquote(value: str) -> str:
    value = _strip_inline_comment(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_mappings(text: str) -> list[Mapping]:
    """Parse the ``mappings:`` block of an okf-map document.

    A deliberately small YAML subset: a top-level ``mappings:`` key, list items
    introduced by ``- source:``, and a following ``docs:`` block list. Enough
    for the kit's map, and nothing more.
    """
    lines = text.splitlines()
    in_mappings = False
    mappings: list[Mapping] = []
    current_source: str | None = None
    current_docs: list[str] = []
    in_docs = False

    def flush() -> None:
        nonlocal current_source, current_docs, in_docs
        if current_source is not None:
            mappings.append(Mapping(source=current_source, docs=tuple(current_docs)))
        current_source = None
        current_docs = []
        in_docs = False

    for raw in lines:
        stripped = raw.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())

        if not in_mappings:
            if stripped.rstrip(":") == "mappings" and indent == 0:
                in_mappings = True
            continue

        if indent == 0:  # a new top-level key ends the mappings block
            break

        if stripped.startswith("- source:"):
            flush()
            current_source = _unquote(stripped[len("- source:") :])
            continue
        if current_source is None:
            continue
        if stripped.rstrip() == "docs:":
            in_docs = True
            continue
        if in_docs and stripped.startswith("- "):
            current_docs.append(_unquote(stripped[2:]))
            continue

    flush()
    return [m for m in mappings if m.source]


def load_mappings(root: Path, map_path: Path = DEFAULT_MAP_PATH) -> list[Mapping]:
    """Load mappings from ``root/map_path``; an absent file means no mappings."""
    full = root / map_path
    if not full.is_file():
        return []
    try:
        return parse_mappings(full.read_text(encoding="utf-8"))
    except OSError as error:  # pragma: no cover - unreadable file is rare
        msg = f"could not read map file {map_path}: {error}"
        raise MappingError(msg) from error


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    # ``**`` matches across directory separators; ``*`` and ``?`` stay within a
    # segment. Anything else is matched literally.
    out = ["(?s:"]
    i = 0
    while i < len(glob):
        char = glob[i]
        if char == "*":
            if glob[i : i + 2] == "**":
                out.append(".*")
                i += 2
                if glob[i : i + 1] == "/":  # ``**/`` also matches zero directories
                    i += 1
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        i += 1
    out.append(r")\Z")
    return re.compile("".join(out))


def resolve_governing_docs(path: str, mappings: list[Mapping]) -> tuple[str, ...]:
    """Return the governing documents for ``path``, deduplicated and ordered.

    A path may match several mappings; their documents are unioned while
    preserving first-seen order. An empty result means the path is unmapped.
    """
    seen: dict[str, None] = {}
    for mapping in mappings:
        if _glob_to_regex(mapping.source).match(path):
            for doc in mapping.docs:
                seen.setdefault(doc, None)
    return tuple(seen)
