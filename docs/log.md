---
title: Documentation log
type: log
status: current
date: 2026-07-17
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [documentation, log]
---

# Documentation log

Dated changes to the docs bundle, newest first.

## 2026-07-22: README and repository metadata refreshed

- Reworked the README around a real-provider path, a minimal mapping example,
  an exact fixture finding, classification semantics, provider data handling,
  and contributor/support links. Added a compact contents list, moved normal
  usage ahead of the verified fixture demo, added source-install instructions,
  and folded secondary demo cases into a disclosure. Fixed the documentation
  index's stale empty-bundle wording. Updated the GitHub About description and
  topic set to match the current CLI and OKF support.

## 2026-07-22 — license changed to proprietary

- Replaced the MIT license with an All Rights Reserved copyright notice modeled
  after `lilabrooks/claude-okf-repo-kit`; updated README and package metadata to
  stop advertising MIT.

## 2026-07-22 — live-provider acceptance run passed (goal met)

- Ran the owner-gated live-provider success criterion (review finding 9) with a
  real Anthropic provider, key supplied from a git-ignored `.env` and never
  entering context. Against the drift fixture, `spec-drift check --base base
  --provider anthropic` returned exit 1 and classified `src/refunds.py` as
  `drift`, citing source `src/refunds.py:5` and document
  `docs/specs/refunds.md:8` with an accurate summary; the clean fixture returned
  exit 0 / `clean`. This proves the live provider path, not just the
  deterministic replay/scripted path the test suite exercises. Temp fixtures
  were removed after the run. Updated the Master-objective "Current state" in
  `AGENTS.md` to record that every `docs/GOAL.md` success criterion now passes.

## 2026-07-22 — accept ADR 0004

- **Accepted [ADR 0004](adr/0004-secret-scanning.md)** at the owner's direction
  (status proposed → accepted; frontmatter, Status section, index). The chosen
  layering: the dependency-free repo-local scanner is the offline in-gate first
  line, and GitHub secret scanning + push protection (free for this public repo,
  and history-aware) is the complementary backstop the owner enables in the
  repository's Code-security settings; gitleaks stays the documented revisit
  target, not adopted now. Added a `CONTRIBUTING.md` "Secrets" section with an
  opt-in local pre-commit hook that runs `scripts/check-secrets.py`.

## 2026-07-22 — accept ADR 0003; add secret scanning (proposed ADR 0004)

- **Accepted [ADR 0003](adr/0003-prompt-injection-threat-model.md)** at the
  owner's direction: status flipped proposed → accepted (frontmatter, Status
  section, index label). No reversal — the code already implements it. It now
  binds future work.
- **Secret scanning added** in response to "ensure API keys are not hardcoded".
  A manual scan first confirmed the tree is clean (keys come only from the
  environment via the provider SDKs; `.env` is git-ignored; `.env.example` holds
  placeholders). New **proposed [ADR 0004](adr/0004-secret-scanning.md)** chooses
  a dependency-free repo-local scanner (`scripts/check-secrets.py`, stdlib) over
  gitleaks/detect-secrets to preserve the zero-dependency stance, and documents
  the coverage tradeoff and revisit trigger. The scanner is wired into the
  `make check`/`check-all` gate (`secrets` target), runs as a standalone
  `secret-scan` GitHub Actions workflow, and is mapped to ADR 0004 in
  `docs/okf-map.yml`. Tests: `tests/test_check_secrets.py`. The fake private-key
  body in `tests/repo_fixtures.py` (used to test credential exclusion) is marked
  `# pragma: allowlist secret`. ADR 0004 awaits owner review
  (`bash scripts/okf pending`).

## 2026-07-22 — robustness & failure-path hardening

Implemented an external review's 15 findings (Fable5 session) as one hardening
pass on the `failure-path-hardening` branch. `make check` green (ruff, format,
mypy strict, 153 tests, 96% coverage, okf-docs); `bash scripts/okf check-stale`
current. The owner-gated live-provider run (finding 9) remains unrun.

