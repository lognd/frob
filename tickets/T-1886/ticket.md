---
id: T-1886
title: 'test_waive004_removes_stale_waiver_on_a_full_unscoped_run: proportional mass-invalidation
  guard blocks single-waiver fixtures'
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_gates.py
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Pre-existing, found while working T-1870 (unrelated): tests/test_gates.py::TestFixEngineTierABatch2::test_waive004_removes_stale_waiver_on_a_full_unscoped_run fails on main (verified directly, before any T-1870 edits): 'assert 0 == 1'. Root cause visible in the log: '1 frob:waive REF001 directives went stale in one run (>= 5 threshold) -- treating as a degraded/under-reporting run'. The T-1620 PROPORTIONAL mass-invalidation check in _mass_invalidation_rules (src/frob/gates/_fix_engine_sync.py) fires whenever ALL of a rule's live waivers go stale in one run, regardless of count -- this test's fixture repo has exactly ONE live REF001 waiver total, so 1-of-1 always trips the proportional guard and fix_waive004_stale_waiver always refuses to delete it, structurally, no matter how genuinely dead the waiver is. Either the test fixture needs a second, live REF001 site so the ratio is not 100%, or the proportional check needs a minimum-sample-size floor (mirroring _DEFLATION_MIN_KNOWN_MODULES-style precedents elsewhere in this repo) before it can fire.