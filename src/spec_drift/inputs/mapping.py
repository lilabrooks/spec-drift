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
from dataclasses import dataclass, field
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


@dataclass
class _MapParser:
    """State machine for the ``mappings:`` subset, split out so the strict
    validation stays readable and within complexity limits."""

    in_mappings: bool = False
    saw_mappings_header: bool = False
    saw_top_level_key: bool = False
    has_content: bool = False
    mappings: list[Mapping] = field(default_factory=list)
    _source: str | None = None
    _docs: list[str] = field(default_factory=list)
    _in_docs: bool = False

    def _flush(self) -> None:
        if self._source is not None:
            if not self._docs:
                msg = f"mapping for source {self._source!r} lists no governing documents"
                raise MappingError(msg)
            self.mappings.append(Mapping(source=self._source, docs=tuple(self._docs)))
        self._source = None
        self._docs = []
        self._in_docs = False

    def _feed_top_level(self, stripped: str) -> None:
        self._flush()
        self.in_mappings = False
        if ":" in stripped:
            self.saw_top_level_key = True
        if stripped.split(":", 1)[0].strip() == "mappings":
            self.in_mappings = True
            self.saw_mappings_header = True

    def _feed_in_block(self, stripped: str) -> None:
        if stripped.startswith("- source:"):
            self._flush()
            self._source = _unquote(stripped[len("- source:") :])
            if not self._source:
                raise MappingError("a mapping entry has an empty source glob")
            return
        if self._source is None:
            raise MappingError(f"unexpected line before a mapping source: {stripped!r}")
        if stripped.rstrip() == "docs:":
            self._in_docs = True
            return
        if self._in_docs and stripped.startswith("- "):
            doc = _unquote(stripped[2:])
            if not doc:
                msg = f"mapping for source {self._source!r} has an empty document path"
                raise MappingError(msg)
            self._docs.append(doc)
            return
        raise MappingError(f"unexpected line in mappings block: {stripped!r}")

    def feed(self, raw: str) -> None:
        stripped = raw.strip()
        if stripped == "" or stripped.startswith("#"):
            return
        self.has_content = True
        if len(raw) - len(raw.lstrip()) == 0:  # top-level key ends any open block
            self._feed_top_level(stripped)
        elif not self.in_mappings:
            # Indented content under a block we don't interpret is fine, but a
            # loose mapping fragment outside a ``mappings:`` block is corruption.
            if stripped.startswith("- source:") or stripped.rstrip() == "docs:":
                msg = "found mapping entries outside a 'mappings:' block; the map is malformed"
                raise MappingError(msg)
        else:
            self._feed_in_block(stripped)

    def result(self) -> list[Mapping]:
        self._flush()
        if self.saw_mappings_header and not self.mappings:
            raise MappingError("the 'mappings:' block is empty or could not be parsed")
        if self.has_content and not self.saw_top_level_key and not self.mappings:
            raise MappingError("does not look like an okf-map document (no top-level keys)")
        return self.mappings


def parse_mappings(text: str) -> list[Mapping]:
    """Parse the ``mappings:`` block of an okf-map document.

    A deliberately small YAML subset: a top-level ``mappings:`` key, list items
    introduced by ``- source:``, and a following ``docs:`` block list. Enough
    for the kit's map, and nothing more.

    Validation is strict on purpose: a governance tool must fail loudly on a
    broken map rather than treat it as "no mappings" and silently greenlight
    every change. Structural corruption — an empty source, a mapping with no
    documents, a stray line inside the block, mapping fragments outside any
    ``mappings:`` block, or a ``mappings:`` header that yields nothing — raises
    :class:`MappingError`. An absent, empty, or comment-only file, or one whose
    only top-level keys are blocks this module does not interpret (``layout:``,
    ``mirrors:``), legitimately yields no mappings.
    """
    parser = _MapParser()
    for raw in text.splitlines():
        parser.feed(raw)
    return parser.result()


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