- **New proposed [ADR 0003](adr/0003-prompt-injection-threat-model.md)** — the
  diff is untrusted, so the request now places trusted documents before the diff
  and fences both with a per-request secret nonce; refines the prompt surface of
  ADR 0001. Awaiting owner review (`bash scripts/okf pending`).
- **Contract-restoring fixes for two already-promised success criteria:**
  provider failures now raise `ProviderError` and map to exit 2 with an
  actionable message (no traceback); a malformed `docs/okf-map.yml` now raises
  `MappingError` → exit 2 instead of silently parsing to "no mappings" and
  greenlighting CI.
- **Spec updates:** `analysis-inputs.md` (credential exclusion reason, batched
  `check-ignore`/`numstat` git calls, rename diff + old-path governance union,
  malformed-map rejection); `drift-analysis.md` (mechanical context bound and
  empty-diff guard → `insufficient-evidence`, provider-error propagation,
  `excluded` carried on the report, ADR 0003 reference); `report.md` (exit-2
  causes now name `MappingError`/`ProviderError`; reports surface `excluded`).
  `schemas/report.schema.json` gained a required `excluded` array.
- **Behavior added:** mechanical context bound (`SPEC_DRIFT_MAX_CONTEXT_CHARS`,
  default 400 000); empty/failed per-file diff → insufficient-evidence; credential
  file exclusion; rename diffs show the rename and resolve governance from both
  ends; `--model` flag; echo-provider warning; excluded paths surfaced in all
  three report formats; batched git calls; anchored replay matching.
- **Template residue pruned:** removed the `hello`/`ask` commands, the `agents`
  package, `build_agent`, and the unused `parse_generated_files`; fixed the
  `pyproject` description; refreshed `.env.example` (dropped the removed
  `SPEC_DRIFT_SYSTEM_PROMPT`, added `SPEC_DRIFT_MAX_CONTEXT_CHARS`). Extended
  `docs/okf-map.yml` to govern the CLI, providers, config, core, and runtime.

## 2026-07-22

- Kit upgrade 0.3.5 → 0.3.10 via the safe updater (`update-existing-repo` from
  a fresh kit clone), per the `okf-kit-upgrade` walkthrough. Refreshed in place
  after backups (`.okf-kit-backups/20260722T181506Z/`, manifest-proven unedited
  kit output): `scripts/okf`, both `.claude` hooks, the `.codex/hooks/
  check-docs-sync.sh` mirror, and the `okf-kit-upgrade`, `okf-adopt`, and
  `okf-second-agent` skills; `docs/index.md` restamped `kit_version` 0.3.5 →
  0.3.10. `.claude/settings.json` merge was a no-op (already current); three
  skills and every `.gitignore` entry were already current. The refreshed
  `check-okf-version.sh` carries kit improvements worth noting: shared
  `OKF-SHARED` awk parsers guarded by `make parity`, case-insensitive ADR
  status matching, and JSON escaping of owner-controlled values in the note
  payload.
- Candidates resolved: `.codex/hooks/check-okf-version.2.sh` was **adopted** —
  it is byte-identical to the refreshed `.claude` hook, which the declared
  `mirrors:` list (kit ADR 0021) and the parity guard require the Codex copy to
  match; the live 0.3.5 copy had diverged from the manifest so the updater
  staged it rather than overwriting. `AGENTS.2.md` was **declined and deleted**:
  it is the kit's generic single-agent template (bracketed, older timestamp,
  "me/my" voice), while this repo's `AGENTS.md` is the filled shared Claude+Codex
  playbook and additionally carries two repo-specific guardrails the template
  lacks ("Model output is untrusted input", "Preserve safe file-write
  behavior"). The template's only genuinely-new deltas (an explicit `.env`
  read-denial guardrail, an `.env.example` export-step note) are already covered
  in substance, so nothing was cherry-picked. Owner confirmed the decline.
