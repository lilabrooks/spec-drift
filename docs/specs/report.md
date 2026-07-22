---
title: Reports and the check command
type: Spec
status: current
date: 2026-07-18
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [report, cli, json, exit-codes]
---

# Reports and the check command

Reporting turns an `AnalysisReport` into output, and the `spec-drift check`
command wires the whole pipeline together with a stable exit-code contract.

## Output formats

`spec_drift.report.render(report, format)` produces one of three forms, all
describing the same findings — each finding's file path, classification, and
summary, with source and document citations where present — plus the paths the
input layer **excluded** from analysis (path and reason only; their content
never reached the model):

- **terminal** — one line per finding, a one-line tally with the exit code, and
  an excluded section when any paths were excluded.
- **markdown** — a findings table plus the tally, and an "Excluded from
  analysis" table when applicable, for pasting into a PR or CI summary.
- **json** — the machine-readable form, validated against
  [`schemas/report.schema.json`](../../schemas/report.schema.json), carrying a
  `findings` array and an `excluded` array. The schema is the governing contract
  for that output; the two move together.

Rendering is pure (returns a string, no I/O). An empty report renders in every
format without error.

## The check command

`spec-drift check --base <ref> [--format terminal|markdown|json] [--provider
<name>] [--strict-coverage] [--output PATH] [--force]` discovers the repository
from the working directory, collects and analyzes `base..HEAD`, renders to the
chosen format, and exits per the contract below. It never modifies the
repository.

## Report-file output

By default the report goes to stdout and the run is read-only. `--output PATH`
writes it to a file instead, safe by default:

- **Stays within the working directory.** `PATH` is resolved relative to the
  directory the command runs in; an absolute path or one that escapes via `..`
  is refused (exit 2), never written.
- **No silent overwrite.** An existing file is preserved; writing over it
  requires `--force`. A forced write replaces only that file.

On a successful write, stdout stays empty and a confirmation goes to stderr, so
the exit code and any redirected report remain clean for scripts.

## Exit-code contract

- **0** — no change requires review. `unmapped` findings alone do not fail
  unless `--strict-coverage` is set.
- **1** — at least one `drift`, `decision-required`, or `insufficient-evidence`
  finding on a governed change (or any `unmapped` finding under
  `--strict-coverage`).
- **2** — an input, repository, configuration, or provider failure prevented
  analysis: not a Git repository, an unresolvable base ref, an unknown provider,
  a malformed `docs/okf-map.yml` (`MappingError`), or a provider that could not
  reach its model (`ProviderError`, e.g. a missing API key). Reported as a
  message on stderr with no stack trace.

The JSON report carries the 0/1 code in its `exit_code` field; 2 is a process
outcome only and is never serialized.

## Boundaries

- Does not classify drift or resolve governing documents — it renders what
  [drift-analysis.md](drift-analysis.md) produced.
