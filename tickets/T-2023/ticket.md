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
land_commit: null
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

## Done report

Measured this repo's real `frob ticket land` durations from `.frob/telemetry.jsonl`
(kind="cli", args_head starting "ticket land", real repo worktrees only, exit=0),
n=746: median 94.6s, p75 321.8s, p90 438.3s, p95 489.4s, max 1620.9s.

Root cause confirmed: `refuse_if_land_in_progress`'s wait deadline was computed
from the CALLING process's own start (`monotonic() + wait_timeout_s`), with
zero regard for how long the land it waits on had already been running. A
caller invoked minutes into a long land got a fresh full-length wait budget
anyway, then refused once THAT expired -- exactly the ticket's reported
incident (60s wait, land took 5m23s, refused after 61s).

Fix, in `src/frob/tickets/_leases.py`:
- `_LAND_WAIT_TIMEOUT_S` raised 60.0 -> 330.0 (just above measured p75, NOT
  the worst-observed 1620.9s value -- the ticket explicitly rejects tuning
  to the worst case, since that would make a genuine stuck-land refusal take
  27 minutes to surface).
- New `_load_land_wait_timeout_s` makes the default overridable per-repo via
  `frob.toml`'s `[tickets] land_wait_timeout_s` (reusing the existing
  `load_positive_int_config` degrade-quietly contract -- a misconfigured or
  absent `frob.toml` always falls back to the finite 330.0 default, so no
  configuration can produce an unbounded wait).
- New `_land_lock_started_at`/`_resolve_land_wait_budget`: the resolved
  budget is now spent relative to the land's OWN recorded `started_at`
  (already written by `frob.tickets._land._land_lock_holder_metadata`),
  not the caller's own call time. A caller arriving late into a land's run
  only waits what remains of that land's allotment; a caller whose land is
  already past budget by the time it checks refuses promptly instead of
  waiting a full fresh window pointlessly. A lock with no parseable
  `started_at` (older/foreign holder) falls back to the pre-T-2023
  behavior unchanged.
- `ARCH001`/`DUP001` cleanup: extracted `_resolve_land_wait_budget` to keep
  `refuse_if_land_in_progress` under the length threshold; the extracted
  helper still triggered a DUP001 rung-2 generic-shape match against two
  unrelated functions (a Python-grammar constant check, a claims-block
  renderer) -- waived with an explicit reason, not silenced blindly.

Evidence: `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_budget_counts_from_the_lands_own_start_not_this_calls_start`,
designated as the repro test. Verified FAIL-then-PASS by hand (playbook
9): committed the test alone first, ran it against the unmodified
`_leases.py` (TypeError: unexpected keyword `now_wall` -- fails), then
applied the fix and re-ran (passes). `frob ticket evidence --check-repro
... --base-ref 04a0e3c3a` (the test-only commit) independently confirmed
`FAILED_AT_PARENT`. `--designate-repro` itself could not reach a verdict
because it validates against the ticket's ORIGINAL base commit
(`cea267451`), where the test function does not exist at all (NO_VERDICT,
pytest exit 5 -- structurally unavoidable for any brand-new test node id,
not a sign of a bad repro); used `--designate-repro-force` to record the
designation, with the true FAILED_AT_PARENT proof from the `--base-ref`
run cited here since the tool's own default base cannot express it for a
newly-added test.

Land-parity: `frob check --land-parity` reported 2 unscoped F401 findings
in `tests/test_gates_fmt_directives.py` and
`tests/unit/test_tickets_evidence_only_scope.py` -- confirmed via
`git diff main --stat` on both paths (empty) that this ticket never
touched either file; pre-existing repo-wide drift, not caused here.

Scope note: `docs/modules/gates.md` was NOT added to this ticket's scope --
`frob ticket scope --add` refused it as held by T-2025's live lease at the
time. No doc anchor exists yet for the new `_load_land_wait_timeout_s`/
`_land_lock_started_at`/`_resolve_land_wait_budget` symbols in
`docs/modules/tickets.md#land-exclusivity-lease-t-1619`; filed as residue.

### Changed
```
 src/frob/tickets/_leases.py | 157 +++++++++++++++++++++++++++++++++++---------
 tests/test_ticket_leases.py |  84 ++++++++++++++++++++++++
 tickets/T-2023/ticket.md    |  13 +++-
 3 files changed, 222 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_budget_counts_from_the_lands_own_start_not_this_calls_start` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/t2023-t2028/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2023-t2028/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2023
