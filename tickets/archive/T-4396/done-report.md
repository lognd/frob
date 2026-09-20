## Done report

Changed:
- tests/test_tickets_organization.py: `TestForceOverrideAudit.test_archive_force_with_no_live_lease_needs_no_reason`
  and `TestForceOverrideAudit.test_archive_force_with_live_lease_and_no_reason_refuses`
  widened both monkeypatched `frob.tickets._leases.read_all_leases` fakes
  (`lambda root: ...`) to accept `**kwargs` -- T-4388 added a keyword-only
  `exclude_from_reconcile` parameter to the real function, called from
  `_require_reason_for_archive_force` (src/frob/app/ticket_runner/_archive.py),
  and the old fakes raised `TypeError: unexpected keyword argument
  'exclude_from_reconcile'`.

No production code changed; src/frob/app/ticket_runner/_archive.py was
declared in scope only because the CI stack trace named it as the call
site whose new keyword argument the fakes did not match.

Evidence: tests/test_tickets_organization.py::TestForceOverrideAudit::test_archive_force_with_no_live_lease_needs_no_reason,
tests/test_tickets_organization.py::TestForceOverrideAudit::test_archive_force_with_live_lease_and_no_reason_refuses,
tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal,
tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists,
tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists,
tests/test_ticket_leases_cross_worktree.py::TestScopeAddIgnoresTerminalLease::test_dropped_ticket_on_local_ledger_does_not_block_live_lease
-- all 6 pass. `--check-repro` confirmed a genuine FAILED_AT_PARENT repro
before the fix (matches the CI failure exactly).

Filed: none

Gates: targeted pytest evidence above; full `frob check --ticket` not run
in this window per the drive's verification budget and host contention.
