---
id: T-1813
title: 'post-land sweep regression from T-1811: 2 new error(s) (ARCH001, invalid-return-type)'
state: done
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_renumber.py
- tickets/T-1813/ticket.md
- tickets/T-1813/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1813/ticket.md
  reason: ticket's own state-transition ledger writes (start/requeue auto-commits)
    are part of this ticket's own diff and SCOPE001-flag otherwise
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1813/done-report.md
  reason: the ticket's own done-report auto-commit is part of its diff and SCOPE001-flags
    otherwise, same as ticket.md
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_tickets.py::TestNewTicket::test_allocates_sequential_id
- tests/test_tickets.py::TestArchive::test_new_ticket_corrupt_archive_fails_loudly
- tests/test_tickets.py::TestArchive::test_new_ticket_fresh_repo_no_archive_file
- tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1811 at commit defaa35d2335d88cb948d23410e01208db6b865e found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH001  src/frob/tickets/_new_renumber.py
- invalid-return-type  src/frob/tickets/_new_renumber.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="ARCH001 is cleared by splitting new_ticket's existing body into three private helpers with the same call sequence and control flow -- no runtime behavior changed. The invalid-return-type fix (line 347, 'return duplicate_check' instead of 'return Err(duplicate_check.danger_err)') is also behavior-neutral: duplicate_check is already an Err(...) object on that branch, so re-wrapping it via Err(duplicate_check.danger_err) constructs an equal Err value -- only the static type annotation was wrong, not the runtime object returned. Bound evidence (existing new_ticket tests) passes at both parent and fix, consistent with a no-behavior-change claim."