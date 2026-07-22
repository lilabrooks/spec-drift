"""The ``spec-drift check`` command: collect changes, analyze, render, exit.

Kept separate from argument parsing so it can be driven directly in tests with
an injected model. It owns the exit-code contract: 0/1 from the analysis report,
2 for an input, repository, or configuration failure.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from spec_drift.analysis import DEFAULT_MAX_CONTEXT_CHARS, analyze
from spec_drift.core.fileset import GeneratedFile, resolve_target_path, write_generated_files
from spec_drift.core.ports import LanguageModel, ProviderError
from spec_drift.inputs import (
    InvalidBaseError,
    MappingError,
    RepositoryError,
    collect_changes,
)
from spec_drift.report import ReportFormat, render

EXIT_INPUT_ERROR = 2


@dataclass(frozen=True, slots=True)
class CheckOptions:
    """How ``spec-drift check`` should render and where it should write."""

    report_format: ReportFormat = ReportFormat.TERMINAL
    strict_coverage: bool = False
    output: str | None = None
    force: bool = False
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS


def _write_report(destination: Path, output: str, rendered: str, *, force: bool) -> str | None:
    """Safely write ``rendered`` to ``output`` under ``destination``.

    Reuses the safe-write layer: reject paths that escape ``destination``, and
    refuse to overwrite an existing file without ``force``. Returns an error
    message on failure, or ``None`` on success.
    """
    generated = GeneratedFile(path=output, content=rendered)
    try:
        target = resolve_target_path(destination, generated)
    except ValueError:
        return f"refusing to write outside the working directory: {output}"
    try:
        write_generated_files([generated], [target], force=force)
    except FileExistsError:
        return f"{output} already exists; pass --force to overwrite"
    return None


def run_check(start: Path, base: str, model: LanguageModel, options: CheckOptions) -> int:
    """Analyze ``base..HEAD`` under ``start`` and report the result.

    Prints to stdout, or writes to ``options.output`` (relative to ``start``)
    when given. Returns the analysis exit code (0 or 1), or ``EXIT_INPUT_ERROR``
    for an invalid repository, base reference, or output path — with a message
    and no stack trace.
    """
    try:
        changeset = collect_changes(start, base)
    except (RepositoryError, InvalidBaseError, MappingError) as error:
        sys.stderr.write(f"error: {error}\n")
        return EXIT_INPUT_ERROR

    try:
        report = analyze(
            changeset,
            model,
            strict_coverage=options.strict_coverage,
            max_context_chars=options.max_context_chars,
        )
    except ProviderError as error:
        sys.stderr.write(f"error: {error}\n")
        return EXIT_INPUT_ERROR
    rendered = render(report, options.report_format)

    if options.output is None:
        sys.stdout.write(f"{rendered}\n")
        return report.exit_code()

    error_message = _write_report(start, options.output, rendered, force=options.force)
    if error_message is not None:
        sys.stderr.write(f"error: {error_message}\n")
        return EXIT_INPUT_ERROR
    sys.stderr.write(f"wrote {options.output}\n")
    return report.exit_code()
