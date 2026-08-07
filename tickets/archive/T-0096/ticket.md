---
id: T-0096
title: 'frob ticket archive: rotate done tickets out of the active ledger'
state: done
kind: ux
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
- src/frob/__main__.py
- docs/modules/tickets.md
- tickets.md
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestArchive::test_moves_done_and_dropped_only
- tests/test_tickets.py::TestArchive::test_idempotent_second_run_moves_nothing
- tests/test_tickets.py::TestArchive::test_nothing_to_archive_is_zero
- tests/test_tickets.py::TestArchive::test_load_queue_merges_active_and_archive
- tests/test_tickets.py::TestArchive::test_blocked_by_archived_ticket_resolves_closed
- tests/unit/test_ticket_store.py::TestArchiveLedger::test_archive_path_at_root
- tests/unit/test_ticket_store.py::TestArchiveLedger::test_load_archive_missing_file_is_empty
- tests/unit/test_ticket_store.py::TestArchiveLedger::test_write_then_load_archive_round_trips
- tests/unit/test_ticket_store.py::TestArchiveLedger::test_archive_format_matches_ledger_marker
designated_repro_test: null
threat: null
component: null
---
tickets.md is 2100+ lines and grows with every done report; agents hand-edit it by string surgery (three evidence failures already) and re-read big chunks every mission. Add frob ticket archive moving done/dropped tickets verbatim to tickets-archive.md (same format, grep-compatible, still tracked); active ledger stays a few hundred lines. Single-file model preserved -- just two files by temperature. Complements T-0094 (evidence CLI).