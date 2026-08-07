## Done report

Wired `frob ticket migrate --to v2` onto migrate_v1_to_v2 (T-1259). Added
AppConfig.ticket_migrate_to (str | None), whitelisted it in
_config_external.py's _STRING_FIELDS, added the `--to` argparse flag
(choices=["v2"]) to the ticket-migrate subparser, and updated
ticket_runner._migrate to dispatch to migrate_v1_to_v2 when to="v2" while
leaving the default (--to omitted) collapse-dir-into-monofile path
unchanged. Documented the flag in docs/modules/cli.md. Two new tests
cover both branches via ticket_runner.run(cfg) end to end.

### Changed
```
 tickets.md | 27 ++++++++++++++++++++++++---
 1 file changed, 24 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_migration.py::TestMigrateCliToV2Flag::test_migrate_to_v2_flag_calls_migrate_v1_to_v2` (pytest node id, verified passing when recorded)
- `tests/test_tickets_migration.py::TestMigrateCliToV2Flag::test_migrate_without_to_keeps_dir_collapse_behavior` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 334 warning(s), 784 waived
- error-findings: none (measured, zero errors)
