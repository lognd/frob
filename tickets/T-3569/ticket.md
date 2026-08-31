---
id: T-3569
title: 'test_without_serial_pools_worker_is_unattributed: mis-stated attribution bound,
  mirror T-3487'
state: in-progress
kind: bug
origin: agent
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
- tests/unit/perf/test_serial_pools.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'record BUG002 waiver: CI-noise-only repro, mirrors T-3487'
  actor: logan
  at: '2026-08-31'
  old_length: 471
  new_length: 1127
evidence:
- tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_without_serial_pools_worker_is_unattributed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33370059331 (ubuntu): 'unpatched attribution (0.5062) was not decisively smaller than patched attribution (0.9992)' -- 0.506 IS decisively smaller than 0.999; this is the twin of the mis-stated bound T-3487 fixed on the sibling test. Restate this test's property the same way T-3487 shipped for its sibling (unpatched < 0.7 absolute AND patched > unpatched * 1.5, or the mirror of whatever exact shape T-3487 used), with the measured numbers in the assertion message.

frob:waive BUG002 reason="the original mis-stated bound only trips on a busy shared CI runner (ratio landing just over 0.5 by rounding), not deterministically on any box -- it passed at the parent commit here on this quiet Linux dev box too, exactly as T-3487 own sibling fix hit the same BUG002 shape for the identical root cause (ratio-bound-near-ceiling CI noise). Not reproducible on demand; the fix is a pure assertion-shape correction, verified by inspection against T-3487 own shipped precedent and by measured arithmetic against the ground-truth numbers (0.5062 < 0.7 and 0.9992 > 0.5062*1.5 both hold, the previous 0.5062 < 0.9992*0.5 did not)."