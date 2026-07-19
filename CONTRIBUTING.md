# Contributing

Thanks for helping keep this project boring in the best way: green checks,
small changes, and no mystery setup.

## Local setup

Use uv when possible:

```bash
uv sync --all-extras
uv run make check
```

Portable fallback:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,anthropic,openai]"
make check
```

If you are working in Codex cloud, put dependency installation in the
environment setup script so it runs while network access is available.

## Before opening a pull request

- Run `make check`.
- For changes to the `check` command, reports, replay provider, or fixture
  scripts, update the matching spec or ADR under `docs/`.
- Update `CHANGELOG.md` for user-visible changes.
- Mirror dependency changes between `pyproject.toml` and `requirements.txt`
  when optional extras change.
- Keep documentation agent-neutral unless a file is intentionally specific to
  one tool.

## Change style

Prefer small, direct patches. Behavior changes should include focused tests and
docs updates when they change the CLI contract, output schema, provider
contract, or CI behavior.

## Fixture and CI changes

When changing `scripts/ci-fixture.py`, the replay provider, or the GitHub
Actions workflow, run both:

```bash
make ci-fixture
make check
```

The fixture path is intentionally deterministic and offline; do not add a
required vendor key or network call to the default CI demonstration.
