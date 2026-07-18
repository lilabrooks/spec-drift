---
title: Documentation log
type: log
status: current
date: 2026-07-17
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [documentation, log]
---

# Documentation log

Dated changes to the docs bundle, newest first.

## 2026-07-18

- Milestone 4 complete: reports and the `check` command. Added
  `src/spec_drift/report/` (terminal/Markdown/JSON rendering of an
  `AnalysisReport`, all describing the same findings; pure, no I/O),
  `src/spec_drift/checker.py` (the `spec-drift check` command wiring
  collect → analyze → render with the 0/1/2 exit-code contract), the `check`
  subparser in `cli.py`, and the committed JSON contract
  `schemas/report.schema.json`. Documented in `docs/specs/report.md` and mapped
  in `docs/okf-map.yml` (the schema is itself a governing contract; check-stale
  current). Verification: `tests/test_report.py` shows all three formats name
  every finding, the JSON output validates against the committed schema (via a
  dependency-free schema validator in `tests/schema_check.py`, in keeping with
  the zero-dependency stance), and the `check` command returns 0/1/2 per the
  contract — including an end-to-end console-script run. 105 tests green on
  Python 3.12, 3.13, and 3.14.
- Accepted ADR 0001 (drift-analysis finding schema and model contract) at the
  owner's direction: status flipped to `accepted`, index updated; it now binds
  future work. Friction noted for the kit: `scripts/okf new-adr` scaffolds ADR
  frontmatter without `owner`/`deciders`, which `check-okf-docs.py` requires —
  the omission surfaced only once the ADR became tracked. Added both fields by
  hand; worth fixing in the kit's ADR template.
- Milestone 3 complete: the drift-analysis engine (`src/spec_drift/analysis/`)
  and validated finding model. `analyze(changeset, model, *, strict_coverage)`
  judges each governed change with one model call carrying its diff and
  governing documents, records unmapped changes without a call, and validates
  the untrusted JSON reply into a `Finding` (classification + paired citations),
  degrading anything unverifiable to `insufficient-evidence`. `AnalysisReport`
  computes the exit code, with `unmapped` actionable only under
  `strict_coverage`. **Proposed ADR 0001 (`docs/adr/0001-analysis-contract.md`)
  authored for the finding schema and model contract — awaiting review; the
  engine is implemented against it.** Documented in `docs/specs/drift-analysis.md`
  and mapped in `docs/okf-map.yml`; also extended `docs/specs/analysis-inputs.md`
  for the new per-file-diff capability (check-stale current). Verification:
  `tests/test_analysis.py` with a deterministic scripted provider reproduces
  clean/drift/decision-required/insufficient-evidence/unmapped with valid
  citations and confirms `--strict-coverage` flips the unmapped exit code —
  92 tests green on Python 3.12, 3.13, and 3.14.
- Milestone 2 complete: the analysis-inputs subsystem (`src/spec_drift/inputs/`)
  — repository discovery, read-only Git diff loading with rename detection,
  unsafe-path filtering (`.env`, outside-root, ignored, binary, in that
  priority), and governing-document resolution from `docs/okf-map.yml`'s
  `mappings:` block, assembled by `collect_changes` into an immutable
  `ChangeSet`. Zero new runtime dependencies: Git via the command line, the map
  via a purpose-built subset parser (`adr-suggest` clean). Documented in the new
  `docs/specs/analysis-inputs.md` and mapped in `docs/okf-map.yml` (check-stale
  current). Verification: fixture tests in `tests/test_inputs.py` cover a clean
  branch, modified/renamed/deleted/added changes, unmapped changes, invalid base
  ref, execution outside a repository, and `.env`/binary/ignored/outside-root
  exclusion — 77 tests green on Python 3.12, 3.13, and 3.14.
- Milestone 1 complete: package, canonical commands, fixture repositories, and
  quality gate established. Added `tests/repo_fixtures.py` — deterministic,
  offline builders for the clean and drift git fixture repositories (kit-style
  `docs/specs/` + `docs/okf-map.yml`, a `base` ref, and a governed change on
  `main`; the drift fixture removes the manager-approval check its spec
  requires) — with contract tests in `tests/test_repo_fixtures.py`, plus a
  `--help` CLI test. Verification passed: `spec-drift --help`, `make test`, and
  `make check` green on Python 3.12, 3.13, and 3.14 (`make check-all`).
  Non-blocking: new test files are unmapped in `docs/okf-map.yml` until their
  governing specs exist. No ADR-shaped changes (`adr-suggest` clean).

## 2026-07-17

- Completed the initial project setup after seeding from python-cli-template and
  installing the kit: rewrote `README.md` for spec-drift, resolved the kit's
  `CLAUDE.2.md` playbook candidate into a single-source `AGENTS.md` (shared by
  Claude Code and Codex) with `CLAUDE.md` importing it, and aligned the
  command name in `docs/GOAL.md` from `specdrift` to `spec-drift` to match the
  installed console command.
- Started the project documentation bundle from the Python CLI template.
