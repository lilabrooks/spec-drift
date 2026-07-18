# spec-drift

Detect when code has silently drifted from the specs and architecture decisions
that are supposed to govern it.

Engineering teams record intended behavior in specifications and ADRs, but code
changes can quietly contradict those documents. `spec-drift` examines a Git diff
alongside the repository's Markdown specs, ADRs, and optional source-to-document
map, then produces an evidence-backed report classifying each governed change —
citing the exact source change and the governing clause.

> **Status: early development.** This repository is a walking skeleton seeded
> from [python-cli-template](https://github.com/lilabrooks/python-cli-template)
> with the [claude-okf-repo-kit](https://github.com/lilabrooks/claude-okf-repo-kit)
> operating contract on top. The quality gate, provider-neutral model layer, and
> CI are in place; the drift-analysis command surface described below is the goal
> being built, milestone by milestone, per [`docs/GOAL.md`](docs/GOAL.md). The
> installed CLI currently exposes the skeleton commands (`hello`, `ask`,
> `providers`).

## What it will do

Run against any supported Git repository:

```bash
spec-drift check --base origin/main
```

`spec-drift` will:

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
├── src/spec_drift/      # the CLI (skeleton today; drift analysis in progress)
└── tests/               # CLI, provider-layer, and repository-health tests
```

## License

MIT — see [LICENSE](LICENSE).
