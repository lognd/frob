---
id: T-1408
title: add regression tests for the T-1401 zero-hit ratchet carve-out in write_coverage_lock
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_records_a_genuine_zero
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_small_drop_within_tolerance_not_clamped
designated_repro_test: null
acceptance:
- text: GIVEN a committed lock with a non-zero value for a module WHEN write_coverage_lock
    is called with module_line[module] == 0.0 for that module THEN the written lock
    records 0.0 for that module, not the stale committed value
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_records_a_genuine_zero
- text: GIVEN a committed lock with a non-zero value for a module WHEN write_coverage_lock
    is called with a non-zero value that drops by less than or equal to _LOCK_TOLERANCE
    THEN the ratchet clamp does not fire (unchanged pre-T-1401 behavior)
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_small_drop_within_tolerance_not_clamped
threat: null
component: null
---
T-1401 fixed the frob-coverage.lock.json write_coverage_lock ratchet defect
in src/frob/gates/_coverage.py (a module whose coverage.xml shows exactly
zero hits was being silently clamped back up to a stale committed value).
The fix and its behavior were verified manually and against the existing
suite, but no new pytest regression test could be added in that ticket:
tests/test_gates.py falls under tests/**, which T-1235 held an exclusive
in-progress lease on for the whole of T-1401's work.

Add to tests/test_gates.py::TestCoverageLoad:
- test_write_coverage_lock_zero_hit_module_never_clamped: seed a committed
  lock with a non-zero value for a module, then write_coverage_lock a
  CoverageData whose module_line for that same module is exactly 0.0;
  assert the resulting lock records 0.0, not the stale value (this is the
  literal T-1401 incident: src/frob/__main__.py 81.2 -> 0.0).
- keep test_write_coverage_lock_refuses_downward_ratchet and
  test_write_coverage_lock_allow_decrease_overrides_ratchet as-is (T-1401
  did not change non-zero ratchet behavior); add one assertion or a
  companion test confirming a non-zero small drop is unaffected by the
  new zero-only carve-out (i.e. the carve-out is `new_pct == 0.0` exactly,
  not `new_pct < some threshold`).

Bind these to write_coverage_lock via frob:tests directives in
src/frob/gates/_coverage.py once landed (that file is NOT in this
ticket's scope -- a one-line frob:tests addition there is a trivial
follow-up commit, or fold it into whichever ticket lands this one).