# spec-drift

Detect when code has silently drifted from the specs and architecture decisions
that are supposed to govern it.

Engineering teams record intended behavior in specifications and ADRs, but code
changes can quietly contradict those documents. `spec-drift` examines a Git diff
alongside the repository's Markdown specs, ADRs, and optional source-to-document
map, then produces an evidence-backed report classifying each governed change —
citing the exact source change and the governing clause.

> **Status: early development.** The core `check` command, report formats,
> safety checks, replay-provider CI demo, and quality gate are in place. The
> project is still pre-1.0, so command details may change while the first public
> release settles.

## Quickstart

Requires Python 3.12+, Git, and [uv](https://docs.astral.sh/uv/). From a fresh
checkout:

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
uv sync --all-extras
SPEC_DRIFT="$PWD/.venv/bin/spec-drift"
tmp="$(mktemp -d)"
uv run python scripts/ci-fixture.py --fixture-dir "$tmp"
```

Analyze a clean change. It exits `0`:

```bash
(cd "$tmp/clean" && SPEC_DRIFT_REPLAY_FILE="$PWD/replay.json" "$SPEC_DRIFT" check --base base --provider replay)
```

Analyze a drift change. It exits `1`, so the `test` confirms that this is the
expected result:

```bash
(cd "$tmp/drift" && SPEC_DRIFT_REPLAY_FILE="$PWD/replay.json" "$SPEC_DRIFT" check --base base --provider replay; test "$?" -eq 1)
```

Write a JSON report:

```bash
(cd "$tmp/clean" && SPEC_DRIFT_REPLAY_FILE="$PWD/replay.json" "$SPEC_DRIFT" check --base base --provider replay --format json --output report.json)
```

Try a missing base ref. It exits `2` with a clear error:

```bash
(cd "$tmp/clean" && SPEC_DRIFT_REPLAY_FILE="$PWD/replay.json" "$SPEC_DRIFT" check --base missing-ref --provider replay; test "$?" -eq 2)
```

The quickstart uses the deterministic `replay` provider, so it needs no vendor
key and makes no model request.

## What it does

Run against any supported Git repository:

```bash
spec-drift check --base origin/main
```

`spec-drift`:

- Read the Git diff without modifying the working tree, and exclude ignored
  files, `.env` files, credentials, and binaries.
- Resolve the governing specs and ADRs through an optional mapping file —
  `docs/okf-map.yml`, the claude-okf-repo-kit convention, is a zero-configuration
  first-class target — and documented repository conventions.
- Evaluate each governed change against those documents with a configured model
  provider, giving accepted ADRs precedence over implementation when they
  disagree.
- Classify governed changes as `clean`, `drift`, `decision-required`, or
  `insufficient-evidence`; report changes with no governing document as
  `unmapped` — a non-blocking note by default, promoted to a failure only under
  `--strict-coverage`.
- Cite repository-relative paths and line numbers for every substantive claim.
- Emit terminal, Markdown, or JSON output with stable exit codes suitable for
  local scripts and CI:

  ```bash
  spec-drift check --base v1.4.0 --format json --output drift-report.json
  ```

- Stay read-only unless an output file is explicitly requested, and refuse to
  overwrite an existing report without `--force`.

Exit codes: `0` no actionable drift, `1` drift / decision required / insufficient
evidence on a governed change, `2` input, repository, configuration, or provider
failure. See [`docs/GOAL.md`](docs/GOAL.md) for the full contract, success
criteria, non-goals, and milestone backlog.

## Development

Requires Python 3.12+ and Git. Using [uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-extras
uv run make check
```

Portable fallback:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,anthropic,openai]"
make check
```

`make check` runs the full gate: environment preflight, ruff (lint + format),
mypy `strict`, pytest with a 90% branch-coverage floor, and documentation
validation — mirrored by GitHub Actions across Python 3.12–3.14. Use
`make check-all` to run the gate across every supported interpreter.

The default `echo` provider is offline and needs no credentials. Anthropic and
OpenAI adapters are opt-in extras that read their key from the environment; copy
`.env.example` for the variable names (nothing loads `.env` automatically — the
settings layer reads `os.environ` directly).

## Repository layout

```
├── AGENTS.md            # shared agent instructions (Claude Code + Codex)
├── CLAUDE.md            # imports AGENTS.md + preloads the goal for Claude Code
├── docs/                # the knowledge bundle
│   ├── GOAL.md          # goal, success criteria, constraints, milestone backlog
│   ├── specs/ · adr/    # component specs and architecture decision records
│   └── okf-map.yml      # source-to-knowledge mapping
├── src/spec_drift/      # the CLI, analysis pipeline, providers, and reports
└── tests/               # CLI, provider-layer, and repository-health tests
```

## License

MIT — see [LICENSE](LICENSE).
