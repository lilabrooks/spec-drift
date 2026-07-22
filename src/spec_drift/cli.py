"""Command-line entry point for spec-drift.

`check` is the tool's real surface: it reports whether the current branch has
drifted from its governing specs and ADRs. `providers` lists the available
model-provider adapters.
"""

import argparse
import sys
from pathlib import Path

from spec_drift import __version__
from spec_drift.checker import CheckOptions, run_check
from spec_drift.config.settings import Settings
from spec_drift.providers.registry import available_providers
from spec_drift.report import ReportFormat
from spec_drift.runtime.factory import build_model

_ECHO_WARNING = (
    "warning: the 'echo' provider cannot analyze drift; every governed change "
    "will be reported as 'insufficient-evidence'. Configure a real provider "
    "with --provider anthropic|openai or SPEC_DRIFT_PROVIDER.\n"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spec-drift",
        description="Detect when code changes drift from governing specs and ADRs.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("providers", help="List available provider adapters.")

    check = subparsers.add_parser(
        "check", help="Report whether changes drifted from governing specs and ADRs."
    )
    check.add_argument(
        "--base", required=True, help="Git ref to compare against (e.g. origin/main)."
    )
    check.add_argument(
        "--format",
        "-f",
        choices=[report_format.value for report_format in ReportFormat],
        default=ReportFormat.TERMINAL.value,
        help="Output format (default: terminal).",
    )
    check.add_argument("--provider", "-p", help="Provider adapter to use.")
    check.add_argument(
        "--model",
        help="Model to request from the provider (or the replay file for --provider replay).",
    )
    check.add_argument(
        "--strict-coverage",
        action="store_true",
        help="Treat changes with no governing document as failures.",
    )
    check.add_argument(
        "--output",
        "-o",
        help="Write the report to this path (relative to the working directory) instead of stdout.",
    )
    check.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the --output file if it already exists.",
    )

    return parser


def _run_check(args: argparse.Namespace) -> int:
    settings = Settings.from_env(provider_override=args.provider, model_override=args.model)
    try:
        model = build_model(settings)
    except ValueError as error:
        sys.stderr.write(f"error: {error}\n")
        return 2
    if settings.provider == "echo":
        sys.stderr.write(_ECHO_WARNING)
    options = CheckOptions(
        report_format=ReportFormat(args.format),
        strict_coverage=args.strict_coverage,
        output=args.output,
        force=args.force,
        max_context_chars=settings.max_context_chars,
    )
    return run_check(Path.cwd(), args.base, model, options)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "providers":
        for name in available_providers():
            sys.stdout.write(f"{name}\n")
        return 0

    return _run_check(args)


if __name__ == "__main__":
    raise SystemExit(main())
