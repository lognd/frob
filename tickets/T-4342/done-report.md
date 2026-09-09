## Done report

Changed:
- src/frob/tickets/_leases.py::_lock_file_held_by_live_process
- src/frob/tickets/_leases.py::orphaned_ticket_locks
- src/frob/tickets/_leases.py::warn_orphaned_ticket_locks
- src/frob/tickets/_leases.py::_warned_orphaned_ticket_lock_ids
- src/frob/tickets/_leases.py::refuse_if_land_in_progress (added the T-4342 scan call)
- docs/modules/tickets-landing.md#orphaned-ticket-lock-detection-t-4342 (new section)

Decisions, argued per the ticket body:
- WHERE it surfaces: `refuse_if_land_in_progress`, the single choke point every
  ledger-mutating ticket verb already calls, wrapped in try/except so a scan
  failure can never break the land-lock check itself -- not the unscoped
  `frob check` gate (~5,000 warnings today, a new one there is invisible).
- SEVERITY: WARNING. Forensic (a past loss), never something the current
  command caused, must never block it.
- FALSE-POSITIVE AVOIDANCE: `_lock_file_held_by_live_process` reuses the same
  non-blocking `flock` acquire-then-release probe `_land_flock_probe` already
  uses for the land lock, rather than re-deriving a second liveness
  primitive -- an in-flight `frob ticket new` holds the lock for its whole
  acquire-write-release span, so a lock this process can itself acquire has
  no live holder. Every ambiguous outcome (no lock backend, unreadable
  ledger) degrades to "do not report."
- WHETHER TO CLEAN: report-only, matching T-1876's posture for stale leases
  -- the lock file is the only forensic trace of what was lost.

Verified in BOTH directions, as required:
- A genuinely orphaned lock (no ticket, flock freely acquirable) IS reported
  (`test_lock_gone_ticket_is_orphaned`) and surfaced through
  `refuse_if_land_in_progress` (`test_land_guard_surfaces_warning`).
- A lock held by a live process is NOT reported (`test_live_holder_not_orphaned`,
  via a second fd's non-blocking flock acquire on the same file, the same
  signal a genuinely live sibling process would produce).
- Also verified against a lock naming a real active ticket, a real archived
  ticket, and an unreadable ledger (all correctly not reported), and that
  warnings log once per (root, id) per process.
- Ran live against this repo's own primary checkout's `.frob/tickets/`
  during scope-extension/pre-work-sweep commands in this session: correctly
  flagged ~29 genuinely orphaned locks (T-4313 itself included) with zero
  false positives against in-flight agent activity from the other running
  implementers.

Evidence: tests/test_ticket_leases.py::TestOrphanedTicketLocks (7 node ids
bound via `frob ticket evidence`), full module run 163/163 passed,
`frob test --base main` touched-set run green.

Filed: none -- no out-of-scope work found.

Gates: `frob check --ticket T-4342` clean except the pre-existing DRIFT002
in docs/guides/agent-playbook-appendix.md (owned by T-4345, present before
this ticket's changes).

### Changed
```
 docs/modules/tickets-landing.md |  65 ++++++++++++
 src/frob/tickets/_leases.py     | 220 ++++++++++++++++++++++++++++++++++++++++
 tests/test_ticket_leases.py     | 154 ++++++++++++++++++++++++++++
 tickets/T-4342/ticket.md        |  23 +++++
 4 files changed, 462 insertions(+)
```

### Evidence
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_lock_gone_ticket_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_real_ticket_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_archived_ticket_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_live_holder_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_bad_ledger_degrades_to_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_warn_logs_once_per_id` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_land_guard_surfaces_warning` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 1 error(s), 4744 warning(s), 954 waived
- error-findings: DRIFT002@docs/guides/agent-playbook-appendix.md
