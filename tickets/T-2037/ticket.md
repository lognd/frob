---
id: T-2037
title: T-2022 needs to be reopened -- auto-dropped on the false-drop premise T-2036
  fixed, its two F401 findings are still live
state: dropped
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
land_commit: null
---
T-2036 fixed the path-shape false-drop defect that caused T-2022 to be auto-dropped while its two F401 findings (tests/test_gates_fmt_directives.py, tests/unit/test_tickets_evidence_only_scope.py) were still live. T-2022 itself was not reopened -- its scope does not overlap T-2036's, and the fixing worktree's ticket CLI exposed no reopen verb for a dropped ticket. Fix the two live F401 unused-import findings, or transition T-2022 back to queued/open and let it track them.

## Drop reason
- 2026-08-10: Premise resolved before the ticket was worked. T-2037 asked to reopen T-2022 because its two F401 findings were still live after the false auto-drop. Both were fixed directly on main at f28ab6590 (unused imports _fmt_marker_entries_with_indents and pytest removed; 49 tests still pass) because they were holding the verify quarantine RAISED, which forces fully-synchronous verification on every land (T-1693) and was blocking the whole fleet from publishing. Confirmed absent from the current tree and from the unscoped floor measurement. Nothing left to reopen T-2022 for; the false-drop mechanism itself is fixed by T-2036, and the surfacing gap that let it cost an hour is T-2049.
