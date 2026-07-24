---
type: ADR
title: Contradictory governing documents are reported, not resolved
description: When a change's governing documents disagree with each other the finding is insufficient-evidence naming the conflict, because ranking document types would be silently picking a side.
tags: [adr, provider-contract, prompt, classification, governance]
timestamp: 2026-07-24T03:10:08Z
status: proposed
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Proposed (authored per the decision policy; awaiting owner review). Refines the
prompt surface of [ADR 0001](0001-analysis-contract.md), whose rollback trigger
reserves prompt changes for their own ADR.

# Context

`docs/GOAL.md` gives accepted ADRs "precedence over implementation when they
disagree", and the prompt says the same. That rule is about a *document versus
code*. It says nothing about two governing documents disagreeing with **each
other**, and the question is not hypothetical: a change can be governed by both
a spec and an accepted ADR, and a pull request can edit the spec while the ADR
still says something else.

Designing a worked example around that case forced the question. The obvious
answer — extend the precedence so an accepted ADR outranks a spec — is wrong for
this repository, for two reasons.

First, it contradicts the grounding rule the project runs on: *"When code and
docs disagree, flag the mismatch. Don't silently pick a side."* A standing
precedence between document types is precisely picking a side, applied
automatically and invisibly.

Second, the two document kinds are not rival authorities over one question. The
spec index describes specs as *how the shipped code behaves*; ADRs record *why
the codebase is shaped this way*. An accepted ADR that contradicts a current
spec does not mean one of them wins — it means the documentation set is broken,
almost always because the spec was not updated when the ADR landed, which the
task workflow already requires. The standing conflict is itself the defect, and
the repair is a human one: reconcile the spec, or supersede the ADR.

A tool cannot make that call. It cannot tell a legitimate spec update from one
written to permit the very change under review — the document-level form of the
self-approval problem [ADR 0003](0003-prompt-injection-threat-model.md) guards
against in diffs.

# Decision

When a change's governing documents state different requirements for the same
thing, the finding is **`insufficient-evidence`**, and the summary names which
documents disagree and on what.

This needs no new classification: the existing meaning — *the governing
documents do not let you judge the change* — is literally true when they
contradict each other. The finding is actionable (exit code 1), so CI stops the
change and a person reconciles the documents.

The existing precedence is unchanged and stays scoped to what it always said: an
accepted ADR overrides the **implementation**. It is never applied to resolve a
conflict between documents.

# Alternatives considered

- **Rank ADRs above specs.** Rejected: it silently picks a side, against the
  project's own grounding rule; it lets a stale ADR quietly overrule a
  legitimately updated spec; and it hides the actual defect, which is that the
  documents disagree at all.
- **Rank whichever document the pull request did *not* edit.** Tempting, since
  accepting an ADR is reserved to the owner while editing a spec is not, so the
  untouched document carries more authority. Rejected: it encodes a provenance
  guess into a per-file judgment that cannot see the whole change set, and it
  would still resolve silently — the reviewer would never learn the documents
  conflict.
- **A new `conflicting-documents` classification.** Rejected as disproportionate:
  it reopens the closed enum of ADR 0001, the report schema, every renderer, and
  the exit-code table, to express something `insufficient-evidence` already says
  correctly. Revisit if conflicts turn out to be common enough that reviewers
  need to filter them apart from genuine evidence gaps.
- **Say nothing and let the model decide.** Rejected: that is the status quo, and
  it produces an arbitrary, unreproducible answer to a question the project has
  never defined — the worst of both, since the reviewer cannot tell a judgment
  from a coin flip.

# Consequences

- A pull request that edits a spec to permit a change an accepted ADR forbids is
  stopped, and the reviewer is told the documents disagree rather than being
  handed a verdict that depends on which document the model weighted.
- `insufficient-evidence` now covers two distinct situations: evidence that is
  missing, and evidence that is self-contradictory. The summary distinguishes
  them; the classification does not. That is the cost of not widening the enum,
  and the revisit trigger watches it.
- The prompt gains the rule and joins the ADR 0001 compatibility surface.
- The repository-side obligation is the human half of this decision and belongs
  in the playbook, not in the tool: an ADR that contradicts a spec is reconciled
  in the same change or rejected.
- **Measured live** on `build_conflicting_docs_fixture`, where a change widens a
  signed-link window to 24 hours and edits the spec to allow it while the
  accepted ADR still says 15 minutes. The run returned `insufficient-evidence`
  and named both sides with exact line numbers — the spec's 24-hour line and the
  ADR's 15-minute line — concluding the change "cannot be judged until they are
  reconciled", with the source citation on the changed constant. Exit code 1.
- **A conflict is described in the summary but under-represented in the
  citations.** The finding schema carries one `document` citation, so a finding
  about two documents disagreeing cannot point at both; the observed run named
  both in prose and left the structured field empty, which the contract permits
  for `insufficient-evidence`. Recorded rather than fixed: widening the citation
  shape is an ADR 0001 change, and it is only worth making if conflict findings
  become common enough that the prose is not enough for a reviewer.

# Rollback / revisit trigger

Revisit if reviewers report that conflict findings are hard to distinguish from
ordinary insufficient-evidence findings in practice — the argument for the
rejected `conflicting-documents` classification — or if real repositories turn
out to carry long-lived intentional spec/ADR tension that this rule would flag
on every unrelated change. Reverting means dropping the prompt rule; nothing
persists, so no data migrates.
