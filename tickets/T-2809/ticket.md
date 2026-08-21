---
id: T-2809
title: 'land deadline guard has a load feedback loop: contended stage timings inflate
  estimated_work_s until every land declines, exactly when the fleet is busiest'
state: done
kind: bug
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/_check_chunking.py
- tests/unit/test_check_budget.py
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check_budget.py
  reason: evidence tests + doc update for the new sample-window derivation
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/commands/check.md
  reason: evidence tests + doc update for the new sample-window derivation
  actor: logan
  at: '2026-08-21'
evidence:
- tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_contended_sample_does_not_inflate_the_estimate
- tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_genuine_slowdown_still_raises_the_estimate
- tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_group_with_no_sample_window_falls_back_to_ema
- tests/unit/test_check_budget.py::TestBudgetTimingSampleWindow::test_appends_and_caps_window
- tests/unit/test_check_budget.py::TestBudgetTimingSampleWindow::test_load_missing_file_returns_empty
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## The loop

`_resolve_land_lock_wait_budget_s` (T-2774) bounds a land's lock wait as
`min(_LAND_LOCK_TIMEOUT_S, deadline - estimated_work_s)`, where
`estimated_work_s` comes from `_derive_post_land_sweep_budget_s` reading
`.frob/check-budget-timing.json` (stage sum x 1.5).

Those stage timings are RE-RECORDED by every check run, including runs made
under heavy fleet load. So:

    fleet load rises
      -> recorded stage timings inflate
      -> estimated_work_s inflates
      -> deadline - estimated_work_s goes negative
      -> EVERY land declines early, immediately
      -> agents retry, adding more load

The guard becomes maximally restrictive exactly when the fleet is busiest,
which is when landing matters most.

## Measured 2026-08-21, same repo, same day

    estimated_work_s = 300    (measured ~03:00, quiet box)
    estimated_work_s = 426    (measured ~05:55, load ~8)
    estimated_work_s = 570-608 (observed by an agent during LOAD 16-25)

Current file contents at the 426 reading:

    gates-fast 87.65, gates-native 46.09, gates-security 73.54,
    lint 1.66, static 75.64   -> sum 284.58 x 1.5 = 426.87

With the fleet-standard `FROB_LAND_DEADLINE_S=540`:

    est 300 -> wait ceiling 240s   ok
    est 426 -> wait ceiling 114s   tight but workable
    est 590 -> NEGATIVE            refuse-always

An agent working T-2359 batch 11 hit exactly this: its land declined early
twice at the 540 default, and only completed after bumping to
`FROB_LAND_DEADLINE_S=595` with `timeout 598`.

## Why the naive fixes are wrong

- Raising the fleet deadline is not available. The shell cap is 540 and the
  harness ceiling is 600; 595/598 is already scraping it. There is no
  headroom to absorb a 600s estimate.
- Ignoring the estimate reintroduces T-2774's original bug: a land that
  cannot finish starts anyway and is SIGKILLed mid-work, stranding the
  ticket in-progress with no diagnostic.
- Simply clamping the estimate hides a real signal. When a land genuinely
  cannot fit in the budget, refusing IS correct.

The defect is not the refusal. It is that the ESTIMATE is polluted by
contention, so it no longer describes what an uncontended land would cost.

## Required shape

`estimated_work_s` should approximate the cost of THIS land's own work, not
the cost of a check that happened to run while five other agents were
saturating the box.

Directions to weigh, measure before choosing:
- Record timings with a contention marker (load / concurrent-check count at
  measurement time) and derive the estimate from the least-contended recent
  samples rather than the most recent one.
- Keep a rolling floor (e.g. minimum over the last N runs) instead of a
  single latest reading, since contention can only inflate a timing, never
  deflate it below the true cost.
- Measure CPU time rather than wall-clock for the stage timings, which is
  far less sensitive to competing processes.

Whatever is chosen must still track genuine repo growth -- the original
T-2715 defect was a hardcoded budget that never grew with the codebase, and
a fix that pins the estimate reintroduces it.

## Positive controls, both directions

- Timings recorded under heavy load must NOT inflate the estimate enough to
  refuse a land that would genuinely fit. Plant this by recording a
  contended timing set and asserting the estimate stays near the
  uncontended value.
- A genuine increase in check cost (real repo growth) MUST still raise the
  estimate. Without this control the fix silently recreates T-2715.
- A land that genuinely cannot fit the declared deadline must STILL decline
  early rather than starting and being killed (T-2774 must not regress).

## Related

T-2774 introduced the deadline guard and is correct. T-2715 fixed the
hardcoded-budget predecessor. T-2790/T-2806 are reducing the underlying
check cost, which shrinks this problem but does not remove the loop.