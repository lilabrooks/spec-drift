---
type: ADR
title: Base-controlled governance and HEAD proposals
description: Read binding governance from an explicit trusted Git commit and report HEAD-side governance changes separately so a change cannot authorize itself.
tags: [adr, security, governance, git, mapping]
generated: { by: "process:codex", at: "2026-07-25T23:41:09Z" }
status: accepted
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Accepted 2026-07-25 at the owner's direction. This decision binds the trusted
input, planning, and report work in the Spec Drift integration roadmap.
Implementation remains pending.

# Context

Spec Drift currently diffs source from a requested base to `HEAD`, then reads
the map and governing documents from the working tree. A pull request can
therefore edit the authority used to judge its own code. Uncommitted governance
can also change the result of an analysis whose source inputs are committed.

The prompt-injection boundary in ADR 0003 protects document delimiters. It does
not decide which revision of a document is authoritative. That choice must be
made before provider construction through Git provenance and deterministic
policy.

# Decision

Committed analysis resolves an explicit protected base ref and records the
requested ref, resolved base, merge base, `HEAD`, and trusted governance commit.
For a pull-request comparison, the trusted governance commit is the merge base
of the protected base ref and the analyzed `HEAD`. A different protected
baseline requires an explicit owner-approved policy value.

The map, policy, document statuses, and binding governing documents are read
only as regular Git blobs from that commit. A missing object, wrong object
type, unsafe path, or unreadable blob is a structured input failure before
provider construction.

Changes between the governance commit and `HEAD` to any map, specification,
ADR, exclusion, workflow policy, coverage policy, or provider policy are
reported separately as governance proposals. Dirty or untracked governance is
also reported as an uncommitted proposal. Proposal content never enters the
binding provider context, changes coverage, relaxes policy, or authorizes code
in the same change.

Code mapped at the governance commit is judged against that commit's map and
binding documents. A new module with no base mapping makes no provider call and
is reported as `unmapped-at-base`, together with any related governance
proposal. It cannot receive `no-drift-observed`.

A governance proposal becomes authority only after it lands as its own
owner-reviewed change and appears in the trusted baseline of a later run.
Provider-free planning may describe dirty proposals. Live execution requires a
clean worktree and the exact committed `HEAD` bound into the approved plan.

# Consequences

- A pull request cannot weaken its own specification, map, exclusions, or
  provider policy and receive approval under the weakened text.
- Existing code changes can still be analyzed while a proposal is present,
  because their provider context comes from the trusted commit.
- New code whose only mapping appears in the same change remains unjudged until
  that governance lands separately.
- Local uncommitted exploration stays possible through provider-free planning,
  while live work remains reproducible from committed inputs.
- The plan and report schemas need distinct governance-proposal and
  `unmapped-at-base` records plus full Git provenance.

# Alternatives considered

- **Read governance from `HEAD`.** Rejected because the change could set its own
  authority.
- **Read governance from the working tree.** Rejected because uncommitted files
  would make a committed analysis irreproducible.
- **Ignore HEAD governance changes.** Rejected because reviewers need to see
  proposed authority changes even though those changes do not bind the run.
- **Let a same-change mapping govern a new module.** Rejected because it is the
  map-level form of self-authorization.

# Rollback / revisit trigger

Revisit if a protected merge-queue commit needs a different trusted-ref rule,
or if a governance-only workflow can prove equivalent authority without Git
objects. Rollback requires another owner-approved trust ADR; returning to
working-tree authority is not a safe compatibility mode.
