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
