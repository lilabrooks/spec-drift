---
type: Playbook
title: Repository instructions
description: Shared master objective, stack, grounding rules, and workflow for coding agents in this repository.
tags: [agent-instructions, adr, specs, drift]
timestamp: 2026-07-17T00:00:00Z
owner: "Lila Brooks"
deciders: ["Lila Brooks"]
---

<!-- Shared operating contract for coding agents (Claude Code and Codex) in this
     repository. Claude Code loads it through CLAUDE.md's `@AGENTS.md` import;
     Codex reads it directly. Edit this file, not CLAUDE.md. Coding agents
     ignore the frontmatter; it exists to make this file a valid OKF concept
     (type is the only required field, per OKF v0.1). -->

# Master objective

Current state: A walking skeleton seeded from python-cli-template — the quality
gate, repository-health tests, CI, and the provider-neutral model layer are in
place; the command surface is still the template's `hello`/`ask`/`providers`,
and no drift analysis exists yet.

Target state: The `spec-drift check` CLI per `docs/GOAL.md` — read a Git diff,
resolve governing Markdown specs/ADRs (with `docs/okf-map.yml` supported
first-class), classify governed changes as clean/drift/decision-required/
insufficient-evidence with `unmapped` notes for undocumented ones, and report to
terminal, Markdown, and JSON with stable exit codes.

Constraints: `docs/GOAL.md` § Constraints; no specs or ADRs yet — decision-shaped
choices (runtime dependencies, output schema, provider contract, CI ownership)
start as proposed ADRs in `docs/adr/`.

Done when: every `docs/GOAL.md` milestone is checked, its success criteria pass
(including the owner-gated live-provider run), and `make check` is green —
environment preflight, ruff, mypy strict, pytest with the 90% branch-coverage
floor, and `scripts/check-okf-docs.py`.

`docs/GOAL.md` carries the detail — kind, problem, target state, success
criteria, and the ordered milestone backlog. The Master objective above is its
one-screen summary; keep the two consistent, with `docs/GOAL.md` authoritative.
Claude Code preloads `docs/GOAL.md` through the imports in `CLAUDE.md`; Codex
reads it at session start. Re-read it during a session only after it changes.

# Setup

Use uv and commit the generated `uv.lock`:

```bash
uv sync --all-extras
uv run make check
```

