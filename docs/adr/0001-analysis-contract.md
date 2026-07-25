---
type: ADR
title: Drift-analysis finding schema and model contract
description: Findings are a fixed enum plus paired citations; the model returns validated JSON and is never trusted to self-classify unmapped.
tags: [adr, analysis, provider-contract, schema]
generated: { by: claude-code/opus-4.8, at: 2026-07-18T13:44:55Z }
status: accepted
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Accepted 2026-07-18. Binds future work; supersede only via a new ADR.

ADR 0009 supersedes this ADR's invalid-output conversion for schema v2:
mechanically invalid model evidence becomes a structured failed run outcome
rather than an `insufficient-evidence` finding. The schema-v1 decision remains
historical and the rest of this ADR stays accepted.

# Context

Milestone 3 introduces the drift-analysis engine — the first component that
calls a model. `docs/GOAL.md` marks two things here as decision-shaped and
requiring a proposed ADR before implementation: the **output schema** (how a
finding is structured) and the **provider contract** (what the model is asked
for and how its answer is trusted). The goal also constrains both: every
finding on a governed change must cite evidence from *both* the diff and a
governing document; missing evidence yields `insufficient-evidence`; a change
with no governing document is `unmapped`, never a judged finding; and model
output is untrusted input that must be parsed and validated before use.

# Decision

**Finding schema.** A `Finding` carries a repository-relative source `path`, a
`Classification` from a closed enum — `clean`, `drift`, `decision-required`,
`insufficient-evidence`, `unmapped` — a one-sentence `summary`, and up to two
`Citation`s (`source`, `document`), each a repo-relative path with an optional
line number. `drift` and `decision-required` on a governed change require
*both* citations; the document citation must name one of that change's mapped
governing documents.

**Model contract.** For each governed change the engine sends one request (one
model call per analysis unit, per the goal's non-goal on retry loops) carrying
the file's diff and the full text of its governing documents, and asks for a
single JSON object: `{classification, source_line, document_path,
document_line, summary}`. The engine supplies the source path (it is known) and
validates the reply:

- Unparseable JSON, a `classification` outside `{clean, drift,
  decision-required, insufficient-evidence}`, or a `document_path` not among the
  change's governing docs → the finding is forced to `insufficient-evidence`.
- `drift`/`decision-required` missing a `source_line` or a document citation →
  forced to `insufficient-evidence`.
- The model may never return `unmapped`; that classification is assigned by the
  engine (no model call) for changes the input layer left unmapped.

Exit-relevant severity lives on the report: `drift`, `decision-required`, and
`insufficient-evidence` are actionable (exit 1); `unmapped` is actionable only
under `--strict-coverage`; `clean` never is.

# Alternatives considered

- **Free-text findings.** Rejected: unparseable, unverifiable, and impossible to
  render as JSON later (milestone 4) or to validate citations against.
- **Trusting the model to label `unmapped` or to cite arbitrary documents.**
  Rejected: violates the untrusted-output constraint and would let the model
  invent a governing contract the map never declared.
- **A tool/function-calling schema instead of JSON-in-text.** Rejected for now:
  the `LanguageModel` boundary is a single text `complete()` call, and JSON in
  text keeps every provider (including offline fixtures) uniform. Revisit if a
  provider's structured-output mode proves materially more reliable.
- **Adding a JSON-schema validation dependency.** Rejected: the object is small
  and fixed; stdlib `json` plus explicit checks keep the zero-dependency stance.

# Consequences

- Findings are renderable to terminal, Markdown, and JSON (milestone 4) and
  their citations are checkable against real paths and the map.
- The engine is provider-neutral and testable offline: a scripted fixture model
  returning canned JSON reproduces every classification deterministically.
- The prompt wording and JSON keys become a compatibility surface: changing them
  is a provider-contract change and needs its own ADR.
- Cost/latency scale linearly with governed changes (one call each); a large
  diff is several units, never a retry loop.

# Rollback / revisit trigger

Revisit if real providers cannot hold the JSON contract reliably (frequent
`insufficient-evidence` from parse failures rather than genuine ambiguity), or
if a structured-output/tool API would raise fidelity enough to justify widening
the `LanguageModel` boundary. Reverting means replacing the schema and the
parse/validate layer; findings are internal, so no persisted data migrates.
