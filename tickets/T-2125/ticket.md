---
id: T-2125
title: 'T-2106 residue: doable still exceeds 540s in the SHARED ROOT after the sweep-budget
  fix (86.5s was measured in a worktree); the sweep line is gone and the new bottleneck
  is unidentified'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_unlanded.py
- tests/unit/test_unlanded_branch_work.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_doable.py
  reason: the actual hotspot per PYTHONFAULTHANDLER stack sample is _unlanded.py::_ticket_state_on_main,
    a per-(branch,ticket) git show spawn -- not _doable.py, which only renders the
    summary
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/tickets/_unlanded.py
  reason: the actual hotspot per PYTHONFAULTHANDLER stack sample is _unlanded.py::_ticket_state_on_main,
    a per-(branch,ticket) git show spawn -- not _doable.py, which only renders the
    summary
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/unit/test_unlanded_branch_work.py
  reason: the actual hotspot per PYTHONFAULTHANDLER stack sample is _unlanded.py::_ticket_state_on_main,
    a per-(branch,ticket) git show spawn -- not _doable.py, which only renders the
    summary
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_confirmed_leak_shape_done_report_plus_in_progress
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_findings_for_one_branch_matches_the_aggregate
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkMainStateSpawnScaling::test_main_state_resolution_does_not_scale_with_branch_times_ticket
designated_repro_test: tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkMainStateSpawnScaling::test_main_state_resolution_does_not_scale_with_branch_times_ticket
threat: null
component: null
anchor: false
anchor_reason: null
---
