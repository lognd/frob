---
id: T-2281
title: fleet_status scope-collision check misses tickets whose land is in flight (in-progress
  + no lease is not a lease-recording bug)
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: new repro/regression tests for the land-in-flight collision fix
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'doc closure: scope_lease_collisions''s new land_ticket_ids param needs
    its anchor updated'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_land_in_progress_ticket_with_no_lease_still_collides
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_land_in_progress_ticket_with_no_lease_still_collides
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed while investigating T-2271. T-2271 suspected a lease-RECORDING defect in _sync_cross_worktree_lease/_evidence.py (a ticket driven to in-progress after a scope change while queued, in the same worktree, ends up with no lease). Reproduced that exact sequence directly (tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility::test_scope_change_while_queued_then_start_leases_with_post_change_scope) -- it records correctly, with the post-change scope. No defect there.

The ACTUAL mechanism (also reproduced directly, ::test_local_close_releases_the_lease_before_a_second_worktree_sees_done): frob ticket land's own _land_finalize_and_close transitions the ticket to DONE in the WORKTREE (releasing the shared cross-worktree lease immediately, via _sync_cross_worktree_lease's ordinary from_state-is-IN_PROGRESS release path) BEFORE _land_squash_apply propagates that state to the primary checkout's own tickets/<id>/ticket.md. So for the whole window between a land's local close and its squash-apply reaching root -- which can be minutes under a heavy gate-check pipeline -- a ticket reads state:in-progress from root/main while holding NO shared lease at all. This is correct, intentional lease-release behavior, not a recording bug.

T-2225's scope-collision check (scripts/fleet_status.py, landed as part of T-2225) reads only leases to decide occupancy, so it is blind to this specific window: a ticket whose land is actively running (files genuinely still contended, from a scope-safety point of view, until the merge is durable) reads as unclaimed. T-2264 already built _land_in_progress_for_ticket (src/frob/tickets/_leases.py) for exactly this class of signal (used by lease_staleness_reason's holder-dead check). Consider having fleet_status's collision check ALSO consult _land_in_progress_for_ticket for a ticket with no lease, before reporting it collision-free -- a THIRD signal, not inferring occupancy from ticket state (T-2271's own explicit constraint), which stays intact.

Not urgent: the window is normally short and the coordinator already treats a fresh in-progress ticket as presumptively still someone's active work in practice. Filed as a properly scoped, disclosed follow-up rather than fixed here, since scripts/fleet_status.py is outside T-2271's own declared scope (src/frob/tickets/_evidence.py).