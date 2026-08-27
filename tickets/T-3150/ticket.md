---
id: T-3150
title: Coordinator lease fallback scan misses live worktree with removed lease file
  (T-3140 item 7)
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: scripts/
  reason: 'narrowed: only the fallback-scan function (likely scripts/fleet_status.py)
    needs investigation, not the whole scripts/ tree'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: 'narrowed: only the fallback-scan function (likely scripts/fleet_status.py)
    needs investigation, not the whole scripts/ tree'
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
tests/unit/test_coordinator_scripts.py::
TestInProgressTicketScopeLeasesLiveGit::
test_live_worktree_with_lease_file_removed_is_not_leaked fails:
expected a live worktree with an unlanded commit (no lease file) to
resolve via the coordinator's fallback scan (leaked=False, worktree=
't-2583'); got leaked=True, worktree=None instead. The fallback scan
(scripts/fleet_status.py or wherever `in_progress_ticket_scope_leases`
lives, production script, out of T-3140's declared scope) appears not
to find the live worktree any more. MEASURED (T-3140 triage): reproduces
byte-for-byte with real git state (a real worktree, a real commit
touching the ticket's declared scope, an empty leases directory) --
looks like a genuine regression in the fallback scan, not test
staleness.

## Plan
Step through the fallback scan against this exact fixture shape (real
git worktree + no lease file) to find why it no longer resolves the
live worktree, and fix it with the existing test as repro (confirm it
fails at this ticket's parent commit before fixing).
