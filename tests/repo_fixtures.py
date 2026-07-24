"""Builders for the git fixture repositories spec-drift's tests analyze.

Each builder creates a real, self-contained git repository under a caller
supplied directory (a pytest ``tmp_path``), emulating a target repo that
follows the claude-okf-repo-kit convention: Markdown specs under
``docs/specs/``, a ``docs/okf-map.yml`` mapping source globs to governing
documents, and source code the spec governs.

Every fixture commits a ``base`` state, marks it with the ``base`` branch,
then commits a change on ``main`` — so ``--base base`` is the canonical
invocation against a fixture, mirroring ``--base origin/main`` in a real
repository. Builders are deterministic and offline: fixed author identity,
fixed timestamps, no network.

The two fixtures established here mirror the goal's success criteria:

- clean: the change agrees with the governing spec (a log line is added,
  the required approval check stays intact).
- drift: the change silently removes the manager-approval check the
  governing spec requires.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

BASE_REF = "base"

_FIXED_ENV = {
    "GIT_AUTHOR_NAME": "Fixture Author",
    "GIT_AUTHOR_EMAIL": "fixtures@example.invalid",
    "GIT_COMMITTER_NAME": "Fixture Author",
    "GIT_COMMITTER_EMAIL": "fixtures@example.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    # Ignore the machine's git configuration so fixture builds are identical
    # everywhere (no hooksPath, templates, or defaultBranch surprises).
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}

_REFUNDS_SPEC = """\
---
type: Spec
title: Refund processing
description: Contract for issuing refunds, including the approval boundary.
---

# Refund processing

- Refunds at or below 100 USD are issued immediately.
- Refunds above 100 USD require manager approval before they are issued.
- Every refund records the requesting user and amount.
"""

_OKF_MAP = """\
mappings:
  - source: "src/refunds.py"
    docs:
      - "docs/specs/refunds.md"
"""

_REFUNDS_BASE = '''\
"""Refund processing governed by docs/specs/refunds.md."""

APPROVAL_THRESHOLD_USD = 100


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    if amount_usd > APPROVAL_THRESHOLD_USD and not manager_approved:
        raise PermissionError("refunds above the threshold require manager approval")
    return f"refunded {amount_usd} USD to {user}"
'''

_REFUNDS_CLEAN_CHANGE = '''\
"""Refund processing governed by docs/specs/refunds.md."""

import logging

APPROVAL_THRESHOLD_USD = 100

logger = logging.getLogger(__name__)


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    if amount_usd > APPROVAL_THRESHOLD_USD and not manager_approved:
        raise PermissionError("refunds above the threshold require manager approval")
    logger.info("refund issued", extra={"user": user, "amount_usd": amount_usd})
    return f"refunded {amount_usd} USD to {user}"
'''

_REFUNDS_DRIFT_CHANGE = '''\
"""Refund processing governed by docs/specs/refunds.md."""

APPROVAL_THRESHOLD_USD = 100


def issue_refund(user: str, amount_usd: int, manager_approved: bool) -> str:
    return f"refunded {amount_usd} USD to {user}"
'''


@dataclass(frozen=True)
class FixtureRepo:
    """A built fixture repository and the ref its change should be diffed against."""

    path: Path
    base_ref: str


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **_FIXED_ENV},
    )
    return result.stdout


def _write(repo: Path, relative: str, content: str) -> None:
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _write_bytes(repo: Path, relative: str, content: bytes) -> None:
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def _build(root: Path, name: str, changed_source: str) -> FixtureRepo:
    repo = root / name
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", _FIXED_ENV["GIT_AUTHOR_NAME"])
    _git(repo, "config", "user.email", _FIXED_ENV["GIT_AUTHOR_EMAIL"])

    _write(repo, "docs/specs/refunds.md", _REFUNDS_SPEC)
    _write(repo, "docs/okf-map.yml", _OKF_MAP)
    _write(repo, "src/refunds.py", _REFUNDS_BASE)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "Base: refund policy implemented per spec")
    _git(repo, "branch", BASE_REF)

    _write(repo, "src/refunds.py", changed_source)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "Change refund processing")
    return FixtureRepo(path=repo, base_ref=BASE_REF)


def build_clean_fixture(root: Path) -> FixtureRepo:
    """A repo whose change agrees with its governing spec."""
    return _build(root, "clean-repo", _REFUNDS_CLEAN_CHANGE)


def build_drift_fixture(root: Path) -> FixtureRepo:
    """A repo whose change removes the approval check its spec requires."""
    return _build(root, "drift-repo", _REFUNDS_DRIFT_CHANGE)


_PAYMENTS_SPEC = """\
---
type: Spec
title: Payment execution
description: How a payment is executed against the gateway, including retry identity.
---

