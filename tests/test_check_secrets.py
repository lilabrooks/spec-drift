"""Tests for scripts/check-secrets.py (ADR 0004).

Secrets are built at runtime by concatenation so this test file contains no
literal a secret scanner (which scans tracked files, including this one) would
itself flag.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-secrets.py"


def _load_scanner() -> object:
    spec = importlib.util.spec_from_file_location("check_secrets", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_secrets = _load_scanner()


def _alnum(prefix: str, n: int) -> str:
    return prefix + ("abcdef0123456789" * 8)[:n]


def _upper(prefix: str, n: int) -> str:
    return prefix + ("ABCDEFGH0123456789" * 8)[:n]


@pytest.mark.parametrize(
    "secret",
    [
        _alnum("sk-ant-", 30),
        _alnum("sk-", 30),
        _upper("AKIA", 16),
        _alnum("ghp_", 36),
        _alnum("xoxb-", 20),
        _alnum("AIza", 35),
        "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
    ],
)
def test_known_credential_shapes_are_flagged(secret: str) -> None:
    assert check_secrets.scan_text(secret), f"missed: {secret[:8]}…"


def test_hardcoded_assignment_is_flagged() -> None:
    line = 'api_key = "' + _alnum("", 24) + '"'
    assert check_secrets.scan_text(line)


def test_placeholder_values_are_ignored() -> None:
    assert check_secrets.scan_text('ANTHROPIC_API_KEY = "your-anthropic-key-here"') == []
    assert check_secrets.scan_text('token: "example-token-value-here"') == []


def test_non_literal_assignment_is_not_flagged() -> None:
    # A reference to a variable/attribute is not a hardcoded secret.
    assert check_secrets.scan_text("token = request.headers.get('authorization')") == []


def test_allowlist_marker_skips_the_line() -> None:
    secret = _alnum("sk-ant-", 30)
    assert check_secrets.scan_text(f'x = "{secret}"  # pragma: allowlist secret') == []
    assert check_secrets.scan_text(f'x = "{secret}"')  # without the marker, still flagged


def test_the_repository_itself_is_clean() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
