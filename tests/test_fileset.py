from pathlib import Path

import pytest

from spec_drift.core.fileset import (
    GeneratedFile,
    parse_generated_files,
    resolve_target_path,
    write_generated_files,
)


def test_parse_generated_files_extracts_single_file() -> None:
    text = "\n".join(
        [
            "Here is the file:",
            "FILE: src/hello.py",
            "```python",
            'print("hi")',
            "```",
            "Done.",
        ]
    )

    files = parse_generated_files(text)

    assert files == [GeneratedFile(path="src/hello.py", content='print("hi")')]


def test_parse_generated_files_extracts_multiple_files() -> None:
    text = "\n".join(
        [
            "FILE: a.txt",
            "```",
            "aaa",
            "```",
            "FILE: b.txt",
            "```",
            "bbb",
            "ccc",
            "```",
        ]
    )

    files = parse_generated_files(text)

    assert files == [
        GeneratedFile(path="a.txt", content="aaa"),
        GeneratedFile(path="b.txt", content="bbb\nccc"),
    ]


def test_parse_generated_files_returns_empty_list_without_markers() -> None:
    assert parse_generated_files("Just a plain text answer, no files here.") == []


def test_parse_generated_files_skips_marker_without_following_fence() -> None:
    text = "\n".join(
        [
            "FILE: orphan.txt",
            "(no fenced block follows, so this marker is prose)",
        ]
    )

    assert parse_generated_files(text) == []


def test_parse_generated_files_skips_unclosed_fence() -> None:
    text = "\n".join(
        [
            "FILE: partial.txt",
            "```",
            "incomplete content",
        ]
    )

    assert parse_generated_files(text) == []


def test_resolve_target_path_rejects_absolute_path(tmp_path: Path) -> None:
    generated = GeneratedFile(path="/etc/passwd", content="x")

    with pytest.raises(ValueError, match="Unsafe or invalid file path"):
        resolve_target_path(tmp_path, generated)


def test_resolve_target_path_rejects_parent_traversal(tmp_path: Path) -> None:
    generated = GeneratedFile(path="../outside.txt", content="x")

    with pytest.raises(ValueError, match="Unsafe or invalid file path"):
        resolve_target_path(tmp_path, generated)


def test_resolve_target_path_joins_relative_path_under_out_dir(tmp_path: Path) -> None:
    generated = GeneratedFile(path="src/hello.py", content="x")

    target = resolve_target_path(tmp_path, generated)

    assert target == tmp_path / "src" / "hello.py"


def test_resolve_target_path_rejects_symlink_escape(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    outside = tmp_path / "outside"
    out_dir.mkdir()
    outside.mkdir()
    link = out_dir / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks unavailable: {error}")

    generated = GeneratedFile(path="linked/escape.txt", content="x")

    with pytest.raises(ValueError, match="Unsafe or invalid file path"):
        resolve_target_path(out_dir, generated)


def test_write_generated_files_creates_parent_directories(tmp_path: Path) -> None:
    files = [GeneratedFile(path="pkg/mod.py", content="x = 1")]
    targets = [resolve_target_path(tmp_path, generated) for generated in files]

    write_generated_files(files, targets, force=False)

    assert (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8") == "x = 1\n"


def test_write_generated_files_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    existing = tmp_path / "already-there.txt"
    existing.write_text("original", encoding="utf-8")
    files = [GeneratedFile(path="already-there.txt", content="new content")]
    targets = [resolve_target_path(tmp_path, generated) for generated in files]

    with pytest.raises(FileExistsError, match=r"already-there\.txt"):
        write_generated_files(files, targets, force=False)

    assert existing.read_text(encoding="utf-8") == "original"


def test_write_generated_files_overwrites_with_force(tmp_path: Path) -> None:
    existing = tmp_path / "already-there.txt"
    existing.write_text("original", encoding="utf-8")
    files = [GeneratedFile(path="already-there.txt", content="new content")]
    targets = [resolve_target_path(tmp_path, generated) for generated in files]

    write_generated_files(files, targets, force=True)

    assert existing.read_text(encoding="utf-8") == "new content\n"


def test_write_generated_files_rejects_mismatched_lists_before_writing(tmp_path: Path) -> None:
    files = [GeneratedFile(path="first.txt", content="first")]
    targets = [tmp_path / "first.txt", tmp_path / "extra.txt"]

    with pytest.raises(ValueError, match="same length"):
        write_generated_files(files, targets)

    assert not (tmp_path / "first.txt").exists()


def test_write_generated_files_rejects_duplicate_targets_before_writing(tmp_path: Path) -> None:
    files = [
        GeneratedFile(path="first.txt", content="first"),
        GeneratedFile(path="second.txt", content="second"),
    ]
    duplicate = tmp_path / "same.txt"

    with pytest.raises(ValueError, match="duplicate target paths"):
        write_generated_files(files, [duplicate, duplicate])

    assert not duplicate.exists()
