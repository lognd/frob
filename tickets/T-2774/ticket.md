---
id: T-2774
title: a contended land is SIGKILLed mid-work because the 500s lock-wait guard bounds
  only the wait, not wait+work against the caller's cap
state: queued
kind: bug
origin: agent
created: '2026-08-21'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured failure

2026-08-21. T-2753's land ran 540s and was SIGKILLed by its caller's
`timeout 540` wrapper. Result: no land commit, ticket stranded at
`state: in-progress`, `land_commit: null`, and NO diagnostic of any kind --
the caller saw only exit 143. Roughly 9 minutes of fleet time bought
nothing. The same thing happened to T-2762 and T-2359 earlier the same
hour; T-2762 then succeeded UNCHANGED on a retry that ran alone, which is
the proof that the work was fine and only the contention killed it.

## Root cause

`_LAND_LOCK_TIMEOUT_S = 500.0` (`src/frob/tickets/_land.py:246`) bounds the
lock WAIT only. Its own comment states it was chosen to fire "with margin
before an outer `timeout 540` would ever need to intervene" -- correct
reasoning about the wait in isolation, and wrong about the total.

The outer cap covers WAIT + WORK, not the wait alone. After acquiring the
lock a land still runs its own `frob check` (~274s unbudgeted, measured) plus
merge/finalize. So:

    wait 300s + work 300s = 600s > 540s cap  -> SIGKILL mid-land

while neither half alone ever trips the 500s guard. The bounded-wait
refusal T-1515 added is therefore unreachable in exactly the case it was
written for: the process is killed before it can decline.

Measured evidence of the two states being indistinguishable from outside:
the land HOLDING the lock had a `frob check` child at 104% CPU, while the
land WAITING showed 63s CPU across 341s elapsed (~18%, parked). Both report
identically as "in flight".

## Why this is worse than slow

A killed land is not a no-op. It leaves the ticket `in-progress` holding its
scope lease, so the file set stays locked against the rest of the fleet
until an agent notices and retries. And it fails SILENTLY -- exit 143 with
no message is precisely the silent-zero class this repo treats as its
dominant bug (epic T-2391): "could not complete" renders as "nothing
happened".

## Required shape

The land must refuse EARLY when its remaining budget cannot cover a land,
instead of starting work it provably cannot finish.

- Let the caller declare its wall-clock budget (env var, e.g.
  `FROB_LAND_DEADLINE_S`, and/or an explicit flag). Absent a declaration,
  behavior must not regress.
- Bound the lock wait by `deadline - estimated_work_s` rather than a flat
  500s. Derive `estimated_work_s` from the timings frob already records --
  `.frob/check-budget-timing.json` is already consumed by
  `_derive_post_land_sweep_budget_s` in `src/frob/app/_check_chunking.py`.
  Reuse that derivation; do NOT add a second hardcoded estimate. Two homes
  for one number desync, and this repo has already been bitten by exactly
  that (`_TRUE_COUNT_BUDGET_S` drifting from its twin).
- If the remaining budget cannot cover a land, return
  `Err(LandError.LandLockTimeout)` (or a new, distinct variant) IMMEDIATELY,
  naming the holder, the remaining budget, and the estimated work time.
  A caller must be able to tell "declined, retry when free" apart from
  "died mid-land", which today it cannot.
- Errors a caller must handle are typani `Result` values, per repo rule --
  not a bare exception.

## Positive controls, both directions

- A land whose remaining budget cannot cover the work REFUSES immediately
  with the typed error, and leaves the ticket's state UNCHANGED (not
  in-progress-but-dead).
- A land with ample budget and a free lock still proceeds exactly as today
  -- the frob repo's own normal land path must be unaffected. Without this
  case the fix is indistinguishable from disabling landing.
- A land that waits a SHORT time and then acquires the lock with budget to
  spare still completes. The fix must not turn every contended land into a
  refusal.
- With no `FROB_LAND_DEADLINE_S` declared, behavior matches today's.

## Note

Do NOT "fix" this by raising the outer timeout. The harness ceiling is 600s,
so a larger wrapper value just moves the kill. Reducing concurrency is a
mitigation the coordinator already applies by hand; this ticket is the
structural half, so that a land which cannot finish says so instead of
dying.
