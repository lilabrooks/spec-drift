---
okf_version: "0.2"
kit_version: "0.3.14"
title: Documentation index
type: index
status: current
date: 2026-07-14
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [documentation, index]
---

# Documentation

Bundle root for this repository's knowledge. Changes to this bundle are
recorded in [log.md](log.md), newest first.

| Location | Contents |
| --- | --- |
| [specs/](specs/index.md) | Component specifications: how the shipped code behaves |
| [adr/](adr/index.md) | Architecture decision records: why the codebase is shaped this way |

This bundle contains the project goal, component specifications, accepted
architecture decisions, the source-to-document map, and the documentation log.
It follows Open Knowledge Format 0.2 and uses the
[claude-okf-repo-kit](https://github.com/lilabrooks/claude-okf-repo-kit)
workflow to keep that knowledge connected to the code.

## The `status:` field in this bundle

`status:` here carries **workflow state, not OKF 0.2 §5.4's lifecycle
vocabulary** (`draft` / `stable` / `deprecated`). ADRs use `proposed` and
`accepted` — the values `bash scripts/okf pending` and the SessionStart hook
both read — and the index, log, and spec files use `current`.

This divergence is deliberate. It does not affect conformance: §11 requires
only parseable frontmatter, a non-empty `type`, and reserved filenames matching
§8 and §9, and `status` is in none of them. It is declared here because §5.4
defines its vocabulary without saying how to treat a value outside it, so a
consumer filtering on lifecycle should not read `accepted` as "not stable".

Should this bundle ever need machine-readable lifecycle as well, the
non-breaking route is a separate key — an additive key is what §4.1 protects —
rather than renaming these values and breaking the tooling that reads them.
