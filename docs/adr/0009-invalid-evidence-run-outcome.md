---
type: ADR
title: Invalid model evidence is a structured run outcome
description: Treat mechanically invalid model evidence as a failed analysis unit and exit 2, while preserving a valid partial report and never accepting a fabricated finding.
tags: [adr, evidence, report, validation, ci]
generated: { by: "process:codex", at: "2026-07-25T23:41:09Z" }
status: accepted
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Accepted 2026-07-25 at the owner's direction. For schema v2 this ADR supersedes
ADR 0001's conversion of mechanically invalid model output into an
`insufficient-evidence` finding and ADR 0002's rule that exit-2 outcomes are
never serialized. Their remaining decisions stay accepted. Implementation
remains pending.

# Context

The current parser converts malformed JSON, disallowed classifications,
out-of-set document paths, missing citations, and other unverifiable model
output into `insufficient-evidence`. That keeps untrusted output from becoming
a clean or actionable verdict, but it still fabricates a finding from a failed
provider response.

Schema v2 adds mechanical validation for source side, path, line or range, diff
hunk membership, document bounds, and content digests. A failure in those
checks means the analysis unit did not produce a trustworthy observation. It is
different from valid evidence showing that the governing material is genuinely
missing, ambiguous, too large, or contradictory.

# Decision

When model-produced evidence fails mechanical validation:

- Emit no finding or observation for that unit.
- Record a structured run outcome with unit state `failed` and reason code
  `invalid-evidence`.
- Return process exit 2 because trustworthy analysis did not complete.
- Preserve findings and outcomes from units that completed before the failure.
- Produce a schema-valid report containing the completed units and the
  structured failure. The report carries an explicit partial or failed run
  state and no rejected citation values.
- Keep raw provider output out of public reports and pull-request artifacts. It
  may enter a private diagnostic artifact only when the approved retention
  policy permits it.

If the report itself fails runtime schema validation, publish no report file.
The descriptor-anchored writer discards its temporary output, prints a
sanitized error, and returns exit 2.

Advisory CI reports an incomplete tool or provider outcome and never a semantic
pass. Required CI fails closed. Calibration and release fixtures treat any
unexpected invalid-evidence outcome as a failed gate.

`insufficient-evidence` remains a valid finding only when trusted, mechanically
valid inputs establish that the change cannot be judged, such as missing
governing material, bounded context refusal, or contradictory binding
documents. It is not a repair label for malformed model output.

# Consequences

- Exit 1 continues to mean that a valid observation requires human review.
- Exit 2 means analysis could not produce a trustworthy conclusion, including
  invalid provider evidence.
- Partial runs remain auditable without accepting the failed unit as a finding.
- The report schema must serialize structured exit-2 and per-unit failure
  outcomes.
- The feedback system uses the run-outcome subject variant, so no observation
  ID or recurrence fingerprint is invented for rejected evidence.

# Alternatives considered

- **Convert invalid evidence to `insufficient-evidence`.** Rejected for schema
  v2 because it erases the boundary between a valid ambiguity finding and a
  failed provider response.
- **Drop the whole report.** Rejected because valid completed units and usage
  records are needed for audit and partial-run recovery.
- **Keep exit 1.** Rejected because exit 1 denotes a valid review finding;
  mechanical rejection prevented analysis.
- **Publish the invalid citation for debugging.** Rejected because downstream
  consumers may treat a serialized citation as accepted evidence.

# Rollback / revisit trigger

Revisit if providers produce invalid evidence often enough that a separately
named provider-quality outcome is operationally useful, or if partial reports
cannot be consumed safely. Any replacement must preserve the rule that rejected
evidence never becomes an accepted finding or semantic pass.
