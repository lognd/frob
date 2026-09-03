## Done report

Re-verified docs/design/ledger-v2.md section 7's migrate_missing_v2 paragraph against current code: the described behavior (gap-fill migrator for partially-migrated repos, closes the gap migrate_v1_to_v2 leaves open) is unchanged and accurate. Only the source-file citation was stale after T-2695's extraction ('src/frob/tickets/_store.py' -> '_store_migrate.py'), fixed inline in the doc. Removed the AFFECT001 waiver on migrate_missing_v2 and ran frob ack against the doc anchor to record the re-verification. No content drift found -- no other edits needed.

### Changed
```
 tickets/T-3472/done-report.md | 17 +++++++++++++++++
 tickets/T-3472/ticket.md      |  6 +++++-
 2 files changed, 22 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_migrates_only_the_monofile_only_tickets` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_never_overwrites_an_already_migrated_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateMissingV2::test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 11 error(s), 4033 warning(s), 868 waived
- error-findings: COV003@tests/gates/test_rule_id_scan_branches.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3472, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
