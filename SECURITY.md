# Security policy

## Supported versions

This project tracks the current `main` branch. Released tags are kept for
history, and security fixes land on `main` first.

## Reporting a vulnerability

Please report security issues privately through this repository's **Security**
tab by choosing **Report a vulnerability**. If private vulnerability reporting
is unavailable, email the maintainer at `lila.m.brooks@gmail.com`. Please
include:

- A short description of the issue.
- Steps to reproduce it.
- The affected files, commands, or generated-project path.
- Any known workaround.

Do not open a public issue for a vulnerability until there is a fix or a clear
disclosure plan.

## Scope

Security-sensitive areas include:

- Git diff loading, changed-file filtering, and governing-document resolution,
  because they decide which repository content enters model context.
- Report-file output paths, because `--output` writes to a user-selected
  location and must stay inside the working directory unless the contract
  changes.
- The replay provider and fixture scripts, because they feed deterministic model
  replies into the real `check` command.
- Provider adapters that touch credentials or model-provider SDKs.
- GitHub Actions and Dependabot configuration.

The project should never require checked-in secrets. Keep credentials in the
environment and use `.env.example` only as documentation.

## Repository security setup

One-time settings a maintainer should confirm on the GitHub repository (they are
account/repo settings, not code, so they live here rather than in a workflow):

- [ ] **Secret scanning** — enable under **Settings → Code security**. Free for
  public repositories; it scans history and a broad partner-pattern set.
- [ ] **Push protection** — enable in the same place. It blocks a push the moment
  it contains a recognized secret, catching leaks the local gate would miss.
- [x] **Dependabot alerts and security updates** — enabled 2026-07-23; this repo
  also commits `.github/dependabot.yml` for weekly version-update checks.

These back up the in-repo defenses, which are already enforced automatically:
`scripts/check-secrets.py` runs in `make check` and the `secret-scan` workflow
([ADR 0004](docs/adr/0004-secret-scanning.md)), API keys are read from the
environment by the provider SDKs, and `.env`/credential files are excluded from
analysis and git-ignored.
