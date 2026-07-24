---
title: Case study — catching the kit's layout stamp_file drift
type: Case study
description: A real shipped bug that took a full manual audit to find, replayed against spec-drift with a live provider, with the result and the limits it exposed.
status: current
date: 2026-07-24
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [case-study, validation, drift, evidence]
---

# Case study — catching the kit's `layout: stamp_file` drift

A validation run against a **real bug that shipped**, not a fixture. It answers
one question — *would spec-drift have caught this?* — and records what it got
right and what it got wrong.

## The bug

[claude-okf-repo-kit](https://github.com/lilabrooks/claude-okf-repo-kit) records
its decisions as ADRs, one of which introduced a `layout:` block letting a repo
relocate its knowledge files.

| Date | Event |
| --- | --- |
| 2026-07-13 | ADR 0018 lands, declaring `layout:` with `stamp_file`; the map header states that **every kit tool follows these paths** |
| → 8 days | `update-existing-repo` keeps stamping `kit_version` into a **hardcoded** `docs/index.md` |
| 2026-07-21 | A full-kit audit — every script line-read — finds it, and kit 0.3.9 fixes it |

The consequence was concrete: a repo with a relocated stamp kept its old stamp,
gained a spurious second `docs/index.md`, and drew a session-start drift note
that never cleared.

Ten commits touched that file during the window. The contradiction sat in the
diff each time.

## Why the mechanical checks stayed quiet

The kit's own staleness check (`okf check-stale`) flags *source changed without
its mapped doc changing*. This drift is invisible to that rule: the ADR added a
new commitment while the implementation sat still, so there was no source change
to flag. Catching it needs a reader that understands what the document
**requires** and compares it against what the code **does** — which is the
problem spec-drift exists for.

## Method

Replaying the original PR would have been an unfair test: the 0.3.8 diff shows
the *read* path (`STAMP_FILE`, already correct) while the buggy *write* path was
pre-existing code outside the diff — and a diff-driven tool cannot judge code it
is never shown. That limitation is real and is stated below rather than designed
around.

So the test used spec-drift's actual contract — *judge the change in front of
you* — by reintroducing the historical bug as a change today:

1. A worktree at the kit's current (fixed) `main`.
2. **Base commit:** add ADR 0018 to the mapping for `scripts/update-existing-repo`
   in `docs/okf-map.yml`. It was not mapped, which is itself a finding (below).
3. **Change under test:** delete the layout-aware stamping branch so the updater
   always writes the hardcoded `docs/index.md` — the pre-0.3.9 behavior — under
   the innocuous message *"Simplify kit_version stamping to the bundle root."*
4. `spec-drift check --base HEAD~1 --provider anthropic --format json`.

Scope was one governed file, so the run cost a single model call.

## Result: caught

```
drift   scripts/update-existing-repo   exit 1
```

> "The diff removes the relocated stamp_file handling, so a target with
> `layout: stamp_file` will no longer stamp its declared file and will instead
> create a `docs/index.md` bundle root, contradicting the spec's requirement to
> stamp that file and only that file (ADR 0018)."

Set that beside what the human audit wrote after line-reading every script:

> "a relocated-stamp repo kept its old stamp, **gained a spurious second-stamp
> `docs/index.md`**…"

The same consequence, independently rediscovered, in one call, from a commit
message that gave nothing away.

## What it got wrong: citation precision

The verdict was right; the evidence pointers were not.

| Cited | What that line actually is | What it should have been |
| --- | --- | --- |
| `installer-scripts.md:1` | `---`, the frontmatter opener | **line 83**, the clause "so every kit tool follows it (ADR 0018)" |
| `update-existing-repo:4` | `set -euo pipefail` | the deleted region, ~line 956 |

Paired citations are the product's headline promise, so a right verdict with
useless pointers is only half delivered. The cause was structural: the request
carried a unified diff and unnumbered document text, so the model had to *count
lines* to produce either number — a known-poor operation. Validation caught
neither, because it checks that a citation exists and that its document is in the
governing set, not that the line means anything.

Fixed under [ADR 0005](../adr/0005-line-anchored-evidence.md): every evidence
line now carries its real line number in a gutter, documents by their own
numbering and diffs by the changed file's, with the prompt stating those numbers
are authoritative.

## Two limits worth stating plainly

- **Diff-driven.** spec-drift judges the change in front of it. It cannot flag
  untouched code when a *document* adds a new claim about it — the shape of the
  original ADR 0018 PR.
- **Map-gated.** It reasons only over documents the map points at. ADR 0018 was
  not mapped to `scripts/update-existing-repo`; without the one-line map entry
  added in step 2, the model never receives the ADR and the drift stays
  invisible. Mapping discipline is a prerequisite, not a detail.

## Takeaway

The tool caught, in one model call, a bug that cost a full manual audit — and the
same run exposed a real defect in its own evidence quality, which became ADR 0005.
Both halves are the point: the value is real, and it is bounded by the map you
give it.
