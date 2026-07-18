---
name: okf-kit-upgrade
description: Walk through a kit upgrade when the SessionStart hook reports kit_version drift — safe updater, candidate review, mirror re-sync, post-update verification. Use when the drift note appears or the owner asks to upgrade the installed kit.
---

# Kit upgrade

When the SessionStart hook notes that this repo's stamped `kit_version` is older than the published kit `VERSION`:

1. **Tell the owner and recommend the safe updater.** Never edit kit-managed files toward the new version by hand — the updater carries the provenance machinery.

```bash
cd /path/to/claude-okf-repo-kit && git pull
bash scripts/update-existing-repo /path/to/this-repo
```

2. **Know what the updater will and won't touch.** Kit-managed scripts (`scripts/okf`, the two hooks, the `okf-*` skills) are refreshed in place — after a backup under `.okf-kit-backups/<timestamp>/` — only when a digest manifest proves the current content is unedited kit output. Anything this repo edited is preserved, with the new kit version written beside it as a same-folder numbered candidate (such as `check-docs-sync.2.sh`) under "Needs review". Changed templates (`CLAUDE.md`, `docs/GOAL.md`, indexes, the map) always arrive as numbered candidates; the updater refreshes its own untouched candidates in place across releases instead of numbering past them.

3. **Review the candidates with the owner.** For each "Needs review" item: diff it against the live file, merge what belongs (local hardening usually stays; kit improvements usually come in), then delete the candidate. Candidate review is the owner's decision — never adopt or discard silently.

4. **Re-sync second-agent mirrors.** If this repo mirrors the hooks into another agent's config (`.codex/hooks/`, for example), the updater does not know about them — after adopting hook changes, copy the `.claude/hooks/` versions over the mirrors and keep them byte-identical. Because this sync is manual and silent to forget, a repo that maintains mirrors should guard the invariant mechanically instead of by discipline: add a check to the repo's own test or validation gate that the mirrored hooks stay byte-identical and that any mirrored skill set stays paired — skipped when the second stack is absent, since it is optional. The check lives in the target's gate, not the kit, so it fits whatever framework the repo already runs (spec-agent-cli added exactly this once Codex config landed beside the Claude stack).

5. **Verify.** Run the target checks — `python3 -m json.tool .claude/settings.json`, `bash -n` on the kit scripts, `bash scripts/okf check-stale`, and this repo's own test command — and confirm the stamp file (`docs/index.md` by default; `layout: stamp_file` in `docs/okf-map.yml` may relocate it) now stamps the new `kit_version`. Log the upgrade in `docs/log.md` (what refreshed, what was preserved for review, what was merged).
