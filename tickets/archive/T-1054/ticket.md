---
id: T-1054
title: frob ticket start from a worktree leaves the root ledger state transition uncommitted
  -- DirtyMain then blocks every land until a human commits it
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_lease.py
  reason: 'Ticket scope glob mentions src/frob/tickets/_lease.py and tests/test_ticket_lease.py
    which never existed (typo for _leases.py / test_ticket_leases.py, the actual module/test
    file these acceptance criteria concern). Correcting the declared scope to the
    real filenames so SCOPE001 reflects the files the fix actually needed to touch.

    '
  actor: logan
  at: '2026-07-27'
- op: remove
  glob: tests/test_ticket_lease.py
  reason: 'Ticket scope glob mentions src/frob/tickets/_lease.py and tests/test_ticket_lease.py
    which never existed (typo for _leases.py / test_ticket_leases.py, the actual module/test
    file these acceptance criteria concern). Correcting the declared scope to the
    real filenames so SCOPE001 reflects the files the fix actually needed to touch.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'Ticket scope glob mentions src/frob/tickets/_lease.py and tests/test_ticket_lease.py
    which never existed (typo for _leases.py / test_ticket_leases.py, the actual module/test
    file these acceptance criteria concern). Correcting the declared scope to the
    real filenames so SCOPE001 reflects the files the fix actually needed to touch.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'Ticket scope glob mentions src/frob/tickets/_lease.py and tests/test_ticket_lease.py
    which never existed (typo for _leases.py / test_ticket_leases.py, the actual module/test
    file these acceptance criteria concern). Correcting the declared scope to the
    real filenames so SCOPE001 reflects the files the fix actually needed to touch.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_ticket_leases.py::TestCommitStartTransition::test_commits_dirty_ledger_with_expected_message
- tests/test_ticket_leases.py::TestCommitStartTransition::test_no_op_when_ledger_already_clean
- tests/test_ticket_leases.py::TestCommitStartTransition::test_reports_exact_recovery_command_on_commit_failure
- tests/test_ticket_leases.py::TestCommitStartTransition::test_commits_cleanly_even_when_caller_shell_has_frob_agent_set
designated_repro_test: null
acceptance:
- text: 'given a worktree, when frob ticket start transitions a ticket to in-progress,
    then the root tickets.md change is committed by the verb itself (message form:
    chore(tickets): record <id> start transition) and root git status stays clean'
  evidence:
  - tests/test_ticket_leases.py::TestCommitStartTransition::test_commits_dirty_ledger_with_expected_message
  - tests/test_ticket_leases.py::TestCommitStartTransition::test_commits_cleanly_even_when_caller_shell_has_frob_agent_set
- text: given a start whose commit step fails, when the verb exits, then it reports
    the dirty root loudly with the exact commit command to run, instead of leaving
    silent dirt
  evidence:
  - tests/test_ticket_leases.py::TestCommitStartTransition::test_reports_exact_recovery_command_on_commit_failure
threat: null
component: null
---
Recurring all through the 2026-07-27 drive: an agent's ticket start in a worktree writes the queued->in-progress line into ROOT tickets.md but never commits it; the next land (any agent) refuses with DirtyMain. Diagnosed explicitly during the T-1023 land (coordinator committed 52419399 by hand to unblock). land already owns its ledger commits; start should own its transition commit the same way.