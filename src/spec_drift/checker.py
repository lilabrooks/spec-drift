"""The ``spec-drift check`` command: collect changes, analyze, render, exit.

Kept separate from argument parsing so it can be driven directly in tests with
an injected model. It owns the exit-code contract: 0/1 from the analysis report,
2 for an input, repository, or configuration failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

from spec_drift.analysis import analyze
from spec_drift.core.ports import LanguageModel
from spec_drift.inputs import InvalidBaseError, RepositoryError, collect_changes
from spec_drift.report import ReportFormat, render

EXIT_INPUT_ERROR = 2


def run_check(
    start: Path,
    base: str,
    model: LanguageModel,
    report_format: ReportFormat,
    *,
    strict_coverage: bool = False,
) -> int:
    """Analyze ``base..HEAD`` under ``start`` and print a report.

    Returns the analysis exit code (0 or 1), or ``EXIT_INPUT_ERROR`` when the
    repository or base reference is invalid — with a message and no stack trace.
    """
    try:
        changeset = collect_changes(start, base)
    except (RepositoryError, InvalidBaseError) as error:
        sys.stderr.write(f"error: {error}\n")
        return EXIT_INPUT_ERROR

    report = analyze(changeset, model, strict_coverage=strict_coverage)
    sys.stdout.write(f"{render(report, report_format)}\n")
    return report.exit_code()
