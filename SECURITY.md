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

- `scripts/create-project` and `scripts/rename-project`, because they write
  files into user-selected paths.
- Generated-project setup and dependency installation paths.
- Provider adapters that touch credentials or model-provider SDKs.
- GitHub Actions and Dependabot configuration.

The template should never require checked-in secrets. Keep credentials in the
environment and use `.env.example` only as documentation.
