---
title: CI integration
type: Spec
status: current
date: 2026-07-18
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [ci, exit-codes, replay, workflow]
---

# CI integration

spec-drift plugs into CI through the `check` command's exit code, and ships a
deterministic replay provider so the integration can be exercised offline. See
[ADR 0002](../adr/0002-ci-integration.md) for the decision.

## Gating on the exit code

A CI job runs `spec-drift check --base <ref>` and lets the process exit code
decide the build: **1** fails it (drift, decision-required, or
insufficient-evidence on a governed change, or unmapped under
`--strict-coverage`), **0** passes it, **2** fails it on an input/repository/
provider error. The exit-code contract lives in
[report.md](report.md).

## The replay provider

`--provider replay` is an offline, deterministic `LanguageModel` that plays back
canned JSON replies keyed by the changed-file path. It reads a JSON file
(`{"src/path.py": "<reply>", "_default": "<reply>"}`) named by the
`SPEC_DRIFT_REPLAY_FILE` environment variable or the provider model argument,
and speaks the same reply contract as a real provider ([ADR 0001](../adr/0001-analysis-contract.md)).
It lets the real `check` command run reproducibly without a vendor key — for
demos, for CI wiring tests, and for golden replay files committed beside
fixtures.

## The ci-fixture demonstration

`make ci-fixture` (running `scripts/ci-fixture.py`) builds a drift fixture and a
clean fixture, runs the real `check` command against each with the replay
provider, and asserts the drift fixture fails (exit 1) while the clean fixture
passes (exit 0), printing both Markdown reports. The script also accepts
`--fixture-dir PATH` for quickstart and acceptance runs that need to keep those
throwaway repositories and their `replay.json` files on disk for follow-up
commands. The committed `.github/workflows/drift.yml` runs the default temporary
mode in a hosted runner — no secret, deterministic.

## Owner-gated real-provider run

Running `check` against the repository's own diff with a real provider needs an
API-key secret and makes a paid, non-deterministic call. It is intentionally
outside the demo workflow and is confirmed during the acceptance pass.

## Boundaries

- Does not define branch protection, required checks, or deploy steps — only how
  spec-drift itself signals pass/fail.
- The replay provider is for reproducible runs, not a substitute for a real
  provider in production analysis.
