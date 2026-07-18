#!/usr/bin/env python3
"""Validate OKF-style documentation metadata and local Markdown links."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_ROOT_NAMES = {"docs", "specs", "skills"}
REQUIRED_DOC_FILES = (
    Path("docs/index.md"),
    Path("docs/log.md"),
    Path("docs/specs/index.md"),
    Path("docs/adr/index.md"),
)
FENCE_RE = re.compile(r"^```")
LINK_RE = re.compile(r"!?\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INLINE_LIST_RE = re.compile(r"^\[(.*)\]$")


class FrontmatterError(ValueError):
    """Raised when a frontmatter block falls outside the supported YAML subset."""


def tracked_markdown_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "*.md"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return sorted(
            path.relative_to(REPO_ROOT)
            for root_name in DOC_ROOT_NAMES
            for path in (REPO_ROOT / root_name).rglob("*.md")
        )

    return [Path(line) for line in result.stdout.splitlines() if line]


def markdown_files_to_check() -> list[Path]:
    return [
        path for path in tracked_markdown_files() if path.parts and path.parts[0] in DOC_ROOT_NAMES
    ]


def frontmatter_lines(path: Path) -> list[str] | None:
    lines = (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            return lines[1:index]
    raise FrontmatterError(f"{path}: frontmatter block is not closed")


def parse_scalar(raw: str) -> object:
    value = raw.strip()
    if value == "":
        return None
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    inline_list = INLINE_LIST_RE.match(value)
    if inline_list:
        inner = inline_list.group(1).strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",")]
    return value


def parse_frontmatter(path: Path, lines: list[str]) -> dict[str, object]:
    data: dict[str, object] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line.startswith((" ", "-")):
            raise FrontmatterError(f"{path}: unexpected frontmatter line: {line}")
        if ":" not in line:
            raise FrontmatterError(f"{path}: frontmatter line must use key: value: {line}")

        key, raw_value = line.split(":", maxsplit=1)
        key = key.strip()
        if not key:
            raise FrontmatterError(f"{path}: frontmatter key is blank")
        value = parse_scalar(raw_value)

        items: list[str] = []
        next_index = index + 1
        while next_index < len(lines) and lines[next_index].startswith("  - "):
            items.append(lines[next_index][4:].strip().strip('"').strip("'"))
            next_index += 1
        if items:
            if value is not None:
                raise FrontmatterError(
                    f"{path}: key {key!r} cannot have both a scalar and block list"
                )
            value = items
            index = next_index
        else:
            index += 1

        data[key] = value

    return data


def is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(is_nonempty_string(item) for item in value)


def validate_frontmatter(errors: list[str]) -> None:
    for required in REQUIRED_DOC_FILES:
        if not (REPO_ROOT / required).is_file():
            errors.append(f"{required}: required OKF file is missing")

    for path in markdown_files_to_check():
        try:
            lines = frontmatter_lines(path)
            if lines is None:
                continue
            data = parse_frontmatter(path, lines)
        except FrontmatterError as error:
            errors.append(str(error))
            continue

        owner = data.get("owner")
        if not is_nonempty_string(owner):
            errors.append(f"{path}: frontmatter owner must be a non-empty string")

        deciders = data.get("deciders")
        if not is_string_list(deciders):
            errors.append(f"{path}: frontmatter deciders must be a non-empty string list")

        if path.parts[0] == "docs" and not is_nonempty_string(data.get("type")):
            errors.append(f"{path}: OKF docs frontmatter must include non-empty type")

        if path == Path("docs/index.md") and not is_nonempty_string(data.get("okf_version")):
            errors.append("docs/index.md: okf_version is required")


def strip_fenced_blocks(text: str) -> str:
    kept: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    return "\n".join(kept)


def is_external_link(target: str) -> bool:
    split = urlsplit(target)
    return bool(split.scheme) or target.startswith(("#", "mailto:"))


def validate_links(errors: list[str]) -> None:
    for path in markdown_files_to_check():
        text = strip_fenced_blocks((REPO_ROOT / path).read_text(encoding="utf-8"))
        for raw_target in LINK_RE.findall(text):
            target = unquote(raw_target.split("#", maxsplit=1)[0])
            if not target or is_external_link(raw_target):
                continue
            candidate = (REPO_ROOT / path.parent / target).resolve()
            try:
                candidate.relative_to(REPO_ROOT)
            except ValueError:
                errors.append(f"{path}: local link escapes repo: {raw_target}")
                continue
            if not candidate.exists():
                errors.append(f"{path}: local link target is missing: {raw_target}")


def main() -> int:
    errors: list[str] = []
    validate_frontmatter(errors)
    validate_links(errors)

    if errors:
        sys.stderr.write("OKF docs check failed:\n")
        for error in errors:
            sys.stderr.write(f"- {error}\n")
        return 1

    sys.stdout.write("okf docs ok\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
