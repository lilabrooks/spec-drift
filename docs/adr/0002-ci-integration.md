---
type: ADR
title: CI integration via exit-code gating and a deterministic replay provider
description: CI gates on the check exit code; a shipped offline replay provider makes the integration testable without a vendor key.
tags: [adr, ci, provider, exit-codes]
timestamp: 2026-07-18T19:14:02Z
status: accepted
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Accepted on 2026-07-19 at the owner's direction.

# Context

Milestone 6 adds a CI integration, which `docs/GOAL.md` marks as decision-shaped
(CI ownership). The question is how a repository wires `spec-drift` into CI, and
how that integration is demonstrated and tested — the milestone requires a local
`make ci-fixture` target that fails on a drift fixture and passes on a clean one.
The obstacle: the real `check` command needs a model provider, and CI cannot
depend on a vendor key or a network call to be deterministic and free.

# Decision

**Gate on the exit code.** CI runs `spec-drift check --base <ref>` and lets its
process exit code fail or pass the job: 1 when review is required, 0 when clean,
2 on an input/repository/provider failure (per `docs/specs/report.md`). This is
the public CI contract.

**Ship a `replay` provider.** A deterministic, offline `LanguageModel` that
plays back canned JSON replies keyed by the changed-file path, read from a file
named by `SPEC_DRIFT_REPLAY_FILE` (or the `SPEC_DRIFT_MODEL` path). It speaks the
same model I/O contract as ADR 0001 — no new contract — and lets the real
`check` command run reproducibly without a key. It joins `echo`, `anthropic`,
and `openai` in the provider registry.

**`make ci-fixture`.** Builds a drift fixture and a clean fixture, runs the real
`check` command against each with the `replay` provider, asserts exit 1 then
exit 0, and prints the Markdown report — the same steps the example workflow
runs.

**Example workflow.** A committed GitHub Actions workflow runs `make ci-fixture`
(deterministic, no secret), demonstrating the integration in a hosted runner. A
real-provider run against the repository's own diff is owner-gated (needs an
API-key secret) and confirmed during the acceptance pass.

# Alternatives considered

- **Document a workflow only, no local target.** Rejected: the local target is
  the milestone's verification and lets users test their wiring offline.
- **Use a real provider in CI by default.** Rejected as the default: needs a
  secret, costs API calls, and is non-deterministic. Kept as an owner-gated
  option.
- **A demo script using the internal API instead of the CLI.** Rejected: it
  would not exercise the real `check` command, weakening the demonstration.
- **Overload the `echo` provider to emit findings.** Rejected: `echo` is a
  trivial mirror; a dedicated `replay` provider keeps both purposes clear.

# Consequences

- The `providers` command now lists `replay`, and the exit-code contract becomes
  a public CI interface — changing either is a contract change needing an ADR.
- Users can test their CI wiring offline and reproducibly, and record golden
  replay files alongside fixtures.
- A small new surface exists: the replay file format (path-to-reply JSON).

# Rollback / revisit trigger

Revisit if exit-code gating proves too coarse (e.g. wanting to gate on `drift`
but not `insufficient-evidence`), or if the `replay` provider goes unused.
Reverting removes the provider, the target, and the workflow; no persisted data
migrates.
