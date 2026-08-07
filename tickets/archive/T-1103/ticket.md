---
id: T-1103
title: 'arch: split tickets/__init__.py (4287) and tickets/_land.py (4762) -- T-1089
  residue after ticket_runner.py split landed'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/tickets/_land.py
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
- tests/test_tickets_ledger_concurrency.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1103: split carries frob:doc/frob:tests reference targets, SCOPE002 requires
    them in ticket scope'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets.py
  reason: 'T-1103: split carries frob:doc/frob:tests reference targets, SCOPE002 requires
    them in ticket scope'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_ledger_concurrency.py
  reason: 'T-1103: split carries frob:doc/frob:tests reference targets, SCOPE002 requires
    them in ticket scope'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_waive.py
  reason: T-1103 split re-points this file's frob:uses-contract reference at the new
    src/frob/tickets/_archive.py::load_queue path
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_renumber_one_dry_run_prints_files
- tests/test_tickets_ledger_concurrency.py::TestRenumberOneRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_renumber_one
- tests/test_tickets_ledger_concurrency.py::TestFinalizeDraftAllocationRace::test_two_concurrent_finalize_draft_calls_get_distinct_ids
- tests/test_tickets_ledger_concurrency.py::TestLedgerLockSpansWholesaleOperations::test_concurrent_ledger_lock_acquisition_serializes
designated_repro_test: null
threat: null
component: null
---
T-1089 residue: ticket_runner.py -> ticket_runner/ package split landed (commits c20d91d5, e08e088a, 5fdc913d on t1089-tickets-splits). The other two monsters in T-1089's original scope -- src/frob/tickets/__init__.py (4287 lines) and src/frob/tickets/_land.py (4762 lines) -- were not attempted this wave; budget exhausted after the first file plus its DRIFT002/SCOPE001/DUP001/INV006 follow-on fixes (see T-1089 Done report for the monkeypatch-indirection and shared-logger-name hazard classes this family of split hits -- both apply here too, and T-1090's atomic id-allocation change plus T-1078's REL bump path in _land.py need the same read-landed-diff-before-carving care T-1089's dispatch prompt called out). Same T-1072/T-1076/T-1086 discipline: cohesive families to private modules, public surface re-exported via __all__, zero caller edits, every frob:tests/frob:doc/frob:describes edge re-pointed, PII allowlist (file,token) entries carried, file-level INV006 waivers carried into each new submodule, smallest file (tickets/__init__.py) first.