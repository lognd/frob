---
id: T-2654
title: 'fleet_status: flag an in-progress ticket that is also blocked_by an open blocker'
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: test file for the fleet_status.py fix must be in scope (COV002/SCOPE002)
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_in_progress_with_open_blocker_flagged
- tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_in_progress_with_no_blockers_not_flagged
- tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_in_progress_with_only_terminal_blockers_not_flagged
- tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_queued_ticket_with_open_blocker_not_flagged
- tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_leases_section_flags_blocked_open_lease
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases::test_in_progress_with_open_blocker_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2651 fixed fleet_status's LEASES section being blind to an in-progress
ticket whose lease FILE was pruned after its worktree was removed. T-2651's
own body separately flagged a related but distinct shape worth its own
check: a ticket that is `blocked_by` (has an open blocker) yet is still
`state: in-progress`. It cannot proceed -- any lease it holds is pure
waste, the exact T-2377 shape (blocked nine hours, left in-progress,
holding a write lease the whole time) but detectable WITHOUT waiting for
the worktree to vanish.

Add a check to `scripts/fleet_status.py` (reuse
`in_progress_ticket_scope_leases`'s ledger read plus the existing
`blocked_by` parsing `_parse_ticket_frontmatter_text` already does) that
flags an in-progress ticket whose `blocked_by` still names an open
blocker -- distinct from (and cheaper to detect than) the no-worktree
leak T-2651 already reports, since it does not depend on worktree
liveness at all.
