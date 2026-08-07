---
id: T-0633
title: 'tickets: ledger writes racing a ticket start background sweep can clobber
  an unrelated ticket''s block'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive
- tests/test_tickets_ledger_concurrency.py::TestRenumberOneRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_renumber_one
- tests/test_tickets_ledger_concurrency.py::TestLedgerLockSpansWholesaleOperations::test_concurrent_ledger_lock_acquisition_serializes
designated_repro_test: null
acceptance:
- text: GIVEN a ticket start whose background sweep completes after a concurrent frob
    ticket new WHEN both finish THEN both tickets' ledger blocks are fully intact
    (state, body, evidence)
  evidence: []
threat: null
component: null
---
Two independent occurrences in one session (2026-07-22): (1) the coordinator's T-0630 block was silently wiped from main's tickets.md by a concurrent stale-ledger write; (2) T-0576's implementer observed frob ticket new, run immediately after frob ticket start's BACKGROUND pre-work sweep, overwrite ticket T-0632's ledger block entirely -- the sweep loads the ledger, the new writes it, the sweep's completion writes back its stale copy (lost update). The ledger lock (.frob/tickets.lock) is held per-operation, not across the background sweep's load-modify-write. Fix: the background sweep must re-acquire the lock AND re-load the ledger before writing (or write only its own ticket's sweep fields via a targeted read-modify-write), never write back a whole stale ledger. Add a regression test: start (with slow sweep stubbed) + concurrent new -> both tickets' blocks intact.