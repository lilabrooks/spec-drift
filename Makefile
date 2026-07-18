# Local quality checks. Mirrors the GitHub Actions workflows.
#
#   make check       Run lint, type-check, tests, and docs validation on the
#                    active interpreter (whatever your .venv has). This is the
#                    everyday command.
#   make check-all   Run the same checks across every supported Python version.
#                    Uses uv with isolated environments, leaving the project's
#                    .venv and lockfiles untouched. CI already does this on
#                    push, so reach for it mainly to reproduce a
#                    version-specific failure locally.
#
# Individual targets (check-env, lint, typecheck, test, okf, coverage) are
# available too.

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
RUFF ?= $(if $(wildcard .venv/bin/ruff),.venv/bin/ruff,ruff)
MYPY ?= $(if $(wildcard .venv/bin/mypy),.venv/bin/mypy,mypy)
PYTEST ?= $(if $(wildcard .venv/bin/pytest),.venv/bin/pytest,pytest)
VERSIONS ?= 3.12 3.13 3.14
UV_RUN ?= uv run --isolated
TEMPLATE_SCRIPTS := $(wildcard scripts/create-project scripts/rename-project)

.PHONY: check check-env shell lint format typecheck test okf coverage check-all

check: check-env shell lint typecheck coverage okf

check-env:
	$(PYTHON) scripts/check-env.py

shell:
	@if [ -n "$(TEMPLATE_SCRIPTS)" ]; then bash -n $(TEMPLATE_SCRIPTS); fi

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) format .

typecheck:
	$(MYPY)

test:
	$(PYTEST)

okf:
	$(PYTHON) scripts/check-okf-docs.py

coverage:
	@$(PYTHON) -c 'import coverage' >/dev/null 2>&1 || { \
		echo "coverage is not installed. Run '$(PYTHON) -m pip install -e \".[dev]\"'."; \
		exit 127; \
	}
	$(PYTHON) -m coverage run -m pytest
	$(PYTHON) -m coverage report

check-all:
	@command -v uv >/dev/null 2>&1 || { \
		echo "check-all needs uv (https://docs.astral.sh/uv/). Install it, or run 'make check' per interpreter."; \
		exit 1; \
	}
	@root="$(CURDIR)"; scratch=$$(mktemp -d); \
	trap 'rm -rf "$$scratch"' EXIT; \
	for v in $(VERSIONS); do \
		echo "=== Python $$v ==="; \
		(cd "$$scratch" && $(UV_RUN) \
			--with-editable "$$root" \
			--with-requirements "$$root/requirements.txt" \
			--python "$$v" -- sh -eu -c ' \
				cd "$$1"; \
				python scripts/check-env.py; \
				ruff check .; \
				ruff format --check .; \
				mypy; \
				coverage erase; \
				coverage run -m pytest; \
				coverage report; \
				python scripts/check-okf-docs.py \
			' sh "$$root") || exit 1; \
	done
	@echo "All versions passed."
