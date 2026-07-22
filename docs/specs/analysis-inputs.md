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
  regardless of ignore rules), `credential` (a well-known secret-bearing name —
  a private key, keystore, `.netrc`, `.pgpass`, `.htpasswd`, or a `.pem`/`.key`/
  `.p12`/`.pfx`/`.keystore`/`.jks`/`.ppk` suffix — matched by name so a
  committed secret is excluded regardless of ignore rules), `outside-root`
  (absolute or `..`-escaping path), `ignored` (matches a `.gitignore` pattern,
  even if tracked), `binary` (git reports the file as binary). The env-file and
  credential reasons therefore win over ignored for a secret that is also
  gitignored. The `ignored` and `binary` sets are each computed in one batched
  git call (`check-ignore --stdin`, `diff --numstat`) rather than one process
  per file.
- **Resolution.** Reads `docs/okf-map.yml` (the claude-okf-repo-kit convention),
  rejecting a malformed map with `MappingError` (CLI exit code 2) rather than
  silently treating it as "no mappings". Each retained change resolves to its
  governing documents by matching the change path against each mapping's source
  glob (`*` within a path segment, `**` across segments); for a rename, **both**
  the new path and the `old_path` are resolved and their documents unioned, so a
  file renamed out of a governed area is still governed. Documents from multiple
  matching mappings are unioned in first-seen order. A change matching no mapping
  has no governing documents and is reported as **unmapped**, never assigned an
  invented contract.

### Per-file diff

For consumers that need the change text itself (drift analysis), the layer also
exposes the unified diff of a single path between the base and HEAD, read-only.
A rename passes both the old and new path so the diff shows the rename delta
rather than a wholesale add. A nonzero git exit yields an empty diff, which the
caller treats as insufficient evidence rather than a change it can judge. This
is the one input a governed change carries beyond its path and status.

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
