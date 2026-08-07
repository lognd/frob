---
id: T-1405
title: update docs/modules/gates.md#public-api for T-1401's write_coverage_lock/load_coverage
  behavior changes
state: done
kind: docs
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:bash -c "grep -q 'zero-hit ratchet' docs/modules/gates.md && grep -q 'unjoined-module'
  docs/modules/gates.md" exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: GIVEN a reader of docs/modules/gates.md#public-api WHEN they read the write_coverage_lock
    entry THEN it documents that a genuine zero-hit module value is never clamped
    to a stale committed value, unconditionally
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: GIVEN a reader of docs/modules/gates.md#public-api WHEN they read the load_coverage
    entry THEN it documents that modules failing to join below the 0.95 threshold
    are enumerated by name in a warning log, not just reported as a fraction
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
T-1401 changed the documented behavior of two public functions in
src/frob/gates/_coverage.py:

- write_coverage_lock: the T-1363 downward ratchet now has an explicit
  carve-out -- a module whose freshly measured value is exactly 0.0 is
  never clamped back to a stale committed value, even with
  allow_decrease=False. Previously any large drop (including a genuine
  zero) was clamped.
- load_coverage: when module_join_fraction falls below 0.95, the specific
  unjoined .py modules are now enumerated in a WARNING log line, not just
  reported as a bare fraction.

docs/modules/gates.md#public-api documents both functions and needs a
matching update (AFFECT001 flagged this in T-1401's own check run, but
docs/** was held by T-1235's concurrent in-progress lease for the whole
of T-1401's work, so the doc could not be updated in the same change --
waived at both call sites in src/frob/gates/_coverage.py with a pointer
to this ticket).

Update docs/modules/gates.md's write_coverage_lock and load_coverage
entries (or their #public-api anchor section) to describe the T-1401
zero-hit ratchet carve-out and the unjoined-module enumeration log.