# Payment execution

A payment is one logical charge against a customer. It may be attempted more
than once — the gateway can time out, the network can fail, the worker can be
restarted — but the customer must be charged exactly once.

## Retry identity

- Every payment carries an `idempotency_key`, assigned when the payment record
  is created and stored on that record.
- Every attempt for one logical payment MUST send that same stored
  `idempotency_key`. Reusing the key is what lets the gateway recognise a retry
  as the same charge rather than a new one.
- A new key MUST NOT be generated per attempt. To the gateway a fresh key is a
  new charge, so a retried payment would debit the customer twice.
- The stored key is never rotated, including after a failed attempt.

## Reporting

- Every attempt records the payment id, the amount, and the outcome.

## Recording execution decisions

This service records architecture decisions as ADRs under `docs/adr/`.
Introducing or changing an execution boundary — a background worker, a queue, a
scheduler, or a new runtime dependency — requires its own accepted ADR before
the change ships. No ADR currently covers executing payments asynchronously.
"""

_PAYMENTS_ADR = """\
---
type: ADR
title: Idempotency key lifecycle for payments
description: The key is minted and persisted before the first gateway call.
status: accepted
---

# Status

Accepted. Binds future work; supersede only via a new ADR.

# Context

The gateway deduplicates by idempotency key. Any attempt that arrives with an
unfamiliar key is treated as a fresh charge, so the identity of a retry is
decided entirely by which key we send.

# Decision

The `idempotency_key` is generated once, when the payment record is created,
and persisted on that record **before** the first gateway request is made.
Every subsequent attempt loads the key from the payment record and sends it
unchanged. No code path may mint a key at attempt time.

# Consequences

A retry is indistinguishable from the original charge to the gateway, so a
duplicate debit is impossible even when an attempt fails after the gateway has
already accepted it.
"""

_PAYMENTS_MAP = """\
mappings:
  - source: "src/payments/**"
    docs:
      - "docs/specs/payment-execution.md"
      - "docs/adr/0002-payment-execution.md"
"""

_RETRY_BASE = '''\
"""Payment retries governed by docs/specs/payment-execution.md."""

MAX_ATTEMPTS = 3


def charge_with_retry(gateway, payment):
    """Attempt a payment, reusing the payment's persisted idempotency key."""
    last_error = None
    for _attempt in range(MAX_ATTEMPTS):
        try:
            return gateway.charge(
                amount=payment.amount,
                idempotency_key=payment.idempotency_key,
            )
        except TimeoutError as error:
            last_error = error
    raise last_error
'''

_RETRY_DRIFTED = '''\
"""Payment retries governed by docs/specs/payment-execution.md."""

import uuid

MAX_ATTEMPTS = 3


def charge_with_retry(gateway, payment):
    """Attempt a payment, tagging each attempt so it can be traced separately."""
    last_error = None
    for _attempt in range(MAX_ATTEMPTS):
        try:
            return gateway.charge(
                amount=payment.amount,
                idempotency_key=str(uuid.uuid4()),
            )
        except TimeoutError as error:
            last_error = error
    raise last_error
'''

_PAYMENTS_WORKER = '''\
"""Background execution for payment retries."""

import queue
import threading

_RETRY_QUEUE: "queue.Queue" = queue.Queue()


def enqueue_retry(payment):
    """Hand a failed payment to the background retry queue."""
    _RETRY_QUEUE.put(payment)