The portable fallback is:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,anthropic,openai]"
make check
```

For Codex cloud environments, put the applicable setup block above in the
environment setup script: setup runs with network access, while agent-phase
internet access is off by default.

The default `echo` provider works offline. Treat Anthropic and OpenAI calls as
external operations that require the matching optional dependency, network
access, and an environment-provided API key.

This repository lives in an iCloud-synced folder. Sync stamps macOS hidden
flags onto `.venv`, which Python 3.13+ silently skips, so the environment is
built as `.venv.nosync` with a `.venv` symlink (sync tools ignore `*.nosync`).
If `uv sync` ever replaces the symlink with a real `.venv` and the console
script stops importing its package, rebuild: `rm -rf .venv .venv.nosync &&
uv venv .venv.nosync && ln -s .venv.nosync .venv && VIRTUAL_ENV="$PWD/.venv.nosync"
uv pip install -e ".[dev,anthropic,openai]"`. The `check-env` preflight below
catches the corruption if it recurs.

# Verification

Run `make check` after every change and before checking off any milestone. It
runs an environment preflight, ruff lint and formatting checks, strict mypy,
pytest with branch coverage, and documentation validation. The coverage floor
is 90%. A milestone with a failing gate is not done.

The preflight (`scripts/check-env.py`) fails fast when file syncing has damaged
the checkout: hidden flags on `.venv` `.pth` files, ` 2` conflict duplicates, or
`.icloud` placeholders. Apply the fix it prints.

Use `make check-all` when a change may behave differently across Python 3.12,
3.13, and 3.14. It requires `uv`, can download interpreters, and uses isolated
environments without replacing the project's `.venv` or writing a lockfile.

## Verification commands

- Tests: `make test`
- Lint + format check: `make lint`
- Type check: `make typecheck`
- Full gate: `make check` (add `make check-all` for the version matrix)
- OKF stale map: `bash scripts/okf check-stale`

# Goal iteration

- When asked to continue or iterate without a specific task, take the first
  unchecked milestone in `docs/GOAL.md` and run it through the task workflow
  below. When its verification passes, check it off, log it, and continue with
  the next unchecked milestone. Stop when the backlog is empty, a decision
  reserved for the owner comes up, or the owner says stop.
- Resuming after an interruption: at session start, if the working tree holds
  uncommitted changes, treat them as in-flight work from a cut-off session, not
  a clean slate. Reconcile them against the first unchecked milestone and the
  newest `docs/log.md` entry, then finish or back out that work before taking a
  new milestone.
- Check a milestone off only when its stated verification passes, then add a
  dated `docs/log.md` entry (newest first, ISO `YYYY-MM-DD` headings).
- Before reporting the goal met, run the acceptance pass (the
  `okf-acceptance-pass` skill carries the full checklist): exercise the
  deliverable as a first-time user — clean checkout, README quickstart, the
  goal's example interactions plus obvious variants and wrong inputs. Tests
  prove the contract; this pass proves the experience. Fix in-scope breakage
  before declaring the goal met, record what was exercised in `docs/log.md`, and
  carry out-of-scope findings into candidate milestones.
- When every milestone is checked, the success criteria pass, and the acceptance
  pass is clean, report that the goal is met and stop building. List any ADRs
  still `status: proposed` (`bash scripts/okf pending`) so the owner can review
  them, then offer candidate next milestones — known items in `docs/log.md`,
  revisit triggers in accepted ADRs, acceptance-pass findings, standard repo
  hygiene the repo still lacks, and extensions that fit the stated non-goals.
  Proposing is not adding: nothing enters `docs/GOAL.md` without the owner's
  confirmation.
- When the code and the goal disagree, flag it. Changing `docs/GOAL.md` (scope,
  success criteria, milestone order) is the owner's decision.
- If `docs/GOAL.md`, or a Master objective bracket, is missing content or still
  contains unfilled template brackets, run the goal interview before iterating.

# Goal interview

When `docs/GOAL.md` still needs filling, run the goal interview with the owner
before iterating — a few questions at a time, drafting as you go, instead of
asking the owner to edit templates. The `okf-goal-interview` skill carries the
full script with worked examples. Push back on answers that can't be checked
mechanically; in an existing codebase propose answers from the code first and
let the owner correct them; draft the backlog to end with a README-quickstart
milestone by default; confirm the finished `docs/GOAL.md` with the owner before
starting the loop. Manual editing stays a valid alternative; never overwrite
goal content the owner wrote by hand.

# Grounding rules (docs are the source of truth)

- The spec and ADR indexes are preloaded for Claude Code and read at session
  start by Codex. Before planning any change, read the specific spec or ADR
  governing the files you'll touch.
- When code and docs disagree, flag the mismatch. Don't silently pick a side.
- If a task conflicts with an accepted ADR, stop and ask before writing code.
  Superseding an accepted ADR is the owner's decision, made via a new ADR file.
- Architectural changes start with a new ADR in `docs/adr/`, written per the
  decision policy below, before any implementation.

# Decision policy (the owner owns the goal, you drive the decisions)

The owner provides the goal, constraints, and guardrails; you make the decisions
that reach the goal and record them where the owner can review them.

- Implementation choices that stay inside existing specs, accepted ADRs, and the
  guardrails below are yours to make without asking.
- Decision-shaped changes — dependency, persistence, cache/queue/worker,
  auth/security/privacy, API contract, deployment, ownership boundary — start
  with a new ADR marked `status: proposed` (scaffold it with `bash scripts/okf
  new-adr <slug> "Title"`), covering context, decision, alternatives,
  consequences, and a rollback or revisit trigger. Implement against the
  proposed ADR, then flag it in your summary and in `docs/log.md`; the owner
  accepts it, asks for changes, or reverts.
- ADR review mechanics (the `okf-adr-review` skill carries the full flow): the
  owner finds pending decisions with `bash scripts/okf pending`. When told to
  accept or reject a proposed ADR, make the status edit and any reversal
  yourself and log the outcome — the decision is the owner's, the edit can be
  yours.
- Reserved for the owner: changing `docs/GOAL.md`, superseding or contradicting
  an accepted ADR, and the actions the guardrails below mark as needing a
  go-ahead. When work can't proceed without one of these, record the blocker in
  `docs/log.md` and ask instead of working around it.

# Guardrails (hold in every session)

Tests and verification:

- Run the gate (see Verification commands) after every change and before
  checking off any milestone. A milestone with a failing gate is not done.
- Never delete, skip, weaken, or mark as flaky a failing test or check to get a
  green run. Fix the code; if the test itself is wrong, say so and get the
  owner's confirmation before changing it.
- Report outcomes as they are. Failures, partial progress, and skipped
  verifications go in the summary and `docs/log.md`, not under the rug.
- Add or update tests when behavior changes. Keep provider tests offline; use
  fakes or mocks for vendor SDK calls.

Security and safety:

- Never write secrets — API keys, tokens, passwords, private keys, connection
  strings — into tracked files. Read them from the environment, and before
  creating an env or credentials file, confirm `.gitignore` covers it.
- Document required and optional environment variables in the committed
  `.env.example` (placeholder values only); real values live in the git-ignored
  `.env`. Nothing loads `.env` automatically — the settings layer reads
  `os.environ` directly.
- Treat changes touching auth, input parsing, file paths, network exposure, or
  permissions as security-sensitive: validate input at trust boundaries, grant
  least privilege, and run `bash scripts/okf adr-suggest`; when it flags the
  change, record the decision as a proposed ADR.
- Model output is untrusted input: parse and validate it before display or
  serialization. Exclude `.env`, ignored, credential, and binary files, and
  paths outside the repository root, before model invocation.
- Preserve safe file-write behavior: reject path escapes and refuse overwrites
  unless the caller explicitly opts in.
- New runtime dependencies are decision-shaped: the proposed ADR names the
  alternatives considered and the maintenance and security tradeoff.
- Never commit `.env`, `.venv/`, `.venv.nosync/`, coverage databases, caches, or
  build output.

Needs the owner's explicit go-ahead, every time:

- Force pushes or history rewrites on shared branches; deleting or migrating
  stored data; deleting files beyond the task's scope.
- Publishing, deploying, releasing, or calling external services with side
  effects.

# Workflow for each task

1. Impact analysis: name the specs and ADRs that govern the target files.
2. Implement. Run the gate (`make check`) and make it pass.
3. Knowledge alignment: run `bash scripts/okf check-stale`. If behavior or a
   contract changed, update the governing spec or ADR to match, and add a dated
   `docs/log.md` entry. If no doc change is warranted, add a one-line entry
   saying why. New spec or ADR files also get added to their directory's
   `index.md`.
4. ADR check: run `bash scripts/okf adr-suggest` for dependency, persistence,
   cache/queue/worker, auth/security/privacy, public API, deployment, or
   ownership-boundary changes. Draft an ADR only for a real decision.

# Docs bootstrap

The knowledge bundle lives under `docs/`:

```
docs/
├── index.md        # bundle root: declares okf_version, links the bundle files
├── GOAL.md         # goal, success criteria, milestone backlog
├── log.md          # dated changelog, newest first
├── okf-map.yml     # maps source paths to governing specs/ADRs
├── specs/
│   ├── index.md    # lists each spec with a one-line description
│   └── _drafts/    # generated spec drafts; review before promoting
└── adr/
    └── index.md    # lists each ADR with a one-line description
