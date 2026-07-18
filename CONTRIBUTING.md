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
- In the template repository, keep the generated-project path working through
  `scripts/create-project`.
- Update `CHANGELOG.md` for user-visible changes.
- Mirror dependency changes between `pyproject.toml` and `requirements.txt`
  when optional extras change.
- Keep documentation agent-neutral unless a file is intentionally specific to
  one tool.

## Change style

Prefer small, direct patches. In the template repository, every extra choice
is copied into new projects, so defaults should be useful for most Python CLI
tools.

## Generated projects

When changing the template's setup scripts, test at least one generated
project. CI covers both uv and pip paths, and a local generated project catches
awkward output or missing cleanup quickly.
