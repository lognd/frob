---
id: T-2141
title: '--allow-cross-ticket carries an undeclared set: the operator cannot state
  which tickets they expect to carry, so a legitimate sibling batch and an accidental
  foreign carry look identical'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
evidence_scope:
- tests/unit/test_ticket_runner_land_cmd_flags.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: fix already landed onto main as a passenger of T-1549''s
    own land; repro test structurally cannot fail at parent any more'
  actor: logan
  at: '2026-08-19'
  old_length: 0
  new_length: 703
evidence:
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestCrossTicketCarriedPathsDisclosure::test_out_of_scope_file_is_reported_carried
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestCrossTicketCarriedPathsDisclosure::test_all_files_in_scope_reports_nothing_carried
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestCrossTicketCarriedPathsDisclosure::test_none_touched_paths_is_unmeasurable_not_empty
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestCrossTicketCarriedPathsDisclosure::test_unloadable_ticket_returns_none_not_empty
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestWarnLandOverrideFlagsDisclosesCarriedSet::test_carried_file_is_logged_at_warning
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestWarnLandOverrideFlagsDisclosesCarriedSet::test_no_flag_no_disclosure_logged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5acddd68b029dfd8bfabfbe8db050a92696d4ad3
---
frob:waive BUG002 reason="T-2141's own fix (_cross_ticket_carried_paths, _land_cmd.py) already landed onto main as an undisclosed-turned-disclosed passenger of T-1549's own --allow-cross-ticket land (both tickets share one series worktree branch, T-1549 landed first per coordinator instruction 2026-08-19/20). main now already contains the fix, so the designated repro test structurally cannot fail at parent any more -- confirmatory-only is the only possible outcome from this point forward, not evidence the original repro was ever weak. git diff main -- src/frob/app/ticket_runner/_land_cmd.py is empty; this land is now a ledger-close operation over already-shipped code, not a fresh code change."