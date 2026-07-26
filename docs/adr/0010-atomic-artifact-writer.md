---
type: ADR
title: Descriptor-anchored atomic artifact writer
description: Publish every generated artifact through one writer that resolves each path component without following symlinks, stages to a restrictive same-directory temporary file, and publishes atomically, failing closed where the primitives are unavailable.
tags: [adr, security, output, filesystem, platform]
generated: { by: "process:claude-code", at: 2026-07-26T03:13:14Z }
status: accepted
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Accepted 2026-07-26 by the owner. Binds `S1`'s writer work: every generated
artifact publishes through this one writer, and no component may write a
generated file by another route. Implementation remains pending until the
integration roadmap's contract and fixture packages freeze, so `SD-P0-4` stays
open.

# Context

`resolve_target_path` validates a destination — rejecting empty, absolute, and
`..` paths, then confirming the resolved path stays under the chosen root — and
`write_generated_files` writes it later with `Path.write_text`. Three defects
follow from the gap between those two steps.

**The check and the open are separate.** Validation resolves the path; the
write reopens it by name. A path component swapped for a symlink between the
two is followed on the second lookup, so the write lands wherever the attacker
pointed it. Resolution is not a guarantee that survives to the write.

**The write is not atomic.** `write_text` truncates and writes in place. An
interrupted or failing write leaves a truncated file at the destination, and a
consumer cannot distinguish it from a complete one. A retry does not fix it,
because the damage is already published under the final name.

**The no-clobber check is racy.** `target.exists()` runs before the write, so a
file created in between is overwritten despite `--force` being absent. The
check expresses the right intent and cannot enforce it.

The destination is not always owner-supplied. `GeneratedFile` carries paths
from model output, so the path is untrusted input in the tool's core use case.
The same writer is intended to carry execution plans as well as reports, so the
weakness applies to every artifact the tool publishes.

Appendix B answer 6 fixed the operating boundary: macOS and Linux on local
filesystems are the first supported production surface, validation completes
before any write, writes are no-clobber and atomic, and platforms lacking the
required primitives fail closed rather than degrading. Those constraints are
recorded in `docs/GOAL.md`; this ADR decides the mechanism that satisfies them.

# Decision

Publish every generated artifact — reports, plans, and anything added later —
through one writer with the following properties.

**Resolve by descriptor, not by name.** Walk the destination one component at a
time from an opened root directory descriptor, opening each component with
`O_NOFOLLOW` and `dir_fd`, so no lookup follows a symlink and no component can
be substituted between validation and use. The final open is anchored to the
descriptor of the directory that was verified, not to a path string. The
existing string-level rejection of empty, absolute, and `..` paths stays as a
cheap pre-filter; it is no longer the security boundary.

**Stage, then publish.** Create a temporary file in the destination directory
with `O_CREAT | O_EXCL` and mode `0600`, write the content, `fsync` the file,
then publish:

- Default, no-clobber: link the temporary name to the final name. The operation
  fails if the final name already exists, so absence is proven by the publish
  itself rather than by an earlier check. Unlink the temporary name afterward.
- Forced replacement: rename the temporary name onto the final name. This is a
  separate, explicitly requested path and never the default.

`fsync` the containing directory after publishing so the link or rename is
durable. On any failure, unlink the temporary file and leave the destination
untouched.

**Fail closed.** Probe for `dir_fd` support and `O_NOFOLLOW` at runtime. Where
either is unavailable — Windows today — refuse to write and return a structured
error naming the unsupported platform. Do not fall back to a name-based write.
An unsupported platform gets no artifact, not a less safe one.

**One writer.** No component writes a generated file by another route. A second
write path would reintroduce the defect this decision removes.

# Alternatives considered

- **Keep `write_text` and re-validate immediately before it.** Rejected: it
  narrows the race window without closing it. Any name-based check followed by
  a name-based open is the same defect with a shorter fuse.
- **Stage to a temporary file and rename unconditionally.** Rejected: rename
  always replaces, so it cannot express the no-clobber default the goal
  requires. Link-then-unlink gives atomic create-if-absent; rename is kept for
  the forced path only.
- **Use `tempfile.NamedTemporaryFile` in the system temporary directory, then
  move.** Rejected: a cross-filesystem move is a copy plus delete, which is not
  atomic, and the staged file would sit outside the destination's ownership and
  permissions.
- **`O_EXCL` directly at the final name, with no temporary file.** Rejected: it
  gives atomic creation but not atomic content. An interrupted write leaves a
  truncated file under the final name.
- **Support every platform with a best-effort fallback.** Rejected by Appendix
  B answer 6. A fallback that silently drops the symlink and atomicity
  guarantees is worse than a refusal, because the caller cannot tell which
  guarantees applied to a given artifact.
- **Rely on the operating system's default temporary-file permissions.**
  Rejected: the default depends on the process umask, and the staged file may
  hold an unpublished report, so the mode is set explicitly.

# Consequences

- Closes `SD-P0-4`. The symlink-swap race, the non-atomic write, and the racy
  no-clobber check disappear together, because publishing becomes one operation
  whose success is the proof.
- Windows becomes an explicitly unsupported production platform for artifact
  output, with a named error rather than a silent degradation.
- Report output gains a durability guarantee it did not have: a published
  report is complete, or it does not exist.
- `docs/specs/report.md` must be updated at implementation time with the
  publish semantics, the forced-replacement path, and the platform refusal.
  `src/spec_drift/core/**` currently maps only to
  `docs/specs/drift-analysis.md`, so the map needs a mapping to the writer's
  own governing spec.
- Requires fixtures for symlink swap on a parent component, symlink swap on the
  final component, no-clobber collision, forced replacement, interruption
  leaving no partial artifact, and refusal on a simulated unsupported platform.
- Adds no runtime dependency. Every primitive is in the standard library.
- Slightly slower per artifact, from two `fsync` calls. Irrelevant at the
  number of artifacts one run produces.

# Rollback / revisit trigger

Revisit if a supported platform turns out to have a destination filesystem that
cannot honor `O_NOFOLLOW` or hard links — some network filesystems — in which
case the refusal set widens or a separate decision covers that transport.
Revisit also if artifact output moves to a stream or object store, where these
filesystem primitives do not apply and a different integrity proof is needed.
Rollback is not a return to `write_text`; that reopens `SD-P0-4` and therefore
requires a replacement containment decision in the same change.
