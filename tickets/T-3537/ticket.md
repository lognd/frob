---
id: T-3537
title: 'macOS: frob_core GIL must-fire wall bound too tight for the CI runner'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_frob_core_gil.py
- tests/unit/strata/test_strata_core_gil.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record macOS-only BUG002 waiver
  actor: logan
  at: '2026-08-31'
  old_length: 0
  new_length: 465
evidence:
- tests/unit/test_frob_core_gil.py::TestTimeoutFiresDuringLongNativeCall::test_timeout_fires_during_near_duplicate_indices
- tests/unit/strata/test_strata_core_gil.py::TestTimeoutFiresDuringLongNativeCall::test_timeout_fires_during_worst_age
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 8d9b6629bc09f6f2c207085cdb59ac7aacdcb878
---
frob:waive BUG002 reason="macOS-only defect verified from CI run 33353658750 job 99371615032: the preemption mechanism works (Timeout banner printed), only the wall bound was too tight for the slow macOS runner (measured 7.006s > 5.0s). The property restated (timeout fired AND call did not run to completion) with a 30s bound is a pure loosening -- it does not add coverage that could fail-then-pass on this Linux dev box, which never showed the tight bound trip."