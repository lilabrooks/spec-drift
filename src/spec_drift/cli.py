"""Command-line entry point for the walking-skeleton CLI.

Replace the `hello` command with your tool's real surface. The `ask` and
`providers` commands exercise the optional model-provider layer; if your CLI
does not call language models, delete them together with the `agents/`,
`config/`, `core/`, `providers/`, and `runtime/` packages and their tests.
"""

import argparse
import sys

from spec_drift import __version__
from spec_drift.config.settings import Settings
from spec_drift.providers.registry import available_providers
from spec_drift.runtime.factory import build_agent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spec-drift",
        description="Walking-skeleton CLI proving the template's quality gate end to end.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hello = subparsers.add_parser("hello", help="Print a greeting.")
    hello.add_argument("name", nargs="?", default="world", help="Who to greet.")

    ask = subparsers.add_parser("ask", help="Send one prompt to the configured model provider.")
    ask.add_argument("prompt", help="Prompt to send.")
    ask.add_argument("--provider", "-p", help="Provider adapter to use.")

    subparsers.add_parser("providers", help="List available provider adapters.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "hello":
        sys.stdout.write(f"Hello, {args.name}!\n")
        return 0

    if args.command == "providers":
        for name in available_providers():
            sys.stdout.write(f"{name}\n")
        return 0

    settings = Settings.from_env(provider_override=args.provider)
    try:
        agent = build_agent(settings)
    except ValueError as error:
        sys.stderr.write(f"error: {error}\n")
        return 2
    result = agent.run(args.prompt)
    sys.stdout.write(f"{result.text}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
