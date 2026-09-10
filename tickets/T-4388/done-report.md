## Done report

Changed:
- src/frob/tickets/_leases.py: `read_all_leases`/`_live_leases_pruning_stale`
  gained `exclude_from_reconcile: frozenset[str]` -- for a ticket id in that
  set, a present-worktree lease is returned as live instead of being
  unlinked by T-4172's terminal-ticket reconciliation.
- src/frob/tickets/_archive.py: `_refuse_archive_if_leased` passes
  `to_archive`'s own ids as `exclude_from_reconcile`, so the T-0843 guard
  sees a just-closed ticket's live lease before it can be reconciled away.
- src/frob/app/ticket_runner/_archive.py: `_require_reason_for_archive_force`
  computes the DONE/DROPPED ticket id set from the ledger and passes it the
  same way, so T-1762's `record_force_override` audit trail is not silently
  skipped for the identical reason.
- tests/test_ticket_leases_cross_worktree.py: updated
  `TestScopeAddIgnoresTerminalLease.test_dropped_ticket_on_local_ledger_does_not_block_live_lease`'s
  premise assertion -- T-4172 now reconciles the stale lease away entirely
  (a stronger fix for the same T-1909 goal), so the lease is no longer
  "live" at all, rather than merely ignored by scope --add's own check.

Evidence: tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal,
tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists,
tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists,
tests/test_ticket_leases_cross_worktree.py::TestScopeAddIgnoresTerminalLease::test_dropped_ticket_on_local_ledger_does_not_block_live_lease
-- all 4 pass; `--check-repro` confirmed a genuine FAILED_AT_PARENT repro
before the fix. T-4172's own tests
(tests/test_ticket_leases.py::TestReadAllLeasesReconciliation) still pass.
`frob test` (touched-set) green.

Filed: none

Gates: `frob check --ticket T-4388` could not complete within the
foreground budget under host contention (2+ other concurrent `frob check`
runs); relying on targeted pytest evidence above plus `frob test` instead,
per the drive's verification budget.
