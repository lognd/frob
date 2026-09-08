---
id: T-4342
title: Surface orphaned per-ticket lock files as a routine detection signal
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
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
- docs/modules/tickets-landing.md
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-landing.md
  reason: doc anchor + test coverage for the orphaned-ticket-lock detector added to
    _leases.py
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_ticket_leases.py
  reason: doc anchor + test coverage for the orphaned-ticket-lock detector added to
    _leases.py
  actor: logan
  at: '2026-09-08'
evidence:
- tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_lock_gone_ticket_is_orphaned
- tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_real_ticket_not_orphaned
- tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_archived_ticket_not_orphaned
- tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_live_holder_not_orphaned
- tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_bad_ledger_degrades_to_none
- tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_warn_logs_once_per_id
- tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_land_guard_surfaces_warning
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
T-4339 found that the ONLY surviving trace of the ticket-loss incident
(T-4313) was an orphaned .frob/tickets/<id>.lock file -- the per-ticket
ticket_lock (_ticket_lock_path, .frob/tickets/<id>.lock) left behind
after _write_ticket_v2_mode acquired it, wrote, and the write was later
rolled back by a concurrent land (_rollback_pathspecs, git clean -fd
over the still-untracked ticket path) -- .frob/ is gitignored and out of
scope for that pathspec-limited clean, so the lock file survives while the
ticket directory does not.

By construction, a .frob/tickets/<id>.lock file whose id has NO
corresponding ticket anywhere (active store or archive) is evidence of
exactly this failure shape. T-4339 fixed the immediate silent-success bug
(a mandatory post-commit read-back before frob ticket new ever prints
created <id>), but nothing routinely scans for orphaned lock files
themselves -- this incident sat undetected for hours because nothing
looked at .frob/tickets/*.lock against the live ticket set.

## Plan
Add a routine check (likely alongside orphaned_leases/release_orphaned_
lease in frob.tickets._leases, or as a frob check/frob verify rule)
that lists every .frob/tickets/*.lock file whose id is absent from both
the active ledger and the archive, and surfaces it loudly (a WARNING at
minimum, a dedicated check/gate code if this project's convention prefers
one). Should not auto-delete the lock (it costs nothing to leave, and
deleting it destroys the one forensic trace) -- surfacing is the goal.

Filed while working T-4339 (in scope: src/frob/tickets/_create.py, widened
to src/frob/app/ticket_runner/_new.py) -- T-4339's own scope explicitly
does not cover this and the natural home (_leases.py) was held by another
in-flight agent at the time.