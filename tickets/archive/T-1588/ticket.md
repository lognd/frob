---
id: T-1588
title: 'ledger v2 has no stale-snapshot guard: write_archive/write_all expected_digest
  is a v1-only primitive'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- tests/test_ticket_store_stale_snapshot.py
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshotV2::test_external_replacement_between_load_and_write_all_is_refused
- tests/test_ticket_store_stale_snapshot.py::TestWriteArchiveRefusesAStaleSnapshotV2::test_external_replacement_between_load_and_write_archive_is_refused
- tests/test_ticket_store_stale_snapshot.py::TestLedgerDigestMapV2::test_map_keys_are_ticket_ids_values_match_ledger_digest
- tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshotV2::test_v1_style_string_digest_in_v2_mode_is_treated_as_no_check
designated_repro_test: null
threat: null
component: null
---
expected_digest (T-0889 optimistic concurrency) fingerprints ONE ledger file via ledger_digest, so it only means anything in v1/'single' mode. T-1583's v2 write_archive branch, and write_all's v2 branch before it, therefore perform NO stale-snapshot check at all: a caller that loads, is overtaken by a sibling process, and writes back a stale wholesale map silently clobbers the sibling's write instead of getting LedgerChangedSinceLoad. Every new repo is v2, and the coordinator/agent flow this repo runs on is exactly the concurrent-writer shape the guard exists for.

tests/test_ticket_store_stale_snapshot.py is pinned to v1 for now (it verifies the monofile primitive); it needs a v2 mirror once a guard exists.

Design question for the implementer: the natural v2 fingerprint is per-TICKET (each tickets/T-####/ticket.md has its own content hash and its own ticket_lock) rather than one tree-wide digest -- a tree digest would make every concurrent write to unrelated tickets collide, throwing away v2's main benefit. Prefer a per-id digest map, or move the wholesale callers (archive, renumber) onto per-ticket writes that each carry their own expected digest.