---
type: ADR
title: Architecture boundaries the model is asked to flag
description: The prompt's decision-required enumeration matches the project's own decision policy, so a queue or worker is flagged rather than read as ungoverned.
tags: [adr, provider-contract, prompt, classification]
timestamp: 2026-07-24T02:51:18Z
status: accepted
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Accepted 2026-07-24. Binds future work; supersede only via a new ADR. Refines
the prompt surface of [ADR 0001](0001-analysis-contract.md), whose rollback
trigger reserves prompt changes for their own ADR. The boundary enumeration now
binds as part of that compatibility surface, and the coupling named in
Consequences is a standing obligation: this list and the decision policy in
`AGENTS.md` are meant to agree, and only a narrowing is caught mechanically.

# Context

`decision-required` exists for a change that crosses an architecture boundary
with no decision record behind it. What counted as a boundary was enumerated in
the prompt as *dependency, persistence, auth, public API, deployment* — narrower
than the list this project applies to itself. `AGENTS.md`, and the
`okf adr-suggest` helper, both name **cache/queue/worker** among decision-shaped
changes. The prompt did not.

Building the payments worked example
([docs/case-studies/payments-idempotency.md](../case-studies/payments-idempotency.md))
turned that discrepancy into measured evidence. A change adding a background
retry queue — the textbook decision-shaped change — was classified live as
`insufficient-evidence` on one run and `clean` on the next. Neither verdict was
unreasonable given what the model was told: the governing documents covered key
handling, the worker did not touch key handling, and a queue was not on the list
of things to treat as a boundary. The tool was asking for a judgment while
withholding the criterion.

# Decision

The prompt enumerates architecture boundaries to match this project's own
decision policy: a runtime dependency, persistence, a **cache/queue/worker or
other change of execution topology**, auth/security/privacy, a public API or
output contract, deployment, or an ownership boundary.

The enumeration stays a closed list rather than an open invitation, so the
classification keeps a checkable meaning — but it is now the *same* closed list
the repository already uses when deciding whether a change needs an ADR. A test
asserts the boundary terms are present, so the list cannot narrow silently.

# Alternatives considered

- **Leave the narrow list.** Rejected on evidence: it omitted the most common
  decision-shaped change, and a reviewer reading `clean` on a new queue would
  reasonably conclude the tool had considered and cleared it.
- **Drop the enumeration and ask for "any architecture boundary".** Rejected:
  that term is exactly what a model resolves inconsistently, and the observed
  failure was already a consistency failure — two runs, two answers. A concrete
  list is what makes the classification reproducible.
- **Make the list configurable per repository.** Rejected as premature: no
  adopter has asked, a per-repo list is one more thing to drift from the repo's
  real policy, and a repo wanting different boundaries can say so in the
  governing documents the model already reads.
- **Infer boundaries from the governing documents alone.** Rejected: it makes
  `decision-required` unreachable in the case that matters most — a boundary no
  document mentions yet, which is precisely when the decision record is missing.

# Consequences

- A queue, worker, or scheduler introduced without an ADR is now classified
  `decision-required` rather than read as ungoverned. Measured on the payments
  example: `insufficient-evidence`/`clean` before, `decision-required` after,
  citing the changed line and the clause requiring the record.
- **The prompt list and the project's decision policy must stay in step.** They
  live in different files and nothing mechanically joins them. The guard test
  pins the boundary terms so a narrowing is caught, but a future *widening* of
  the policy still has to be carried across by hand — named here because this
  ADR exists because of exactly that drift.
- `decision-required` will fire more often. That is the intent, but it raises the
  cost of a false one; the revisit trigger below watches for it.
- The prompt remains part of the ADR 0001 compatibility surface.

# Rollback / revisit trigger

Revisit if `decision-required` proves noisy in practice — runs flagging routine
changes as boundary crossings, or adopters routinely dismissing it — which would
argue for tightening the list or demanding stronger evidence before the
classification is allowed. Also revisit if this project's own decision policy
changes, since the two lists are meant to agree. Reverting means restoring the
narrower enumeration; nothing persists, so no data migrates.
