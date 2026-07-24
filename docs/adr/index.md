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
- [0003 Prompt-injection threat model and unforgeable document delimiters](0003-prompt-injection-threat-model.md): the diff is untrusted, so a per-request secret nonce fences trusted documents from it and a forged citation is still rejected — **accepted**.
- [0004 Secret scanning in the quality gate](0004-secret-scanning.md): a dependency-free repo-local scanner blocks committed keys/tokens in the gate and CI, chosen over gitleaks/detect-secrets to keep the zero-dependency stance, with GitHub push protection as the backstop — **accepted**.
- [0005 Line-anchored evidence in model context](0005-line-anchored-evidence.md): documents and diffs carry their real line numbers in a gutter, so a citation names the governing clause and the changed line instead of a counted guess — **proposed**.
