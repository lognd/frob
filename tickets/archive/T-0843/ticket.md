---
id: T-0843
title: 'ticket archive: refusal hint says force=True not the CLI flag; T-0753 guard
  over-broad for in-progress-only leases'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
- tests/test_ticket_runner_archive_force.py
- src/frob/tickets/_models.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'The literal "pass force=True to override" refusal hint the ticket names

    lives in TicketError.ArchiveLiveLeaseExists''s message in

    src/frob/tickets/_models.py, not in the originally-scoped files -- that

    enum message is what actually renders in the CLI''s "ticket archive

    failed: %s" error line. Fixing only the log-line copy in

    src/frob/tickets/__init__.py would leave the exact string the ticket

    quotes unfixed.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/test_tickets.py
  reason: 'The T-0753/T-0764 archive-lease regression tests this ticket''s narrowed

    guard behavior changes live in tests/test_tickets.py

    (TestArchiveRefusesDuringInFlightWork) -- updating them to reflect the

    narrowed refusal condition is part of driving this bug fix''s own tests,

    not a separate concern.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_force_overrides_the_live_lease_refusal
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_ignores_a_stale_lease_from_a_removed_worktree
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_ignores_a_live_lease_for_a_ticket_it_would_not_touch
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists
designated_repro_test: null
threat: null
component: null
---
`frob ticket archive` refusal message says "pass force=True to override"
-- that is the internal python kwarg, not the CLI surface. The CLI flag
is --force (verify; if absent, add it mirroring other force flags).
Remedy hints must be copy-pastable commands (the repo's own violation-
message convention). Also consider: when the only live leases belong to
tickets whose blocks archive would NOT touch (in-progress tickets are
never archived), the refusal is over-broad -- evaluate narrowing the
T-0753 guard to refuse only when a live-leased ticket's OWN block would
be moved/rewritten, so a red TICK003 can be cleared without waiting for
unrelated in-flight work.