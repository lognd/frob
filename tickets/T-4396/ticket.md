---
id: T-4396
title: TestForceOverrideAudit fakes T-4388's new read_all_leases keyword arg
state: queued
kind: bug
origin: human
created: '2026-09-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_tickets_organization.py
- src/frob/app/ticket_runner/_archive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4388 (landed 90ecadfa1) added an `exclude_from_reconcile` keyword-only
parameter to `frob.tickets._leases.read_all_leases`, and
`src/frob/app/ticket_runner/_archive.py::_require_reason_for_archive_force`
now calls it with `exclude_from_reconcile=terminal_ids`.

CI run 34448820080 shows this breaks two tests on ubuntu and macOS:
tests/test_tickets_organization.py::TestForceOverrideAudit::{
test_archive_force_with_no_live_lease_needs_no_reason,
test_archive_force_with_live_lease_and_no_reason_refuses}

Both monkeypatch `frob.tickets._leases.read_all_leases` with a lambda
that only accepts `root` (e.g. `lambda root: []`, `lambda root:
[_FakeLease()]`), predating T-4388's new keyword argument. The real
call site now passes `exclude_from_reconcile=...`, so the fake raises:

TypeError: TestForceOverrideAudit.test_archive_force_with_no_live_lease_needs_no_reason.<locals>.<lambda>() got an unexpected keyword argument 'exclude_from_reconcile'
(src/frob/app/ticket_runner/_archive.py:139, in _archive ->
_require_reason_for_archive_force)

Fix: widen both monkeypatched lambdas in
tests/test_tickets_organization.py::TestForceOverrideAudit to accept
the new keyword (e.g. `lambda root, **kwargs: []`), matching
`read_all_leases`'s real signature. No production code change expected
-- the two tests' fakes are simply stale against T-4388's new parameter.

Keep the four tests T-4388 already fixed green:
tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::{test_force_overrides_the_live_lease_refusal, test_refuses_without_force_when_a_live_lease_exists},
tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists,
tests/test_ticket_leases_cross_worktree.py::TestScopeAddIgnoresTerminalLease::test_dropped_ticket_on_local_ledger_does_not_block_live_lease
