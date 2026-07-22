---
type: ADR
title: Secret scanning in the quality gate
description: A dependency-free repo-local scanner (scripts/check-secrets.py) blocks committed keys/tokens in the gate and CI, chosen over gitleaks/detect-secrets to preserve the zero-dependency stance.
tags: [adr, security, ci, tooling]
timestamp: 2026-07-22T19:28:20Z
status: accepted
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Status

Accepted 2026-07-22. Binds future work; supersede only via a new ADR. The
repo-local scanner is the offline first line; GitHub secret scanning and push
protection (free for this public repo) are the complementary provider-side
backstop that also covers git history — enable them in the repository's
Code-security settings.

# Context

The guardrails forbid writing secrets into tracked files, and a manual scan
confirmed none are present today. Nothing yet *enforces* that: a future commit
could hardcode an API key, token, or private key, and only human review would
catch it. The owner asked for a mechanical check so this cannot regress. This is
a security/tooling and CI-ownership change — decision-shaped — so it starts as a
proposed ADR. It touches no runtime code and adds no runtime dependency.

# Decision

Add a **dependency-free, repo-local scanner**, `scripts/check-secrets.py`
(stdlib only), that reads the set of tracked files via `git ls-files` and fails
with a non-zero exit and a file:line report when it finds:

- known credential prefixes — `sk-ant-…` / `sk-…` (Anthropic/OpenAI), `AKIA…`
  (AWS access key id), `ghp_…` / `gho_…` / `github_pat_…` (GitHub), `xox[baprs]-…`
  (Slack), `AIza…` (Google);
- private-key PEM blocks (`-----BEGIN … PRIVATE KEY-----`);
- an assignment of a long literal to a key/secret/token/password name
  (`API_KEY = "…"`), excluding obvious placeholders (`your-…-here`, `changeme`,
  `example`, `<…>`, empty values).

It is wired into the `make check` gate (a new `secrets` target) and runs in CI
as its own lightweight workflow. It follows the existing pattern of
`scripts/check-env.py` and `scripts/check-okf-docs.py`: a small committed check,
not a packaged tool. `.env.example` is scanned like any file — its placeholder
values must stay non-secret. The scanner is mapped to this ADR in
`docs/okf-map.yml`.

# Alternatives considered

- **gitleaks (binary or `gitleaks/gitleaks-action`).** More thorough (entropy
  analysis, git-history scanning). Rejected as the default: it adds an external
  action/binary to pin and trust, and its GitHub Action has an org-license wrinkle
  — extra supply-chain surface for a small utility repo whose defining constraint
  is zero dependencies. Named as the revisit target if history scanning or entropy
  detection becomes necessary.
- **detect-secrets (Yelp), a Python dev dependency + baseline file.** Fits the
  stack but adds a dependency and a `.secrets.baseline` to maintain, and the
  baseline can rot into a rubber stamp. Rejected to keep the toolchain minimal.
- **Rely on GitHub push protection / secret scanning alone.** Useful but
  provider-side, not reproducible in the local `make check` gate, and limited to
  partner patterns. Kept as complementary, not the mechanism.
- **Do nothing (manual review).** Rejected: the owner asked for enforcement, and
  a one-time manual scan does not prevent regressions.

# Consequences

- A committed key matching a known pattern fails the gate locally and in CI
  before it can merge; the check runs offline with no dependency.
- Coverage is pattern-based: it catches known prefixes and blatant assignments,
  not arbitrary high-entropy secrets or ones already in git history. This is a
  first line of defense, not a guarantee — the revisit trigger covers the gap.
- A new false-positive surface: a real long literal that looks like a secret may
  need an inline allow marker (`# pragma: allowlist secret`) the scanner honors,
  or a placeholder-style value. Test fixtures that write fake secrets into
  throwaway repos live under `tests/` and use non-matching sentinels.
- The gate gains one more step; contributors must keep `.env.example` values as
  obvious placeholders.

# Rollback / revisit trigger

Revisit if a real secret slips past the pattern set, if scanning git *history*
(not just the current tree) becomes required, or if false positives grow
burdensome — at which point adopt gitleaks (pinned by commit SHA) or
detect-secrets and retire the local scanner. Reverting means deleting
`scripts/check-secrets.py`, its `make` target, and its workflow; nothing persists.
