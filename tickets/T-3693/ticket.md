---
id: T-3693
title: fix TestTimingDebug flaky elapsed<60s assertion (blocks CI floor)
state: done
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_check_admission.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: add BUG002 waiver
  actor: logan
  at: '2026-09-02'
  old_length: 940
  new_length: 1361
evidence:
- tests/unit/test_check_admission.py::TestTimingDebug::test_mark_prints_breadcrumb_when_enabled
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
test_mark_prints_breadcrumb_when_enabled (T-3689) asserts 0.0 <= elapsed
< 60.0 against _timing_mark's printed elapsed-since-_TIMING_PROCESS_START.
_TIMING_PROCESS_START is captured at frob.check's MODULE IMPORT time; in
a fresh diag process that's ~0.6s, but inside the long-lived pytest suite
process the module was imported many minutes earlier, so the assertion
fails deterministically once the suite has run long enough (confirmed:
908.288s on ubuntu, 1534.019s on macOS, run 33625622797) -- not flaky,
guaranteed. This is currently the single thing blocking ubuntu from
going green (the Test step fails before the frob-check self-gate step
even runs).

Fix: monkeypatch check_mod._TIMING_PROCESS_START to a known-recent value
at the top of this test, matching the sibling test
test_mark_elapsed_grows_with_process_start_offset's own existing pattern
(which already does this correctly and was unaffected).

References: T-3689, T-3692.



frob:waive BUG002 reason="the defect is wall-clock-process-age-dependent (elapsed since frob.check module import exceeding 60s), not reproducible by a single fast repro-check invocation at the parent commit -- reproduced instead by directly aging _TIMING_PROCESS_START and observing the print (see Done report); a repro test that sleeps 60+s to trigger it for real is not a reasonable addition to this unit test file"