- Post-update verification green: valid `settings.json`, `bash -n` on all kit
  scripts, `bash scripts/okf check-stale` current, no unresolved candidates, and
  `make check` passing (ruff, format, mypy strict, 121 tests, 94% coverage,
  okf-docs).

## 2026-07-19

- Kit upgrade 0.3.2 → 0.3.5 via the safe updater, per the `okf-kit-upgrade`
  walkthrough. Before the run, the `.codex/hooks/` mirror directory was
  declared in a new top-level `mirrors:` list in `docs/okf-map.yml` (kit ADR
  0021), so the updater now manages those copies. Refreshed in place after
  backups (manifest-proven unedited kit output): `scripts/okf`,
  `.claude/hooks/check-okf-version.sh`, and the `okf-kit-upgrade` skill;
  `check-docs-sync.sh` and four skills were already current, and
  `docs/index.md` was restamped in place. New sixth skill installed:
  `okf-second-agent` (kit ADR 0024) — the guided second-agent port this repo
  performed by hand, now kit-owned — paired into `.agents/skills/` verbatim
  (its text names both stacks factually), with the refreshed `okf-kit-upgrade`
  carried over Codex-worded. Candidates resolved: the
  `.codex/hooks/check-okf-version.2.sh` mirror candidate was adopted (mirrors
  stay byte-identical; the prior copy was unedited 0.3.2 output); the
  `CLAUDE.2.md` template candidate was declined — this repo is AGENTS.md-first
  and `CLAUDE.md` is an import shim, so the two template deltas that apply
  landed in `AGENTS.md` instead (the `mirrors:` declaration in the Codex
  config paragraph, the unresolved-candidate reminder in the version policy;
  the 0.3.3 `.env`-loading caveat was already satisfied by our "nothing loads
  `.env` automatically" wording, and the skill references are count-agnostic
  globs); the `docs/okf-map.2.yml` starter candidate was dropped (our map
  carries real mappings plus the new declaration). Kit-classifier note for
  harvest: the updater staged `CLAUDE.2.md` rather than `AGENTS.2.md` because
  our shim carries a `# Preloaded context` heading, which defeats the kit's
  heading-free commented-shim test (kit ADR 0022) — a shim variant the kit
  has not seen before. Verified: `make check` green, kit `verify-install`
  passed with zero warnings (mirror parity confirmed), `bash scripts/okf
  check-stale` current, and the SessionStart hook is fully silent — no drift,
  no advisory, no pending ADRs.
- Public-readiness polish and first-time-user acceptance pass complete. Updated
  `README.md` from the old walking-skeleton language to the implemented
  `check` command, added a copy-paste quickstart, and made that quickstart set a
  project-local `UV_CACHE_DIR` so locked-down environments do not depend on a
  writable home cache. Added `scripts/ci-fixture.py --fixture-dir PATH` so the
  quickstart can keep its clean/drift fixture repositories and replay files for
  follow-up `spec-drift check` runs; documented the mode in
  `docs/specs/ci-integration.md` and covered it in `tests/test_ci_fixture.py`.
  Refreshed stale public contributor/security docs that still referred to the
  removed template `create-project`/`rename-project` scripts, and updated
  `AGENTS.md`'s master objective to match the implemented CLI. Accepted ADR
  0002 at the owner's direction and updated the ADR index.
- Acceptance exercised in a pristine copy with the current patch applied:
  README setup (`uv sync --all-extras`), fixture creation, clean fixture
  analysis (exit 0), drift fixture analysis (exit 1), JSON report output
  (`report.json` observed), missing base ref (exit 2, clear message), missing
  `--base`, unknown provider, existing output without `--force`, and path
  traversal output refusal. Verification: `make ci-fixture`,
  `tests/test_ci_fixture.py`, `bash scripts/okf pending`, `bash scripts/okf
  check-stale`, and `make check` are green locally. The live-provider success
  criterion remains owner-gated: an `ANTHROPIC_API_KEY` is present, but no
  external model call was made without an explicit go-ahead because it sends
  fixture content outside the repo and may incur API cost.

