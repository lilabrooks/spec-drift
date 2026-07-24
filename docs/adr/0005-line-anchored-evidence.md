---
type: ADR
title: Line-anchored evidence in model context
description: Documents and diffs carry their real line numbers in a gutter, so a citation names the governing clause and the changed line instead of a counted guess.
tags: [adr, provider-contract, prompt, evidence]
timestamp: 2026-07-24T01:34:17Z
status: accepted
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Accepted 2026-07-24. Binds future work; supersede only via a new ADR. Refines
the prompt-assembly surface of [ADR 0001](0001-analysis-contract.md), whose
rollback trigger reserves prompt changes for their own ADR, and preserves the
fencing [ADR 0003](0003-prompt-injection-threat-model.md) requires. The gutter
format and the prompt sentences naming it now join the ADR 0001 compatibility
surface. The validation alternative rejected below stays deferred, not dropped:
it is this ADR's revisit trigger, not a pending obligation.

# Context

Paired citations are the product's headline promise: `docs/GOAL.md` requires
every finding on a governed change to cite evidence from *both* the diff and the
governing document, and ADR 0001 makes them mandatory for `drift` and
`decision-required`. Validation enforces that a citation *exists* and that its
document is in the change's governing set — but nothing checks whether the line
number is meaningful, and nothing helped the model produce a good one.

A live run against a real bug (see
[docs/case-studies/kit-layout-stamp-drift.md](../case-studies/kit-layout-stamp-drift.md))
exposed the cost. The model classified the change correctly and explained it
accurately, then cited `installer-scripts.md:1` — the `---` frontmatter opener —
when the governing clause was on line 83, and `update-existing-repo:4`
(`set -euo pipefail`) when the change was near line 956. The verdict was right
and the evidence pointers were noise, which is the half of the promise a
reviewer actually clicks.

The cause is structural rather than a prompt-wording weakness: the request
carried a unified diff and unnumbered document text, so the model had to *count
lines* to produce either number. Counting is a known-poor operation for language
models, and no amount of instruction fixes an input that withholds the answer.

# Decision

Every line of evidence in the request carries its real line number in a
fixed-width gutter (`<number>| `), and the prompt states that those numbers are
authoritative and must be cited verbatim:

- **Documents** are numbered from 1 by their own lines, so `document_line` can
  name the clause that the change contradicts.
- **Diffs** are annotated with the line numbers of the *changed* file, derived
  mechanically from each hunk header's new-side start. Added and context lines
  carry the line they occupy after the change; removed lines carry `-` because
  they no longer exist; hunk and file headers stay unnumbered.
- The system prompt states that `document_line` is the specific clause, "not the
  document's first line" — the exact failure observed.

The numbering is applied inside the ADR 0003 fences, so the trust boundary is
unchanged: documents remain nonce-fenced and the diff remains labeled untrusted.

Numbers are supplied, not enforced: a cited line is still the model's claim. This
ADR removes the guessing, and deliberately stops short of rejecting a finding
whose line looks wrong (see Alternatives).

# Alternatives considered

- **Validate the cited source line against the diff's touched range, downgrading
  a mismatch to `insufficient-evidence`.** Rejected for now, and the live case is
  why: on the observed run it would have converted a *correct* `drift` finding
  into a non-answer, which is strictly worse for the reviewer than a right
  verdict with a poor pointer. Worth revisiting once numbering has been measured
  and mis-cites are rare enough that a mismatch signals a bad verdict rather than
  bad counting.
- **Instruct harder without changing the input** ("cite the exact clause"). Rejected:
  the prompt already asked for a clause-level citation; the input made it
  unanswerable.
- **Post-process by searching the document for the summary's quoted text.**
  Rejected: brittle (summaries paraphrase), and it would invent a citation the
  model did not make — the opposite of the untrusted-output stance.
- **Ask for a quoted snippet instead of a line number.** Rejected: the JSON
  contract and the report schema are line-based, and snippets cannot be
  validated against the governing set the way a path can.

# Consequences

- Citations become clickable in the sense the reports promise: `path:line`
  reaches the clause and the changed line.
- The prompt and the gutter format join the ADR 0001 compatibility surface;
  changing either is a contract change.
- Requests grow by roughly the gutter width per line (~7 characters). The
  mechanical context bound continues to measure raw evidence (`context_size`),
  so the effective prompt is modestly larger than the bound implies — immaterial
  at the 400 000-character default against a ~128k-token context, and noted here
  so the two are not confused.
- Tests assert the numbering behavior directly (numbering, deletion handling,
  header handling) rather than exact prompt bytes, which the ADR 0003 nonce
  already made non-deterministic.
- **Measured, not assumed.** On the same live case, `source_line` moved from `4`
  (`set -euo pipefail`) to `956` — inside the changed hunk — and `document_line`
  from `1` (the frontmatter opener) to `97`, a real clause. The rerun also
  surfaced an unrelated brittleness it would otherwise have masked: the model
  returned a correct verdict prefixed with one sentence of prose, and the reply
  parser accepted code fences but not preambles, discarding a complete answer.
  Parsing now retries the outermost brace span (an ADR 0001 validation detail,
  not a contract change). Shipping this ADR unmeasured would have traded a
  bad-citation failure for a no-answer failure.

# Rollback / revisit trigger

Revisit if measurement shows citations are still landing off-target after
numbering — which would point at the model or the JSON contract rather than the
input — or if a provider's structured-output mode can carry citations as
validated references instead of free integers. The natural follow-on is the
rejected validation alternative above, once mis-cites are rare. Reverting means
dropping the two numbering helpers and the prompt sentences; nothing persists, so
no data migrates.
