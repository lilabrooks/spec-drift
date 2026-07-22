"""Safe file writing for the report-output path.

A :class:`GeneratedFile` pairs a repository-relative path with content; the two
helpers resolve that path under a chosen destination and write it, safe by
default: no overwrite without force, no path escape outside the destination.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    path: str
    content: str


def resolve_target_path(out_dir: Path, generated: GeneratedFile) -> Path:
    relative = Path(generated.path)
    if (
        not generated.path.strip()
        or not relative.parts
        or relative.is_absolute()
        or ".." in relative.parts
    ):
        msg = f"Unsafe or invalid file path in agent output: {generated.path!r}"
        raise ValueError(msg)

    root = out_dir.resolve(strict=False)
    target = out_dir / relative
    if not target.resolve(strict=False).is_relative_to(root):
        msg = f"Unsafe or invalid file path in agent output: {generated.path!r}"
        raise ValueError(msg)
    return target


def write_generated_files(
    files: list[GeneratedFile],
    targets: list[Path],
    *,
    force: bool = False,
) -> None:
    if len(files) != len(targets):
        msg = "Generated files and target paths must have the same length"
        raise ValueError(msg)

    normalized_targets = [target.resolve(strict=False) for target in targets]
    if len(set(normalized_targets)) != len(normalized_targets):
        msg = "Generated files contain duplicate target paths"
        raise ValueError(msg)

    if not force:
        existing = [target for target in targets if target.exists()]
        if existing:
            joined = ", ".join(str(path) for path in existing)
            msg = f"Refusing to overwrite existing file(s) without --force: {joined}"
            raise FileExistsError(msg)

    for generated, target in zip(files, targets, strict=True):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{generated.content}\n", encoding="utf-8")
