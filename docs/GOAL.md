---
type: Goal
title: Spec-drift project goal
description: The goal, success criteria, constraints, and milestone backlog for the spec-drift CLI.
tags: [goal, milestones, cli, specs, adr, drift]
timestamp: 2026-07-14T00:00:00Z
owner: Lila Brooks
deciders: [Lila Brooks]
---

# Goal

Kind: utility

Problem: Engineering teams record intended behavior in specifications and architecture decisions, but code changes can silently contradict those documents. Reviewers must manually connect changed files to governing documentation, interpret whether the change affects a contract, and determine whether the code or documentation needs correction.

Solution: The `spec-drift` CLI examines a Git diff alongside the repository's Markdown specs, ADRs, and optional source-to-document map. It produces an evidence-backed report classifying each governed change as clean, specification drift, decision required, or insufficient evidence; changes with no governing document are reported as unmapped notes, not failures. Findings cite the exact source change and governing document clause.

# Target state

The following command works in any supported Git repository:

```bash
spec-drift check --base origin/main
```

`spec-drift`:

- Discovers the repository root and changed files.
- Reads the Git diff without modifying the working tree.
- Excludes ignored files, credentials, `.env` files, binaries, and unsupported content.
- Finds governing specs and ADRs through an optional mapping file — `docs/okf-map.yml`, the claude-okf-repo-kit convention, is supported first-class, so a kit-adopted repository is a zero-configuration target — and documented repository conventions.
- Evaluates changed behavior against those documents using a configured model provider.
- Gives accepted ADRs precedence over implementation when they disagree.
- Classifies governed changes as `clean`, `drift`, `decision-required`, or `insufficient-evidence`. Changes with no governing document are reported separately as `unmapped` — a non-blocking note by default, promoted to a failure only under `--strict-coverage` — so partially documented repositories can adopt the tool without failing on every undocumented file.
- Cites repository-relative file paths and line numbers for every substantive claim.
- Supports terminal, Markdown, and JSON output.
- Uses stable exit codes suitable for local scripts and CI.
- Remains read-only unless the user explicitly requests an output file.
- Refuses to overwrite an existing report unless `--force` is supplied.

Primary interactions:

```bash
spec-drift check --base origin/main
```

Reports whether the current branch has drifted from its governing specs and ADRs.

```bash
spec-drift check --base v1.4.0 --format json --output drift-report.json
```

Produces a machine-readable report suitable for CI or further automation.

```bash
spec-drift check --base missing-ref
```

Exits with a clear error naming the invalid Git reference. It does not display a stack trace or make a model request.

# Success criteria

On a clean machine with Python 3.12+ and Git installed:

- Installing the package and running `spec-drift --help` succeeds without credentials or network access.
- A fixture where implementation and specifications agree returns exit code `0` and a `clean` result.
- A fixture where code removes a required approval check returns exit code `1`, classifies the finding as `drift`, and cites both the changed source line and the governing specification clause.
- A fixture that changes authentication, dependencies, persistence, deployment, a public API, or another architecture boundary returns exit code `1` with `decision-required` when no corresponding decision record changed.
- A fixture with changed code but no governing document reports `unmapped` as a non-blocking note and returns exit code `0`, rather than inventing a contract; the same fixture under `--strict-coverage` returns exit code `1`. `insufficient-evidence` is reserved for governed changes whose evidence cannot be judged.
- Invalid Git references, malformed mapping files, unsupported repositories, and provider failures return exit code `2` with actionable messages and no stack traces.
- Terminal, Markdown, and JSON output represent the same findings.
- JSON output validates against the project's committed report schema.
- Ignored files, `.env` files, credentials, and binary content never enter model context or report output.
- Output written with `--output` stays within the requested destination and is never overwritten without `--force`.
- Tests run without network access through deterministic fixture providers.
- Owner-gated (needs a configured provider key): `spec-drift check` with a real provider against the drift fixture reproduces the fixture classification with valid source and document citations — proving the live provider path, not just the deterministic one.
- `make check` passes: lint, formatting, strict type checking, tests, branch-coverage threshold, and documentation validation.
- The README quickstart can be reproduced verbatim from a clean checkout.

