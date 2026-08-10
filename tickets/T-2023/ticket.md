---
id: T-2023
title: T-1961s land-wait timeout is calibrated below the observed land duration, so
  ledger verbs now cost 60s and refuse anyway
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: test file for the wait-timeout fix's failing-first repro test
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_budget_counts_from_the_lands_own_start_not_this_calls_start
designated_repro_test: tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_budget_counts_from_the_lands_own_start_not_this_calls_start
threat: null
component: null
anchor: false
anchor_reason: null
---
FOLLOW-UP TO T-1961, NOT A DUPLICATE AND NOT A CRITICISM OF ITS FIX.
T-1961's `refuse_if_land_in_progress` bounded-wait works exactly as designed:
it waits, logs once, then refuses LOUDLY rather than hanging. That shape is
correct and must be preserved. The defect is only the CALIBRATION of the
constant.

MEASURED 2026-08-10, immediately after T-1961 landed (`2066bc189`):

    $ time uv run frob ticket drop T-1971 --reason "..."
    WARNING: ... waiting for in-flight land to finish (up to 60s) before proceeding...
    WARNING: ... in-flight land did not finish within 60s, refusing rather than waiting indefinitely
    ERROR: ticket drop: refused -- LandInProgress
    real  1m1.808s

`_LAND_WAIT_TIMEOUT_S = 60.0` (`src/frob/tickets/_leases.py:144`) is set well
below the observed duration of the thing it waits for. A single land in this
repo was measured at 5m23s wall clock (`ps -eo etime` on
`frob ticket land T-1943`), and under 5-6 agent dispatch lands are
near-continuous, frequently 2-3 concurrent. So the wait expires roughly 1/5
of the way into a typical land and the caller refuses anyway -- now costing
61 seconds instead of failing instantly.

NET EFFECT: for the coordinator's actual workload the fix converts an
instant refusal into a 60-second-then-refusal. It is a strict improvement
for short lands and a regression in latency for long ones. Filing a single
ticket still required a background retry loop AFTER this landed.

## Do not fix it this way
- Do NOT simply raise the constant to cover the worst observed land. A fixed
  timeout large enough for a 9-minute land makes every genuine failure take
  9 minutes to surface, which is worse than refusing.
- Do NOT remove the bound and wait indefinitely. T-1961's own ticket
  explicitly rejected this: an unbounded wait turns a visible refusal into a
  hang, which becomes the 540s land guard and killed-land dirty-root failure
  that T-1963 had to clean up.
- Do NOT make the caller retry in a loop internally. That is the same
  unbounded wait wearing a disguise, and it hides contention from the
  operator instead of reporting it.
- Do NOT tune this by feel. Measure real land durations first (`ps -eo
  etime,cmd` sampled against live `frob ticket land` processes) and state the
  distribution in the Done report.

## Fix directions worth weighing (pick with evidence, do not implement all)
- Make the timeout configurable via `frob.toml` so a heavily-parallel repo
  can raise it without recompiling a constant, defaulting to today's value.
- Scale the wait to the OBSERVED land: the land writes its own start time
  (`land.lock` already carries `started_at`), so a waiter can compute how
  long this land has actually been running and wait proportionally rather
  than blindly.
- Make the refusal actionable: report which ticket holds it, how long it has
  been running, and the queue depth, so the caller can decide rather than
  guess.

## Acceptance criteria
1. A test that FAILS FIRST: simulate a land lasting longer than the current
   default and assert the ledger verb refuses today; then assert the new
   behavior completes (or refuses with the improved, actionable message).
2. Report the MEASURED distribution of land durations in this repo used to
   justify whatever value or policy is chosen -- no unmeasured constants.
3. An unbounded hang must remain impossible; assert an upper bound exists in
   every configuration, including a misconfigured `frob.toml`.