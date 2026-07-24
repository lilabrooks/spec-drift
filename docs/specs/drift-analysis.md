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
findings. `spec_drift.analysis.analyze(changeset, model, *, strict_coverage,
max_context_chars)` is the entry point. It is read-only and provider-neutral:
any `LanguageModel` implementation drives it, and tests use offline scripted
providers. The finding schema and model contract are governed by
[ADR 0001](../adr/0001-analysis-contract.md); the untrusted-diff threat model
and prompt structure by [ADR 0003](../adr/0003-prompt-injection-threat-model.md).

## Contract

- **One unit per governed change.** Each governed change produces at most one
  model call carrying the file's diff and the full text of its governing
  documents. There is no retry loop and no conversation.
- **The diff is untrusted; documents are trusted.** The request places the
  governing documents before the diff and fences both with a per-request secret
  token, so a crafted diff cannot forge a document or smuggle instructions past
  the trust boundary (ADR 0003).
- **Evidence is line-anchored.** Every evidence line in the request carries its
  real line number in a `<number>| ` gutter — documents by their own numbering,
  diffs by the changed file's (removed lines marked `-`) — and the prompt states
  those numbers are authoritative, so a citation names the governing clause and
  the changed line rather than a counted guess (ADR 0005).
- **Evidence is bounded mechanically.** When a change's diff plus its governing
  documents exceed `max_context_chars`, the finding is `insufficient-evidence`
  and no model call is made — the CLI never silently truncates material a
  provider would otherwise drop. The bound defaults to 400 000 characters and is
  configurable via `SPEC_DRIFT_MAX_CONTEXT_CHARS`.
- **An unavailable diff is not judged.** A governed change whose diff is empty
  (a genuinely empty diff or a nonzero git exit) becomes `insufficient-evidence`
  with no model call, rather than a verdict on a change the tool cannot see.
- **Unmapped changes are recorded, not judged.** A change the input layer left
  unmapped becomes an `unmapped` finding with no model call — analysis never
  invents a governing contract.
- **Findings are validated.** Each `Finding` has a `Classification` of `clean`,
  `drift`, `decision-required`, `insufficient-evidence`, or `unmapped`, a
  one-sentence summary, and up to two repo-relative `Citation`s (source,
  document). `drift` and `decision-required` require both a source line and a
  document citation naming one of the change's governing documents.
- **Contradictory documents are reported, not resolved.** When a change's
  governing documents state different requirements for the same thing, the
  finding is `insufficient-evidence` and the summary names which documents
  disagree and on what (ADR 0007). The accepted-ADR precedence is scoped to a
  document disagreeing with the *implementation*; it is never used to rank one
  governing document above another, because that would silently pick a side and
  hide the real defect — that the documentation set disagrees with itself.
- **Untrusted output degrades safely.** Unparseable JSON, an unknown or
  disallowed classification, a document citation outside the governing set, or a
  judged classification missing required evidence all yield
  `insufficient-evidence` — never a trusted verdict and never `unmapped` from the
  model. A reply wrapped in a code fence, or prefixed with a prose preamble, is
  parsed rather than discarded — the outermost JSON object is retried before
  giving up — which parses more forgivingly without trusting more, since the
  payload still faces identical validation.
- **Provider failures propagate.** A `LanguageModel` that cannot reach its
  model raises `ProviderError`; `analyze` lets it propagate so the CLI maps it to
  exit code 2 with an actionable message, never a stack trace.
- **Excluded paths are carried through.** `AnalysisReport` also carries the
  input layer's `excluded` paths (path and reason only; the model never saw
  their content) so the safety behavior is auditable in the report.
- **Severity drives the exit code.** `AnalysisReport.exit_code()` returns 1 when
  any finding requires review: `drift`, `decision-required`, or
  `insufficient-evidence` always, and `unmapped` only under `strict_coverage`.
  Otherwise 0. Excluded paths never affect the exit code. Exit code 2
  (input/repository/configuration/provider failure) is the CLI's.

## Boundaries

- Does not render findings (terminal/Markdown/JSON output is a later component)
  or decide the process exit status — it only computes the exit *code value*.
- Reads governing documents from disk as text; a mapped document missing on disk
  is not treated as evidence.
- The prompt wording and JSON keys are a provider-contract surface: changing
  them requires revising ADR 0001 (structure/threat model: ADR 0003).