Exit-code contract:

- `0`: no actionable drift found; `unmapped` notes alone never fail the run unless `--strict-coverage` is set.
- `1`: drift, a decision requirement, or insufficient evidence on a governed change requires review (plus `unmapped` findings under `--strict-coverage`).
- `2`: input, repository, configuration, or provider failure prevented analysis.

# Non-goals

- No automatic edits to source code, specifications, ADRs, or mapping files.
- No automatic acceptance, rejection, or superseding of architecture decisions.
- No general-purpose code review, style review, vulnerability scanning, or dependency auditing.
- No claim that undocumented implementation behavior is an authoritative contract.
- No hosted service, dashboard, IDE extension, or GitHub App in the first release.
- No conversation history, autonomous repair loop, or iterative self-correction. One model call per analysis unit is expected — a large diff becomes several units, never a retry loop that rewrites findings.
- No support for arbitrary documentation formats beyond Markdown in the first release.
- No full-repository semantic index or persistent vector database.

# Constraints

- Python 3.12-3.14.
- Provider-neutral model boundary with an offline deterministic provider for tests.
- Git is the source of changed-file and diff information.
- Read-only repository access by default.
- Repository-relative paths in all model context and output.
- Accepted ADRs override conflicting implementation behavior until the owner supersedes them.
- Every finding on a governed change must include evidence from both the diff and governing documentation. Missing evidence produces `insufficient-evidence`; a change with no governing document produces `unmapped`, never a judged finding.
- Model output is untrusted input and must be parsed and validated before display or serialization.
- `.env` files, ignored files, credential files, binary files, and files outside the repository root are excluded before model invocation.
- Context size is bounded mechanically. When the required evidence exceeds that bound, the CLI reports insufficient evidence instead of silently truncating material.
- Report writes follow safe-by-default behavior: plan first, remain inside the selected destination, and refuse silent overwrites.
- New runtime dependencies, output schemas, provider-contract changes, and CI ownership changes require proposed ADRs before implementation.

# Milestones

Ordered backlog; check off a milestone only after its stated verification passes.

- [x] Establish the package, canonical commands, fixture repositories, and quality gate.
  - Verification: `spec-drift --help`, `make test`, and `make check` succeed on Python 3.12-3.14.

- [x] Implement deterministic repository discovery, Git diff loading, ignored-file filtering, and governing-document resolution.
  - Verification: fixture tests cover a clean branch, modified files, renamed files, deleted files, changed files with no governing document, an invalid base reference, execution outside a Git repository, ignored files, `.env` files, binary files, and paths outside the repository root.

- [x] Implement the provider-neutral drift-analysis skill and validated finding model.
  - Verification: deterministic provider fixtures reproduce golden results for `clean`, `drift`, `decision-required`, `insufficient-evidence`, and `unmapped`, with valid source and document citations, and `--strict-coverage` flips the `unmapped` fixture's exit code.

- [x] Implement terminal, Markdown, and JSON reports with stable exit codes.
  - Verification: all three formats describe the same fixture findings; JSON validates against the committed schema; exit codes match the documented contract.

- [ ] Implement safe report-file output.
  - Verification: output stays under the selected destination, traversal attempts fail, existing files are preserved without `--force`, and a forced write replaces only the selected report.

- [ ] Add a documented CI integration.
  - Verification: a local `make ci-fixture` target runs the same steps the workflow defines, failing for an actionable drift fixture and passing for a clean fixture with the Markdown report printed. The hosted GitHub Actions run itself is owner-gated (needs a push to GitHub) and is confirmed during the acceptance pass.

- [ ] Complete the README quickstart and first-time-user acceptance pass.
  - Verification: from a clean checkout, follow the README verbatim to install `spec-drift`, analyze the clean fixture, detect the drift fixture, produce JSON output, and receive a clear error for a missing Git reference.
