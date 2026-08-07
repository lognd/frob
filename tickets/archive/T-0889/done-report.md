## Done report

## Done report

Changed:
src/frob/tickets/_store.py::ledger_digest
src/frob/tickets/_store.py::_MISSING_LEDGER_DIGEST
src/frob/tickets/_store.py::write_all
src/frob/tickets/_store.py::write_archive
src/frob/tickets/_models.py::TicketError (LedgerChangedSinceLoad added)
src/frob/tickets/__init__.py::archive
src/frob/tickets/__init__.py::_write_archived_and_active
src/frob/tickets/__init__.py::renumber
src/frob/tickets/__init__.py::_load_and_validate_renumber_ids
src/frob/tickets/__init__.py::_persist_renumber
src/frob/tickets/__init__.py::renumber_one
src/frob/tickets/_land.py::_rewrite_draft_references_in_bodies

Fix: `write_all`/`write_archive` now accept an optional `expected_digest`
(a `ledger_digest` sha256 snapshot the caller took at load time). Under
the same `ledger_lock` span, the on-disk ledger is re-fingerprinted
immediately before the wholesale write; a mismatch refuses
(`Err(TicketError.LedgerChangedSinceLoad)`) instead of silently
overwriting whatever changed. `expected_digest=None` (default) preserves
prior unconditional-overwrite behavior for any not-yet-updated caller.
Wired into every existing load-then-wholesale-write caller: `archive`,
`renumber`, `renumber_one` (via `_load_and_validate_renumber_ids`/
`_persist_renumber`), and land's `_rewrite_draft_references_in_bodies`
(the one caller whose load and write were NOT already held under one
lock span -- closes that gap directly, not just via defense in depth).

Evidence: tests/test_ticket_store_stale_snapshot.py (7 new tests, all
bound via `frob ticket evidence T-0889 ... --accepts 0`):
- TestWriteAllRefusesAStaleSnapshot::test_external_replacement_between_load_and_write_all_is_refused
- TestWriteAllRefusesAStaleSnapshot::test_matching_digest_write_all_succeeds
- TestWriteAllRefusesAStaleSnapshot::test_no_expected_digest_preserves_unconditional_overwrite
- TestWriteArchiveRefusesAStaleSnapshot::test_external_replacement_between_load_and_write_archive_is_refused
- TestLedgerDigest::test_missing_ledger_digests_to_empty_string
- TestLedgerDigest::test_digest_changes_when_content_changes
- TestLedgerDigest::test_digest_stable_for_unchanged_content

Also reran full existing suites touching the changed code paths (all
green, foreground, plain pytest node ids): tests/test_ticket_land.py::
TestDraftReferenceRewriteOnLand::test_land_rewrites_own_draft_id_reference_in_done_report,
tests/test_tickets.py::TestArchive/TestArchiveRefusesDuringInFlightWork/
test_tickets_queue_workflow_integration, tests/test_tickets_collision.py::
TestSweepWorktreeCollisionIncident, tests/test_tickets_ledger_concurrency.py
(all 3 classes), tests/unit/test_ticket_store.py::TestArchiveLedger::
test_write_then_load_archive_round_trips -- 20 tests, all pass.

Filed: none (no out-of-scope work found; the pre-existing gates-security
SELFAUDIT001 findings on src/frob/arch/_logging_checks.py are unrelated
to this ticket's scope and untouched by this change).

Gates: `frob check --only <stage> --delta --ticket T-0889` run per
chunked stage (playbook section 3b):
- gates-fast: PASS (0 errors after adding frob:ticket/frob:doc/frob:tests
  directives to every touched symbol and fixing one frob:tests directive
  syntax bug of my own, plus `frob fmt` wrap and `frob ticket sweep
  T-0889` refresh)
- gates-native: PASS (0 errors)
- lint: PASS (ruff-check/ruff-format/ty all clean)
- static: PASS (frob-cycle/frob-dup/frob-arch/frob-exports all pass;
  pre-existing long-function/god-module warnings on files I touched are
  warnings, not errors, and predate this change)
- gates-security: FAIL on pre-existing SELFAUDIT001 (src/frob/arch/
  _logging_checks.py capability declarations) -- untouched by this
  ticket, out of scope (src/frob/tickets/** only), not introduced by
  this change.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_external_replacement_between_load_and_write_all_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_matching_digest_write_all_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshot::test_no_expected_digest_preserves_unconditional_overwrite` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestWriteArchiveRefusesAStaleSnapshot::test_external_replacement_between_load_and_write_archive_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_missing_ledger_digests_to_empty_string` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_digest_changes_when_content_changes` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest::test_digest_stable_for_unchanged_content` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 1 error(s), 2303 warning(s), 219 waived
- error-findings: SELFAUDIT001@design
