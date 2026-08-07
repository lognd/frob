---
id: T-0889
title: ticket CLI write-back clobbers externally-replaced ledger with stale in-memory
  snapshot (reverted 3 done tickets)
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_store_stale_snapshot.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_external_replacement_between_load_and_write_all_is_refused
- tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_matching_digest_write_all_succeeds
- tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_no_expected_digest_preserves_unconditional_overwrite
- tests/test_ticket_store_stale_snapshot.py::TestWriteArchiveRefusesAStaleSnapshot::test_external_replacement_between_load_and_write_archive_is_refused
- tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_missing_ledger_digests_to_empty_string
- tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_digest_changes_when_content_changes
- tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_digest_stable_for_unchanged_content
designated_repro_test: null
acceptance:
- text: GIVEN tickets.md is externally replaced between a CLI process's load and its
    write-back WHEN the write happens THEN no unrelated ticket block regresses (reload-and-merge
    or loud refusal), proven by a regression test
  evidence:
  - tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_external_replacement_between_load_and_write_all_is_refused
  - tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_matching_digest_write_all_succeeds
  - tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_no_expected_digest_preserves_unconditional_overwrite
  - tests/test_ticket_store_stale_snapshot.py::TestWriteArchiveRefusesAStaleSnapshot::test_external_replacement_between_load_and_write_archive_is_refused
  - tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_missing_ledger_digests_to_empty_string
  - tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_digest_changes_when_content_changes
  - tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_digest_stable_for_unchanged_content
threat: null
component: tickets
---
Real incident during T-0680 (see its Done report): in a worktree whose tickets.md had just been restored to main's version (section 10b recipe), a sequence of frob ticket start/evidence/sweep/done-report calls SILENTLY REVERTED three unrelated tickets (T-0660/T-0661/T-0719) from done back to queued with evidence and Done reports wiped -- the CLI appears to write back a stale in-memory ticket-queue snapshot loaded before the restore, clobbering the on-disk ledger state. Same corruption family as the land-splice regression (T-0577 lineage) but in the plain CLI write path, not land. Investigate the store's load/write lifecycle for a cached snapshot surviving an external file replacement (mtime/digest check on write-back would fail loudly). Fix = detect ledger-changed-since-load and reload before any write, plus a regression test that replaces tickets.md between load and write.