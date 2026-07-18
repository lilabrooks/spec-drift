Repository instructions live in AGENTS.md, shared with Codex — the master
objective, stack, grounding rules, decision policy, guardrails, and task
workflow. Edit AGENTS.md, not this file.

@AGENTS.md

# Preloaded context

These imports resolve when Claude Code loads this file, so the goal and the
knowledge indexes are in context at session start without a read step. Keep the
imported files small; full specs and ADRs stay on disk until a task needs them.

@docs/GOAL.md
@docs/specs/index.md
@docs/adr/index.md
