---
id: T-4388
title: Lease reconciliation unlinks live lease before archive T-0843 guard sees it
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_runner_archive_force.py
- tests/test_tickets.py
- tests/test_ticket_leases_cross_worktree.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: coordinator confirmed CI failure covers 4 tests across these files
  actor: logan
  at: '2026-09-09'
- op: add
  glob: tests/test_ticket_leases_cross_worktree.py
  reason: coordinator confirmed CI failure covers 4 tests across these files
  actor: logan
  at: '2026-09-09'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Landed ticket T-4172 (commit 1c6bee53c, lease reconciliation in
src/frob/tickets/_leases.py) introduced a deterministic failure that will red
the ubuntu CI leg.

Repro (deterministic, no xdist needed): in a fresh v2-mode repo, create+
start+close a ticket (e.g. T-0001), then write a live lease record for
T-0001 pointing at the same worktree/root, then call archive()/archive_v2().

Expected (T-0843's own contract, tests/test_ticket_runner_archive_force.py
::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal and
::test_refuses_without_force_when_a_live_lease_exists): archive refuses (or
requires --force) because the ticket being archived still holds a live
cross-worktree lease.

Actual: read_all_leases() now logs "T-0001 lease's ticket has already
finished on this ledger -- stale lease at .../frob-leases/T-0001.json
reconciled against ticket state and unlinked (T-4172)" and UNLINKS the lease
before archive's own guard (_refuse_archive_if_leased) ever sees it, so
read_all_leases() returns () and the guard silently no-ops -- archive
proceeds with no refusal and no --force required.

This is T-4172's own lease-reconciliation logic treating "ticket already
DONE/DROPPED on the ledger" as sufficient proof a lease is stale -- but
T-0843's whole guard exists PRECISELY for the case where a ticket has just
transitioned to done/dropped while a lease from that same close operation
(or a sibling worktree's) is still live. Reconciling it away on ledger-state
alone defeats T-0843's live-lease refusal for exactly the scenario it was
built to catch (T-0753's field-incident risk: archiving now would risk
reverting the ticket's start/evidence/acceptance on next restore).

MUST-FIRE: test_force_overrides_the_live_lease_refusal and
test_refuses_without_force_when_a_live_lease_exists
(tests/test_ticket_runner_archive_force.py) both fail deterministically
against main plus T-4172 (verified locally, 100% repro, not load-sensitive).

Fix direction: reconciliation must not unlink a lease purely because the
ledger already reads done/dropped -- that is exactly the state a lease
recorded by the closing operation itself is expected to be in while still
live. Either run reconciliation after archive's own guard, or narrow it to
only unlink when the lease's own worktree is also confirmed gone -- not
merely because the ticket closed -- so archive's guard keeps first refusal.
Keep T-4172's own tests green.
