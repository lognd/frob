---
id: T-2037
title: T-2022 needs to be reopened -- auto-dropped on the false-drop premise T-2036
  fixed, its two F401 findings are still live
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_gates_fmt_directives.py
- tests/unit/test_tickets_evidence_only_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2036 fixed the path-shape false-drop defect that caused T-2022 to be auto-dropped while its two F401 findings (tests/test_gates_fmt_directives.py, tests/unit/test_tickets_evidence_only_scope.py) were still live. T-2022 itself was not reopened -- its scope does not overlap T-2036's, and the fixing worktree's ticket CLI exposed no reopen verb for a dropped ticket. Fix the two live F401 unused-import findings, or transition T-2022 back to queued/open and let it track them.