## Done report

docs/modules/tickets-data-storage.md's 4 frob:describes anchors for migrate_to_ledger/migrate_v1_to_v2/_migrate_one_v2/_split_done_report already named src/frob/tickets/_store_migrate.py (T-2718's lease had cleared and the anchors were updated by the time this ticket started, verified by grep against _store_migrate.py's actual def lines). Removed the 4 now-unneeded AFFECT001 waivers in _store_migrate.py that cited the T-2718 lease conflict as the reason they could not be updated in T-2695; left migrate_missing_v2's own AFFECT001 waiver in place since it documents against docs/design/ledger-v2.md, a doc outside this ticket's declared scope and not one of the 4 anchors named in the ticket body.

Changed: src/frob/tickets/_store_migrate.py (removed 4 stale AFFECT001 waiver comment blocks)
Evidence: uv run frob check --only docblocks --only drift (repo-wide baseline errors, none referencing _store_migrate.py or tickets-data-storage.md), uv run frob check --ticket T-2730 -> gate:SCOPE 0 errors, gate:AFFECT passes; uv run frob test --base main -> no tests selected (docs/comment-only change, expected)
Filed: none
Gates: docs-kind ticket, no code symbols changed

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 16 error(s), 4134 warning(s), 864 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-2730, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_land_parity_gate.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