```

`docs/index.md` is the only `index.md` allowed frontmatter; it declares
`okf_version`. Every new spec or ADR gets YAML frontmatter with at least a
`type:` field (OKF v0.1), plus `title` and `description`. Keep each `index.md`
current when files are added or renamed. `docs/okf-map.yml` maps source globs to
the specs and ADRs that govern them; keep it current when modules move or new
source areas gain contracts. Adopting an existing codebase goes beyond bootstrap
— the `okf-adopt` skill carries the inventory-and-map sequence.

# OKF helper commands

`scripts/okf` is a repo-local Bash helper installed by claude-okf-repo-kit — not
an official OKF CLI, not global, not a prompt. Run it as `bash scripts/okf ...`.
Prefer it over re-deriving numbering, index entries, or staleness by hand; when
a helper declines on this repo's conventions, do the workaround in the open and
record it in a dated `docs/log.md` entry.

- `bash scripts/okf check-stale` — run after changing source files. Update the
  mapped spec/ADR, or add a dated `docs/log.md` rationale, when it reports stale
  mappings. It also lists changed files with no mapping — non-blocking.
- `bash scripts/okf draft [paths...]` — generate fact-based spec drafts under
  `docs/specs/_drafts/`. Treat drafts as scaffolding: verify, rewrite into
  human-readable commitments, promote into `docs/specs/`, update the index.
- `bash scripts/okf adr-suggest` — run when a change may include an architecture
  decision.
- `bash scripts/okf new-adr <slug> [title]` — scaffold the next-numbered ADR
  with `status: proposed` frontmatter and an index entry. Fill every bracket
  before implementing against it.
- `bash scripts/okf new-spec <slug> [title]` — scaffold a spec with an index
  entry, then fill it in and map the governed source in `docs/okf-map.yml`.
- `bash scripts/okf pending` — list ADRs still `status: proposed`. Run it when
  reporting the goal met, and whenever the owner asks what's awaiting review.

# Agent config (committed to the repo)

Shared: `docs/` (goal, indexes, log, `okf-map.yml`), `scripts/okf`, `README.md`.

Claude Code: `CLAUDE.md` (imports this file plus the preloaded goal/indexes),
`.claude/settings.json` (guardrail hooks and the permission rule denying `.env`
reads), `.claude/skills/okf-*/SKILL.md`, `.claude/hooks/check-docs-sync.sh`
(Stop hook), `.claude/hooks/check-okf-version.sh` (SessionStart hook). All
committed. Don't move, rename, or disable the hooks; if one blocks, do the
update it asks for.

Codex: `.codex/hooks.json` and `.codex/hooks/*.sh` (byte-identical to the Claude
hooks — a repository-health test enforces the parity), and `.agents/skills/okf-*`
(the same skill set, Codex-worded).

Never commit: `.claude/settings.local.json`, `CLAUDE.local.md`,
`.codex/settings.local.json`, `Codex.local.md` — personal overrides only.

# OKF and kit version policy

A SessionStart hook compares `okf_version` and `kit_version` in `docs/index.md`
against upstream. On an OKF minor bump, migrate automatically (formatting,
frontmatter, structure only — never spec or ADR content) and log it; on a major
bump, stop and present a migration summary first. On kit drift, tell the owner
and recommend the safe updater `scripts/update-existing-repo` from an up-to-date
kit clone (the `okf-kit-upgrade` skill carries the walkthrough). If the skills
don't load, the resident rules here still bind — proceed from these one-liners.