def start_worker(gateway):
    """Drain the retry queue on a background thread."""

    def _drain():
        while True:
            payment = _RETRY_QUEUE.get()
            charge_with_retry(gateway, payment)

    threading.Thread(target=_drain, daemon=True).start()
'''


def build_payments_fixture(root: Path) -> FixtureRepo:
    """A repo whose change breaks retry identity and adds an unrecorded queue.

    Two governed files change in one commit, so one run exercises two
    classifications: `src/payments/retry.py` starts minting a fresh
    idempotency key per attempt, which the spec and the accepted ADR both
    forbid; and `src/payments/worker.py` introduces a background queue, an
    architecture boundary neither document decides. The documents are
    deliberately silent on execution topology so the queue is genuinely
    undecided rather than contradicted.
    """
    repo = root / "payments-repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", _FIXED_ENV["GIT_AUTHOR_NAME"])
    _git(repo, "config", "user.email", _FIXED_ENV["GIT_AUTHOR_EMAIL"])

    _write(repo, "docs/specs/payment-execution.md", _PAYMENTS_SPEC)
    _write(repo, "docs/adr/0002-payment-execution.md", _PAYMENTS_ADR)
    _write(repo, "docs/okf-map.yml", _PAYMENTS_MAP)
    _write(repo, "src/payments/retry.py", _RETRY_BASE)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "Base: retries reuse the persisted idempotency key")
    _git(repo, "branch", BASE_REF)

    _write(repo, "src/payments/retry.py", _RETRY_DRIFTED)
    _write(repo, "src/payments/worker.py", _PAYMENTS_WORKER)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "Move payment retries onto a background worker")
    return FixtureRepo(path=repo, base_ref=BASE_REF)


def build_mixed_fixture(root: Path) -> FixtureRepo:
    """A repo exercising every change kind and every exclusion reason.

    Base -> HEAD introduces: a modified governed file, a rename, a delete, an
    added file with no governing document, plus a ``.env`` file, a private-key
    credential file, a binary file, and a force-added file matching
    ``.gitignore`` — the four exclusions. The ``.env`` is also gitignored, so it
    proves the env-file reason wins over the ignored reason.
    """
    repo = root / "mixed-repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", _FIXED_ENV["GIT_AUTHOR_NAME"])
    _git(repo, "config", "user.email", _FIXED_ENV["GIT_AUTHOR_EMAIL"])

    _write(repo, "docs/specs/refunds.md", _REFUNDS_SPEC)
    _write(repo, "docs/okf-map.yml", _OKF_MAP)
    _write(repo, "src/refunds.py", _REFUNDS_BASE)
    _write(repo, "src/oldname.py", "SHARED = 1\n")
    _write(repo, "src/legacy.py", "LEGACY = 1\n")
    _write(repo, ".gitignore", "build/\n.env\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "Base state")
    _git(repo, "branch", BASE_REF)

    _write(repo, "src/refunds.py", _REFUNDS_DRIFT_CHANGE)  # modified, governed
    (repo / "src" / "oldname.py").unlink()
    _write(repo, "src/newname.py", "SHARED = 1\n")  # rename (identical content)
    (repo / "src" / "legacy.py").unlink()  # delete
    _write(repo, "src/newfeature.py", "def feature() -> int:\n    return 42\n")  # added, unmapped
    _write(repo, ".env", "SECRET=shhh\n")  # env file (also gitignored)
    # A fake key body proves credential exclusion; not a real secret.
    _write(repo, "deploy/server.pem", "-----BEGIN PRIVATE KEY-----\n")  # pragma: allowlist secret
    _write_bytes(repo, "assets/logo.bin", b"\x89PNG\r\n\x00\x00binary")  # binary
    _write(repo, "build/generated.txt", "generated output\n")  # ignored (force-added)
    _git(repo, "add", "-A")
    _git(repo, "add", "-f", ".env", "build/generated.txt")
    _git(repo, "commit", "-q", "-m", "Mixed changes")
    return FixtureRepo(path=repo, base_ref=BASE_REF)
