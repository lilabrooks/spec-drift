---
title: Architecture decision records index
type: index
status: current
date: 2026-07-14
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [adr, index]
---

# Architecture Decision Records

Decision-shaped changes — dependency, persistence, auth, API contract,
deployment, ownership boundary — get an ADR here, listed in this index with its
status. Accepted ADRs bind future work until the owner supersedes them.
- [0001 Drift-analysis finding schema and model contract](0001-analysis-contract.md): closed finding classification with paired citations, and a validated JSON model contract that never trusts the model to self-classify unmapped — **accepted**.
- [0002 CI integration via exit-code gating and a deterministic replay provider](0002-ci-integration.md): CI gates on the check exit code, and a shipped offline replay provider makes the integration testable without a vendor key — **accepted**.
