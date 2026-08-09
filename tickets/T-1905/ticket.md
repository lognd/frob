---
id: T-1905
title: T-1892 EvidenceCmdSilent refusal breaks more fixtures using 'true' as evidence-cmd
  (test_ticket_runner_archive_force.py, test_ticket_leases.py)
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_runner_archive_force.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found via T-1902's mandated reverse-dependency search over 2026-08-09.

Same root cause as T-1902: T-1892's EvidenceCmdSilent refusal (silent
zero-exit evidence commands are correctly rejected) breaks additional
existing fixtures that pass the literal command 'true' as
ticket_evidence_cmd, beyond the two tests T-1902 already fixes.

MEASURED via:
  uv run pytest tests/test_ticket_runner_archive_force.py tests/test_ticket_leases.py -q

9 failures, all with the same captured error:
  WARNING frob.tickets._evidence: evidence command 'true' exited 0 but
    captured stdout+stderr empty -- refused (T-1892)
  ERROR   frob.app.ticket_runner: EvidenceCmdSilent: evidence command
    exited 0 with empty stdout+stderr -- proves nothing

Failing tests:
  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet
  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
  tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket
  tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean
  tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_evidence_no_commit_leaves_ledger_dirty
  tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_evidence_auto_commits
  tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
  tests/test_ticket_leases.py::TestCloseEvidenceDoneReportRequeueAutoCommit::test_close_auto_commits

THE NEW BEHAVIOR IS CORRECT (same rule as T-1902) -- do not revert or
bypass it. Fix by swapping 'true' for a chatty zero-exit command (e.g.
'echo verified') in each fixture, same recipe as T-1902's Done report.

Also checked and clean (no action needed):
  tests/test_ticket_leases.py lines 1927/1943/1982 use 'true' but those
  three sites are in a DIFFERENT test than the 5 above and were not in
  the pytest failure list -- likely already expect/handle the refusal or
  are unreached by the assertions; re-verify when fixing this ticket.
  tests/test_tickets_cmd_evidence.py:164 uses 'true' but that file was
  NOT in the failing set either -- also re-verify, do not assume clean.