## 2026-07-18

- Fixed a red CI that local `make check` could not see (lesson: check the hosted
  runs after a push, not just the local gate). Three environment/inheritance
  failures: (1) `scripts/ci-fixture.py` ran `git` without a fixed identity, so
  `git commit` failed on CI runners that have no global git user — now passes
  `GIT_AUTHOR_*`/`GIT_COMMITTER_*` and a hermetic config; (2) the `Tests`
  workflow still carried the template's `template-smoke` and `package-smoke`
  jobs, which run the removed `scripts/create-project` and assert the template's
  version, and (3) `code-quality` still shell-checked those deleted scripts —
  all removed, leaving each workflow scoped to this project. This is a template
  finding: `create-project` leaves generated projects with CI jobs and steps
  that reference template-only files, so a fresh project's CI is red until they
  are pruned. `ci-fixture.py`'s change is an internal fix with no contract
  change to `docs/specs/ci-integration.md`.
- Milestone 6 complete: documented CI integration. Ship a deterministic,
  offline `replay` provider (`src/spec_drift/providers/replay.py`) that plays
  back canned JSON replies keyed by the changed-file path — so the real `check`
  command runs reproducibly without a vendor key — plus `scripts/ci-fixture.py`
  and a `make ci-fixture` target that build a drift fixture and a clean fixture
  and assert the drift one fails (exit 1) and the clean one passes (exit 0),
  printing both Markdown reports. Added `.github/workflows/drift.yml` running
  that same target in a hosted runner (no secret). **Proposed ADR 0002
  (`docs/adr/0002-ci-integration.md`) authored for the CI-integration contract —
  awaiting review; implemented against it.** Documented in
  `docs/specs/ci-integration.md`, mapped in `docs/okf-map.yml` (check-stale
  current). Verification: `make ci-fixture` passes locally and
  `tests/test_ci_fixture.py` guards it; `tests/test_replay_provider.py` covers
  the provider; 120 tests green on Python 3.12, 3.13, and 3.14. The hosted
  Actions run is confirmed during the acceptance pass (milestone 7), after this
  push. The `new-adr` scaffold again omitted `owner`/`deciders`; added by hand.
- Milestone 5 complete: safe report-file output. `spec-drift check --output PATH
  [--force]` writes the report to a file instead of stdout, reusing the existing
  safe-write layer (`core/fileset.py`): the path must stay within the working
  directory (absolute or `..`-escaping paths refused, exit 2), an existing file
  is preserved without `--force`, and a forced write replaces only that file. On
  success stdout stays clean and a confirmation goes to stderr. Refactored the
  `check` runner to take a `CheckOptions` object (four options exceeded the
  argument-count lint). Updated `docs/specs/report.md`; check-stale current.
  Verification: `tests/test_check_output.py` covers containment, traversal and
  absolute-path refusal, overwrite refusal, and force-replaces-only-the-target —
  111 tests green on Python 3.12, 3.13, and 3.14.
- Milestone 4 complete: reports and the `check` command. Added
  `src/spec_drift/report/` (terminal/Markdown/JSON rendering of an
  `AnalysisReport`, all describing the same findings; pure, no I/O),
  `src/spec_drift/checker.py` (the `spec-drift check` command wiring
  collect → analyze → render with the 0/1/2 exit-code contract), the `check`
  subparser in `cli.py`, and the committed JSON contract
  `schemas/report.schema.json`. Documented in `docs/specs/report.md` and mapped
  in `docs/okf-map.yml` (the schema is itself a governing contract; check-stale
  current). Verification: `tests/test_report.py` shows all three formats name
  every finding, the JSON output validates against the committed schema (via a
  dependency-free schema validator in `tests/schema_check.py`, in keeping with
  the zero-dependency stance), and the `check` command returns 0/1/2 per the
  contract — including an end-to-end console-script run. 105 tests green on
  Python 3.12, 3.13, and 3.14.
