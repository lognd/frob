---
id: T-0751
title: 'frob check --stamp-baseline: chunk or make incremental so it stays under agent
  foreground caps'
state: done
kind: ux
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
- docs/guides/agent-playbook.md
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: add coverage for T-0751's --stamp-baseline --only chunk/merge behavior
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_gate_error_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_records_without_stamping
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
designated_repro_test: null
threat: null
component: null
---
follow-up from T-0627: --stamp-baseline runs the full undelta'd gates pass (same ~110s+ wall time as a bare frob check) and is deliberately NOT refused under FROB_AGENT since it is a legitimate one-shot warm-up step, not a repeatable verification loop -- so it can still stall a dispatched sub-agent the same way T-0627 fixed for plain frob check. T-0627's ticket body named this as option (c) (make --stamp-baseline itself incremental) and left it unbuilt. Needs either: stamp per stage-group chunk and merge, or a documented coordinator-only path (stamp-baseline runs from the coordinator's shell before dispatch, never from an agent's).