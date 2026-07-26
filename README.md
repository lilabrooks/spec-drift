# spec-drift

> [!WARNING]
> **Experiment concluding.** This implementation is being retired. The code
> and history will remain available as a historical reference, but new use is
> not recommended. A smaller read-only Git evidence collector and cross-agent
> review skill are being evaluated and will be linked here only if they pass
> their acceptance checks.

[![Specs + ADRs](https://img.shields.io/badge/specs%20%2B%20ADRs-included-0A7)](docs/index.md)
[![Claude Code + Codex](https://img.shields.io/badge/agents-Claude%20Code%20%2B%20Codex-5D3FD3)](AGENTS.md)
[![Tests](https://github.com/lilabrooks/spec-drift/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/lilabrooks/spec-drift/actions/workflows/tests.yml)
[![OKF](https://img.shields.io/badge/docs-OKF%200.1-blue)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
[![License: Source Visible](https://img.shields.io/badge/license-source--visible-red)](LICENSE)

Detect when a code change no longer matches the specs and architecture
decisions that govern it.

Engineering teams record intended behavior in specifications and ADRs, but code
changes can quietly contradict those documents. `spec-drift` examines committed
Git changes alongside their governing documents, then reports each finding with
source and document citations.

> **License:** The source is visible for inspection under custom proprietary
> terms. Installation, execution, modification, distribution, and production
> use require prior written permission. GitHub's Terms of Service govern rights
> available through GitHub's functionality. See [LICENSE](LICENSE).

## Contents

- [What it does](#what-it-does)
- [Install](#install)
- [Use it in a repository](#use-it-in-a-repository)
- [Classifications and exit codes](#classifications-and-exit-codes)
- [Verified demo](#verified-demo)
- [Development](#development)
- [Help and contributing](#help-and-contributing)

## What it does

- Reads committed changes in `base..HEAD` without modifying the working tree.
- Resolves governing documents through `docs/okf-map.yml`.
- Gives accepted ADRs precedence when implementation and decisions disagree.
- Validates untrusted model output before rendering or serialization.
- Cites repository-relative source and document lines for every judged finding.
- Emits terminal, Markdown, or JSON reports for local scripts and CI.
- Refuses to overwrite an existing report unless `--force` is supplied.

### Example finding

When a change removes an approval check required by a mapped specification,
the Markdown report names the conflict and cites both sides:

| File | Classification | Source | Document | Summary |
| --- | --- | --- | --- | --- |
| `src/refunds.py` | `drift` | `src/refunds.py:5` | `docs/specs/refunds.md:7` | The change removes the required manager-approval check. |

Result: `1 drift (exit 1)`

See [`docs/GOAL.md`](docs/GOAL.md) for the complete contract, success criteria,
non-goals, and milestone backlog.

## Install

These instructions are for the copyright holder and people who have prior
written permission to use the software. The checkout requires Python 3.12+,
Git, and [uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-extras
. .venv/bin/activate
spec-drift --help
```

The provider extras are included by `--all-extras`. A portable `venv` and `pip`
fallback appears under [Development](#development).

## Use it in a repository

Run `spec-drift` from any directory inside the target Git repository. It
compares committed changes between the selected base and `HEAD`.

### Map source files to governing documents

Create `docs/okf-map.yml` in the target repository:

```yaml
mappings:
  - source: "src/payments/**"
    docs:
      - "docs/specs/payments.md"
      - "docs/adr/0001-payment-provider.md"
```

Source patterns and document paths are repository-relative. `*` matches within
one path segment; `**` crosses directories. A changed file with no matching
entry is reported as `unmapped`.

This repository stores its knowledge as an
[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundle. `docs/okf-map.yml` is the source-to-document mapping convention used by
[claude-okf-repo-kit](https://github.com/lilabrooks/claude-okf-repo-kit).

### Choose a provider

List the available adapter names:

```bash
spec-drift providers
```

For live analysis, place `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in the process
environment through your shell, CI secret store, or secret manager. Keep real
keys out of tracked files, screenshots, and shared shell history.
[`.env.example`](.env.example) lists the supported variables; the CLI does not
load `.env` automatically. If you use a `.env` file in another repository,
confirm that repository ignores it before adding a key.

Run with your chosen provider:

```bash
# Anthropic
spec-drift check --base origin/main --provider anthropic

# OpenAI
spec-drift check --base origin/main --provider openai
```

You can set `SPEC_DRIFT_PROVIDER` instead of passing `--provider` each time.
Running without either setting selects `echo`, an offline wiring check that
reports governed changes as `insufficient-evidence`.

Write a machine-readable report:

```bash
spec-drift check --base v1.4.0 --provider anthropic \
  --format json --output drift-report.json
```

### Provider data and cost

A governed change with a readable diff inside the context limit produces one
model request containing that file's Git diff and its mapped governing
documents. Before any request, `spec-drift` excludes ignored files, `.env`
files, credential files, binaries, and paths outside the repository root. API
calls can incur provider charges, so choose a provider and model that fit your
organization's code-handling and budget policies.

## Classifications and exit codes

| Classification | Meaning | Default exit code |
| --- | --- | --- |
| `clean` | The change agrees with its governing documents. | `0` |
| `drift` | The change conflicts with a governing requirement. | `1` |
| `decision-required` | An architecture-boundary change needs a corresponding decision record. | `1` |
| `insufficient-evidence` | The mapped change cannot be judged from the available evidence. | `1` |
| `unmapped` | No governing document covers the changed file. | `0` |

`--strict-coverage` changes `unmapped` to exit `1`. Exit code `2` means an
input, repository, configuration, or provider failure prevented analysis.

## Verified demo

The repository ships deterministic `clean` and `drift` fixtures. They use the
offline `replay` provider, so the demo needs no vendor key and makes no model
request.

From the repository root, create both temporary fixture repositories:

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
uv sync --all-extras
SPEC_DRIFT="$PWD/.venv/bin/spec-drift"
tmp="$(mktemp -d)"
uv run python scripts/ci-fixture.py --fixture-dir "$tmp"
```

The clean fixture exits `0`:

```bash
(
  cd "$tmp/clean"
  SPEC_DRIFT_REPLAY_FILE="$PWD/replay.json" \
    "$SPEC_DRIFT" check --base base --provider replay
)
```

The drift fixture exits `1`; the trailing `test` confirms that result:

```bash
(
  cd "$tmp/drift"
  SPEC_DRIFT_REPLAY_FILE="$PWD/replay.json" \
    "$SPEC_DRIFT" check --base base --provider replay
  test "$?" -eq 1
)
```

<details>
<summary>More demo cases</summary>

Write a JSON report for the clean fixture:

```bash
(
  cd "$tmp/clean"
  SPEC_DRIFT_REPLAY_FILE="$PWD/replay.json" \
    "$SPEC_DRIFT" check --base base --provider replay \
    --format json --output report.json
)
```

Try a missing base ref. It exits `2`; the trailing `test` confirms that result:

```bash
(
  cd "$tmp/clean"
  SPEC_DRIFT_REPLAY_FILE="$PWD/replay.json" \
    "$SPEC_DRIFT" check --base missing-ref --provider replay
  test "$?" -eq 2
)
```

</details>

## Development

Using [uv](https://docs.astral.sh/uv/):

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

`make check` runs the full gate: environment preflight, ruff lint and formatting
checks, mypy `strict`, pytest with a 90% branch-coverage floor, documentation
validation, and secret scanning. GitHub Actions runs the same checks across
Python 3.12 through 3.14. Use `make check-all` for the local version matrix.

## Does it actually catch things?

An [export-migration showcase](docs/case-studies/export-migration.md) runs a
single believable PR — moving customer exports onto a queue and CDN — that goes
wrong five ways at once, and reports all five classifications plus the excluded
secrets in one command: ordering drift, a cross-tenant leak that reads like a
tightening, an undecided architecture boundary, two governing documents that
contradict each other, and a privacy rule no type system can express. Every
citation in it was checked against the file.


A [payments worked example](docs/case-studies/payments-idempotency.md) shows the
shape of bug this is for: a retry refactor that mints a fresh idempotency key per
attempt. The code is valid, the mocked-gateway tests pass, lint and typing stay
green — and every retry becomes a second charge on a real customer's card.
`spec-drift` reports `drift` against the clause that forbids it, plus
`decision-required` for the background queue that arrived with no decision
record. That case study also records the run where its own prediction failed, and
what that exposed.


[A case study](docs/case-studies/kit-layout-stamp-drift.md) replays a real bug
that shipped for eight days in another repository and took a full manual audit —
every script line-read — to find. Given the same change in a diff, `spec-drift`
classified it as `drift` in one model call and independently described the same
consequence the audit had documented. The same run also exposed a defect in its
own citation precision, which is written up there and fixed under
[ADR 0005](docs/adr/0005-line-anchored-evidence.md). Both halves are recorded:
what it caught, and where it fell short.

## Repository layout

```text
├── AGENTS.md            # shared agent instructions (Claude Code + Codex)
├── CLAUDE.md            # imports AGENTS.md + preloads the goal for Claude Code
├── docs/                # the OKF knowledge bundle
│   ├── GOAL.md          # goal, success criteria, constraints, milestone backlog
│   ├── specs/           # component specifications
│   ├── adr/             # architecture decision records
│   └── okf-map.yml      # source-to-document mapping
├── src/spec_drift/      # the CLI, analysis pipeline, providers, and reports
└── tests/               # CLI, provider-layer, and repository-health tests
```

## Help and contributing

- Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change. Preparing
  a code contribution requires prior written permission under this repository's
  source-visible terms.
- Use [SUPPORT.md](SUPPORT.md) for setup questions and bug reports.
- Report vulnerabilities through the process in [SECURITY.md](SECURITY.md).
- See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

Copyright (c) 2026 Lila Brooks. All Rights Reserved. The source is public for
inspection; no permission to install, execute, modify, distribute, or deploy it
is granted without prior written permission. See [LICENSE](LICENSE).
