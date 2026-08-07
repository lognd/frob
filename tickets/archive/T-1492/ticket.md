---
id: T-1492
title: 'ledger v2: wire migrate --to v2 CLI flag onto migrate_v1_to_v2'
state: done
kind: feature
origin: agent
created: '2026-08-03'
priority: medium
blocked_by:
- T-1259
parent: T-1259
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/__init__.py
- docs/modules/cli.md
- tests/test_tickets_migration.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: migrate --to v2 flag needs an AppConfig field (ticket_migrate_to) plus its
    _config_external whitelist entry, same pattern as every other ticket_* dest; CLI
    parser alone cannot carry the value through to the runner
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: migrate --to v2 flag needs an AppConfig field (ticket_migrate_to) plus its
    _config_external whitelist entry, same pattern as every other ticket_* dest; CLI
    parser alone cannot carry the value through to the runner
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_tickets_migration.py::TestMigrateCliToV2Flag::test_migrate_to_v2_flag_calls_migrate_v1_to_v2
- tests/test_tickets_migration.py::TestMigrateCliToV2Flag::test_migrate_without_to_keeps_dir_collapse_behavior
designated_repro_test: null
acceptance:
- text: GIVEN a monofile-mode repo WHEN frob ticket migrate --to v2 runs THEN it calls
    migrate_v1_to_v2 (T-1259) and reports the migrated count, leaving --to omitted
    behavior (collapse dir into monofile) unchanged
  evidence:
  - tests/test_tickets_migration.py::TestMigrateCliToV2Flag::test_migrate_to_v2_flag_calls_migrate_v1_to_v2
  - tests/test_tickets_migration.py::TestMigrateCliToV2Flag::test_migrate_without_to_keeps_dir_collapse_behavior
threat: null
component: null
---
found while working T-1259: migrate_v1_to_v2 (src/frob/tickets/_store.py) is implemented and golden-round-trip tested, but T-1259's own scope does not cover the CLI parser (_cli_parsers/_ticket/_progress.py) or the ticket_runner dispatch (app/ticket_runner/_query.py, __init__.py) needed to actually expose --to v2 on the existing frob ticket migrate subcommand. This ticket wires that flag.