- Accepted ADR 0001 (drift-analysis finding schema and model contract) at the
  owner's direction: status flipped to `accepted`, index updated; it now binds
  future work. Friction noted for the kit: `scripts/okf new-adr` scaffolds ADR
  frontmatter without `owner`/`deciders`, which `check-okf-docs.py` requires —
  the omission surfaced only once the ADR became tracked. Added both fields by
  hand; worth fixing in the kit's ADR template.
- Milestone 3 complete: the drift-analysis engine (`src/spec_drift/analysis/`)
  and validated finding model. `analyze(changeset, model, *, strict_coverage)`
  judges each governed change with one model call carrying its diff and
  governing documents, records unmapped changes without a call, and validates
  the untrusted JSON reply into a `Finding` (classification + paired citations),
  degrading anything unverifiable to `insufficient-evidence`. `AnalysisReport`
  computes the exit code, with `unmapped` actionable only under
  `strict_coverage`. **Proposed ADR 0001 (`docs/adr/0001-analysis-contract.md`)
  authored for the finding schema and model contract — awaiting review; the
  engine is implemented against it.** Documented in `docs/specs/drift-analysis.md`
  and mapped in `docs/okf-map.yml`; also extended `docs/specs/analysis-inputs.md`
  for the new per-file-diff capability (check-stale current). Verification:
  `tests/test_analysis.py` with a deterministic scripted provider reproduces
  clean/drift/decision-required/insufficient-evidence/unmapped with valid
  citations and confirms `--strict-coverage` flips the unmapped exit code —
  92 tests green on Python 3.12, 3.13, and 3.14.
- Milestone 2 complete: the analysis-inputs subsystem (`src/spec_drift/inputs/`)
  — repository discovery, read-only Git diff loading with rename detection,
  unsafe-path filtering (`.env`, outside-root, ignored, binary, in that
  priority), and governing-document resolution from `docs/okf-map.yml`'s
  `mappings:` block, assembled by `collect_changes` into an immutable
  `ChangeSet`. Zero new runtime dependencies: Git via the command line, the map
  via a purpose-built subset parser (`adr-suggest` clean). Documented in the new
  `docs/specs/analysis-inputs.md` and mapped in `docs/okf-map.yml` (check-stale
  current). Verification: fixture tests in `tests/test_inputs.py` cover a clean
  branch, modified/renamed/deleted/added changes, unmapped changes, invalid base
  ref, execution outside a repository, and `.env`/binary/ignored/outside-root
  exclusion — 77 tests green on Python 3.12, 3.13, and 3.14.
- Milestone 1 complete: package, canonical commands, fixture repositories, and
  quality gate established. Added `tests/repo_fixtures.py` — deterministic,
  offline builders for the clean and drift git fixture repositories (kit-style
  `docs/specs/` + `docs/okf-map.yml`, a `base` ref, and a governed change on
  `main`; the drift fixture removes the manager-approval check its spec
  requires) — with contract tests in `tests/test_repo_fixtures.py`, plus a
  `--help` CLI test. Verification passed: `spec-drift --help`, `make test`, and
  `make check` green on Python 3.12, 3.13, and 3.14 (`make check-all`).
  Non-blocking: new test files are unmapped in `docs/okf-map.yml` until their
  governing specs exist. No ADR-shaped changes (`adr-suggest` clean).

## 2026-07-17

- Completed the initial project setup after seeding from python-cli-template and
  installing the kit: rewrote `README.md` for spec-drift, resolved the kit's
  `CLAUDE.2.md` playbook candidate into a single-source `AGENTS.md` (shared by
  Claude Code and Codex) with `CLAUDE.md` importing it, and aligned the
  command name in `docs/GOAL.md` from `specdrift` to `spec-drift` to match the
  installed console command.
- Started the project documentation bundle from the Python CLI template.
