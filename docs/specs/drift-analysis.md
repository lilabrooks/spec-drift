---
title: Drift analysis
type: Spec
status: current
date: 2026-07-18
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [analysis, findings, provider, classification]
---

# Drift analysis

Drift analysis turns a resolved `ChangeSet` (see
[analysis-inputs.md](analysis-inputs.md)) into an `AnalysisReport` of validated
findings. `spec_drift.analysis.analyze(changeset, model, *, strict_coverage)` is
the entry point. It is read-only and provider-neutral: any `LanguageModel`
implementation drives it, and tests use offline scripted providers. The finding
schema and model contract are governed by
[ADR 0001](../adr/0001-analysis-contract.md).

## Contract

- **One unit per governed change.** Each governed change produces exactly one
  model call carrying the file's diff and the full text of its governing
  documents. There is no retry loop and no conversation.
- **Unmapped changes are recorded, not judged.** A change the input layer left
  unmapped becomes an `unmapped` finding with no model call — analysis never
  invents a governing contract.
- **Findings are validated.** Each `Finding` has a `Classification` of `clean`,
  `drift`, `decision-required`, `insufficient-evidence`, or `unmapped`, a
  one-sentence summary, and up to two repo-relative `Citation`s (source,
  document). `drift` and `decision-required` require both a source line and a
  document citation naming one of the change's governing documents.
- **Untrusted output degrades safely.** Unparseable JSON, an unknown or
  disallowed classification, a document citation outside the governing set, or a
  judged classification missing required evidence all yield
  `insufficient-evidence` — never a trusted verdict and never `unmapped` from the
  model.
- **Severity drives the exit code.** `AnalysisReport.exit_code()` returns 1 when
  any finding requires review: `drift`, `decision-required`, or
  `insufficient-evidence` always, and `unmapped` only under `strict_coverage`.
  Otherwise 0. Exit code 2 (input/repository/provider failure) is the CLI's.

## Boundaries

- Does not render findings (terminal/Markdown/JSON output is a later component)
  or decide the process exit status — it only computes the exit *code value*.
- Reads governing documents from disk as text; a mapped document missing on disk
  is not treated as evidence.
- The prompt wording and JSON keys are a provider-contract surface: changing
  them requires revising ADR 0001.
