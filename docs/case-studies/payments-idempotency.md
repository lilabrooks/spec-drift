---
title: Case study — a payment retry that would double-charge
type: Case study
description: The worked example, built as a real fixture and verified against a live provider, including the run where a prediction failed and what that exposed.
status: current
date: 2026-07-24
owner: Lila Brooks
deciders: [Lila Brooks]
tags: [case-study, validation, drift, decision-required]
---

# Case study — a payment retry that would double-charge

The worked example for `spec-drift`, built as a real fixture
(`build_payments_fixture`) and run against a live provider. Every output below
is captured from an actual run; nothing is illustrative.

## The change

A payment service requires that **every attempt for one logical payment reuses
the key stored on the payment record** — the spec says so, and an accepted ADR
decides that the key is minted and persisted before the first gateway call. Both
documents govern `src/payments/**` through `docs/okf-map.yml`.

A developer then moves retries onto a background worker:

```diff
             return gateway.charge(
                 amount=payment.amount,
-                idempotency_key=payment.idempotency_key,
+                idempotency_key=str(uuid.uuid4()),
             )
```

The code is valid. Unit tests pass — the gateway is mocked, and a mock does not
care which key it receives. Lint, typing, and secret scanning stay green. And
every retry now looks to the payment provider like a brand-new charge, so one
timeout becomes two debits on a customer's card.

This is the gap the tool is for: not invalid code, but valid code that no longer
does what the documentation says it does.

## What `spec-drift` reports

Captured from `spec-drift check --base base --provider anthropic`:

```
drift              src/payments/retry.py  Each retry attempt mints a fresh idempotency key instead of reusing the persisted one, contradicting the accepted ADR and spec that forbid minting keys at attempt time.  [source src/payments/retry.py:15; doc docs/adr/0002-payment-execution.md:20]
decision-required  src/payments/worker.py  Introduces a background worker and retry queue execution topology, but no ADR covers asynchronous payment execution as required.  [source src/payments/worker.py:22; doc docs/specs/payment-execution.md:31]

1 drift, 1 decision-required (exit 1)
```

Two classifications from one change set, and `exit 1` stops the merge.

Every citation was checked against the file rather than taken on trust:

| Citation | What is actually on that line |
| --- | --- |
| `retry.py:15` | `idempotency_key=str(uuid.uuid4()),` — the offending line itself |
| `0002-payment-execution.md:20` | "The `idempotency_key` is generated once, when the payment record is created," |
| `worker.py:22` | `threading.Thread(target=_drain, daemon=True).start()` |
| `payment-execution.md:31` | "Introducing or changing an execution boundary — a background worker, a queue, a…" |

Both source lines fall inside the diff's hunks, so each points at something the
change actually did.

## The first run failed, and that was the useful part

The `decision-required` half was a **prediction**, and the first live run
disproved it. Worse, it disproved it inconsistently — two runs of the same input:

| Run | `worker.py` verdict |
| --- | --- |
| 1 | `insufficient-evidence` — "key handling is not shown, so it cannot be judged" |
| 2 | `clean` — "consistent with the spec and ADR" |

Neither verdict was unreasonable. The governing documents covered key handling,
the worker did not touch key handling, and — the actual defect — **a queue was
not on the list of boundaries the prompt asked the model to watch for.** The
enumeration read *dependency, persistence, auth, public API, deployment*, while
this project's own decision policy has always included **cache/queue/worker**.
The tool was asking for a judgment while withholding the criterion.

Two changes followed, and the run above is from after both:

- The prompt's boundary list now matches the project's decision policy
  ([ADR 0006](../adr/0006-decision-required-boundaries.md)), with a test pinning
  the terms so it cannot narrow again unnoticed.
- The fixture's spec gained the convention that execution boundaries are recorded
  as ADRs, and states that none covers asynchronous payments — so the queue is
  *undecided*, which is what `decision-required` means, rather than *forbidden*,
  which would be `drift`.

## What the deterministic test does and does not prove

`tests/test_payments_example.py` drives this fixture through the shipped
`replay` provider, so the mapping, diff loading, reply validation, citation
checking, and exit code are asserted offline on every run. That proves the
**pipeline**: a reply of this shape survives validation and renders as shown.

It does not prove the **judgment** — replay supplies the verdicts. Only the live
run above speaks to what a model concludes, which is exactly why the prediction
that failed could fail: the deterministic test was green the whole time.

## Limits, stated plainly

- **Diff-driven.** Only the change is judged. A pre-existing double-charge bug
  that no commit touches will not be found.
- **Map-gated.** `src/payments/**` must point at those documents. Unmapped code
  is reported as `unmapped`, not judged.
- **Not deterministic across runs.** The two contradictory verdicts above are the
  honest evidence for that. A verdict on ambiguous input is a judgment, not a
  measurement, which is why every finding carries citations a reviewer can check.
