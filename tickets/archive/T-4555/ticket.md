---
id: T-4555
title: Export tickets.lock path publicly from frob.tickets._store for cross-module
  probes
state: done
kind: ux
origin: human
created: '2026-09-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
- tests/unit/test_ticket_store.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: test binding TICKETS_LEDGER_LOCK_REL single-source invariant
  actor: logan
  at: '2026-09-18'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: test binding TICKETS_LEDGER_LOCK_REL / _lock_path invariant
  actor: logan
  at: '2026-09-18'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: frob:doc anchor for the new public TICKETS_LEDGER_LOCK_REL export
  actor: logan
  at: '2026-09-18'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: frob:doc anchor for the new public TICKETS_LEDGER_LOCK_REL export
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_ticket_store.py::TestLockPath::test_public_lock_rel_matches_private_lock_path
- tests/test_ticket_leases.py::TestTicketsLedgerLockRelSingleSource::test_leases_constant_is_the_store_constant
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3612 (narrow LandInProgress to the ledger-splice
critical section).

T-3612's narrowed refuse_if_land_in_progress needs .frob/tickets.lock's
exact path from frob.tickets._leases to probe the same lock
frob.tickets._store.ledger_lock holds. _store._lock_path/_LOCK_REL are
deliberately PRIVATE (T-0601: "no consumer outside this module and its
own test"), and _store.py was out of T-3612's declared scope, so T-3612
added a SECOND, independently-defined constant
(_leases.TICKETS_LEDGER_LOCK_REL = Path(".frob") / "tickets.lock") with a
comment demanding it stay byte-for-byte identical to _store._LOCK_REL --
exactly the "two independently-defined copies that could silently drift
apart" shape _leases.py's own T-1619 comment about LAND_LOCK_REL already
warns against for the OTHER lock.

Fix: give _store.py one canonical, public accessor for the ledger lock
path (e.g. TICKETS_LEDGER_LOCK_REL or a ledger_lock_path(root) function),
re-export or import it from _leases.py, and delete
_leases.TICKETS_LEDGER_LOCK_REL's duplicate definition. Low risk, small
diff -- deferred only because it touches _store.py, outside T-3612's
scope.