---
id: T-1886
title: 'test_waive004_removes_stale_waiver_on_a_full_unscoped_run: proportional mass-invalidation
  guard blocks single-waiver fixtures'
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates.py
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4709: preserve proportional-min-live-count rationale trimmed from _fix_engine_sync.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1077
  new_length: 1679
evidence:
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_waive004_removes_stale_waiver_on_a_full_unscoped_run
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Pre-existing, found while working T-1870 (unrelated): tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_waive004_removes_stale_waiver_on_a_full_unscoped_run fails on main (verified directly, before any T-1870 edits): 'assert 0 == 1'. Root cause visible in the log: '1 frob:waive REF001 directives went stale in one run (>= 5 threshold) -- treating as a degraded/under-reporting run'. The T-1620 PROPORTIONAL mass-invalidation check in _mass_invalidation_rules (src/frob/gates/_fix_engine_sync.py) fires whenever ALL of a rule's live waivers go stale in one run, regardless of count -- this test's fixture repo has exactly ONE live REF001 waiver total, so 1-of-1 always trips the proportional guard and fix_waive004_stale_waiver always refuses to delete it, structurally, no matter how genuinely dead the waiver is. Either the test fixture needs a second, live REF001 site so the ratio is not 100%, or the proportional check needs a minimum-sample-size floor (mirroring _DEFLATION_MIN_KNOWN_MODULES-style precedents elsewhere in this repo) before it can fire.


T-4709 follow-up (condensed from _WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT's
docstring in src/frob/gates/_fix_engine_sync.py, trimmed for
DOCARCH002's 12-line cap): without a floor, `fix_waive004_stale_waiver`
would be structurally unable to ever delete a lone dead waiver for a
low-traffic rule -- not a rare edge case, since a repo with exactly one
live waiver for some rule is an entirely ordinary state, not itself a
degradation signal. Chosen at 2 so the guard keeps its full bite the
moment there is ANY sample size to reason about proportionally --
2-of-2 and up still trip it exactly as before.