---
id: T-2581
title: 'M6: REL001 extension -- refuse release cut with open milestone-X tickets'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: high
blocked_by:
- T-2574
- T-2576
parent: T-2573
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: wire _release_open_milestone_violations into release_gate
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_gates.py
  reason: TestReleaseOpenMilestoneViolations evidence for REL001 M6
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_gates.py
  reason: TestReleaseOpenMilestoneViolations evidence for REL001 M6
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_open_ticket_in_cut_milestone_refuses
- tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_open_ticket_in_other_milestone_does_not_refuse
- tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_terminal_ticket_in_cut_milestone_does_not_refuse
- tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_no_open_tickets_in_milestone_succeeds
- tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_names_every_blocking_ticket
- tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_queue_unavailable_does_not_crash
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Extend REL001 (src/frob/gates/_debt_deprecated.py, `release_gate`/its
callers -- REL001 currently refuses a release over open `frob:debt` and
open `frob:deprecated`; verify the exact call shape before extending it,
same file already carries two REL001-reporting checks side by side as a
precedent for how to add a third finding kind under the same rule id).

New rule: refuse to cut release X while OPEN tickets carry milestone X.
Must name WHICH tickets block the cut in the refusal message, not just
that something does -- follow the existing REL001 finding shape (each
finding already names the specific edge/ticket that blocks; match that
precedent, do not report a bare count).

Depends on M1 (T-2574, milestone field) and M2 (T-2576, MILE003 +
backfill -- without every open ticket actually carrying a milestone,
this check cannot meaningfully compare "milestone X" against the
release version being cut). Does not depend on M3/M4/M4b/M5.