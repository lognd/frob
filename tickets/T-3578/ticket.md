---
id: T-3578
title: macOS-only ledger commit failure in archive-force live-lease test
state: done
kind: bug
origin: human
created: '2026-08-31'
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
- tests/test_ticket_runner_archive_force.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_runner_archive_force.py
  reason: 'cross-platform: the sibling test in the same file also reproduces the identical
    ledger-commit failure'
  actor: logan
  at: '2026-08-31'
evidence:
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_commit_failure_names_the_failing_step_and_git_detail
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33376126399, macos-latest only (job 99437896987, darwin, Python 3.14.6, pytest-xdist gw0), first occurrence: tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists dies with SystemExit: 1.

Full traceback (fetched via gh api repos/lognd/frob/actions/jobs/99437896987/logs):

Failure is in the tests SETUP helper _make_done_ticket (tests/test_ticket_runner_archive_force.py:73/92), not in the archive-force logic under test itself. _make_done_ticket calls ticket_run(...) to close T-0001 (src/frob/app/ticket_runner/__init__.py:807 -> _close_cmd.py _close). The close transition itself succeeds; the failure is in the FINAL step, commit_ticket_ledger_change (src/frob/tickets/_leases.py) -- committed.is_err/nonzero from _add_and_commit_tickets_md git add/commit, so _close_cmd.py:1465 sys.exit(1) fires. Captured log:

ERROR frob.tickets._leases:_leases.py:2827 tickets: T-0001 ledger change left <tmp_path>/repo DIRTY -- the commit step failed. Run this by hand before anything else lands: git -C <repo> add tickets/T-0001 && git -C <repo> commit -m "chore(tickets): close T-0001" -- tickets/T-0001

i.e. either git add or git commit itself returned nonzero inside _add_and_commit_tickets_md (src/frob/tickets/_leases.py:2789-2809). No git stderr is captured in the log (gitio.run_argv results are not logged on failure here), so the exact git-level cause (missing global user.name/user.email on a fresh macOS runner, a path/quoting difference, a _retry_commit_with_fallback_identity darwin gap, or a xdist-worker race in _repair_stale_ledger_commit_markers) is not directly visible from CI output alone -- diagnose against T-3500s live-process darwin-branch family (which touches this same tickets/_leases.py module, e.g. _land_check_with_optional_rollback -> refuse_if_land_in_progress -> the darwin cwd/live-pid detection) as the prime suspect for any macOS-specific behavior difference in this path, though the immediate failure signature (git add/commit nonzero) points more directly at a git-identity or command-quoting gap than the live-pid scan itself.

Fix hermetically: at minimum, log_ledger_commit_failure should capture and surface the actual git stderr/returncode from the failed add/commit call (currently swallowed), so a recurrence is diagnosable from CI output alone without re-fetching raw job logs; and _retry_commit_with_fallback_identity should be re-audited for a darwin-specific gap (e.g. global git config discovery differing between macos-latest runner image and the other two). If the underlying cause is confirmed macOS-CI-environment-only (not a real cross-platform correctness bug), frob:waive BUG002 with that reasoning is acceptable per this tickets own instructions.

Also FYI (same run, other tests, NOT this ticket, no action needed here): tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero and tests/test_frob_self_model.py (SELFAUDIT001 SYS111 ratchet) and tests/test_docptr_gate.py (DOC006) also failed in this run -- unrelated pre-existing/other-ticket territory (DOC006/SYS111 is T-3575s subject), listed here only for run-context completeness.