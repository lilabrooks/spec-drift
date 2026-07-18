---
title: Component specifications index
type: index
status: current
date: 2026-07-14
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [specs, index]
---

# Component Specifications

Each component that makes promises to users or to other components gets a spec
here.

| Spec | Description |
| --- | --- |
| [analysis-inputs.md](analysis-inputs.md) | Repository discovery, Git diff loading, unsafe-path filtering, and governing-document resolution into a `ChangeSet` |
| [drift-analysis.md](drift-analysis.md) | Judging governed changes against their documents into validated findings and an exit-code-bearing `AnalysisReport` |
| [report.md](report.md) | Terminal/Markdown/JSON rendering, the committed JSON report schema, and the `check` command's exit-code contract |
| [ci-integration.md](ci-integration.md) | Exit-code gating, the deterministic replay provider, and the `make ci-fixture` demonstration |
