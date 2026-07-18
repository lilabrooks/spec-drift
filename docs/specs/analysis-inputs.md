---
title: Analysis inputs
type: Spec
status: current
date: 2026-07-18
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [inputs, git, diff, mapping, filtering]
---

# Analysis inputs

The input layer turns a repository and a base reference into the set of changes
drift analysis will judge, together with the documents that govern each change.
It is read-only and makes no model call. `spec_drift.inputs.collect_changes` is
the single entry point; it returns an immutable `ChangeSet`.

## Contract

`collect_changes(start, base)`:

- **Discovery.** Resolves the repository root from `start` (any directory
  inside the repository). A directory outside any repository raises
  `RepositoryError`.
- **Base validation.** A `base` that does not resolve to a commit raises
  `InvalidBaseError`. Both errors map to CLI exit code 2.
- **Diff loading.** Reads `base..HEAD` with rename detection. Each change
  carries a repository-relative `path` and a `status` of `added`, `modified`,
  `deleted`, or `renamed`; a rename also carries its `old_path`. The working
  tree is never modified.
- **Filtering.** Removes paths that must never reach a model, recording each
  with a reason, in this priority order: `env-file` (a `.env`/`.env.*` name,
  regardless of ignore rules), `outside-root` (absolute or `..`-escaping path),
  `ignored` (matches a `.gitignore` pattern, even if tracked), `binary` (the
  HEAD blob contains a NUL byte). The env-file reason therefore wins over
  ignored for a `.env` that is also gitignored.
- **Resolution.** Reads `docs/okf-map.yml` (the claude-okf-repo-kit convention)
  and resolves each retained change to its governing documents by matching the
  change path against each mapping's source glob (`*` within a path segment,
  `**` across segments). Documents from multiple matching mappings are unioned
  in first-seen order. A change matching no mapping has no governing documents
  and is reported as **unmapped**, never assigned an invented contract.

### Per-file diff

For consumers that need the change text itself (drift analysis), the layer also
exposes the unified diff of a single path between the base and HEAD, read-only.
This is the one input a governed change carries beyond its path and status.

## Guarantees

- A `ChangeSet` partitions its retained changes into `governed` (at least one
  governing document) and `unmapped` (none); excluded paths appear only in
  `excluded`, never in `included`.
- No new runtime dependency: Git is read through the `git` command line and
  `okf-map.yml` through a purpose-built parser for the `mappings:` subset.

## Boundaries

- Does not read or interpret document *content*, classify drift, or decide exit
  codes — those belong to later analysis and reporting components.
- Interprets only the `mappings:` block of `okf-map.yml`; the optional
  `layout:` block is not yet consulted.
