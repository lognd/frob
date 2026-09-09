---
id: T-draft-858a1bad
title: T-0843 archive live-lease guard defeated by T-4172 stale-lease reconciliation
  for just-closed tickets
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_archive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: populate body dropped during ticket new (empty backtick substitution)
  actor: logan
  at: '2026-09-09'
  old_length: 0
  new_length: 2774
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4066.

Repro (deterministic, no xdist needed): in a fresh v2-mode repo, create+start+close a ticket (e.g. T-0001), then write a live lease record for T-0001 pointing at the same worktree/root, then call archive()/archive_v2(). Expected (T-0843's own contract, tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal and ::test_refuses_without_force_when_a_live_lease_exists): archive refuses (or requires --force) because the ticket being archived still holds a live cross-worktree lease. Actual: read_all_leases() now logs "T-0001 lease's ticket has already finished on this ledger -- stale lease at .../frob-leases/T-0001.json reconciled against ticket state and unlinked (T-4172)" and UNLINKS the lease before archive's own guard (_refuse_archive_if_leased) ever sees it, so read_all_leases() returns () and the guard silently no-ops -- archive proceeds with no refusal and no --force required.

This is T-4172's own lease-reconciliation logic (attributed in the log line itself) treating "ticket already DONE/DROPPED on the ledger" as sufficient proof a lease is stale -- but T-0843's whole guard exists PRECISELY for the case where a ticket has just transitioned to done/dropped while a lease from that same close operation (or a sibling worktree's) is still live; reconciling it away on ledger-state alone defeats T-0843's live-lease refusal for exactly the scenario it was built to catch (T-0753's field-incident risk: archiving now would risk reverting the ticket's start/evidence/acceptance on next restore).

MUST-FIRE: test_force_overrides_the_live_lease_refusal and test_refuses_without_force_when_a_live_lease_exists (tests/test_ticket_runner_archive_force.py) both fail deterministically against current main plus T-4172's in-flight change (verified locally, 100% repro, not load-sensitive).

Likely fix direction (T-4172 owns _leases.py, verify against its own acceptance criteria before changing): the reconciliation should not unlink a lease purely because the LEDGER already reads done/dropped -- that is exactly the state a lease recorded by the closing operation itself is expected to be in while still live. Determine whether T-4172 intended this interaction; if not, narrow the reconciliation (e.g. only unlink when the lease's OWN worktree is also confirmed gone, not merely because the ticket closed) so archive's own guard keeps first refusal.

Filed instead of fixed directly: T-4172 (leases, gate cache) is held by another live agent per this drive's dispatch brief -- src/frob/tickets/_leases.py is out of T-4066's declared scope (tests/test_ticket_runner_archive_force.py, tests/test_check_runner.py, tests/unit/test_check_tool_unavailable.py) and out of my lease.
