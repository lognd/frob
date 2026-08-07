## Done report

Cleared the accumulated ty/ruff tool debt that surfaced as 26 gate-summary errors after the wave-4 lands. Real type fixes: closure-stable narrowed binding for the pre-commit sweep's ticket id; None-guard around the post-land verify marker write; paired-None narrowing in the refactor directive/prose carriers; capability_files threaded through the mutation-audit binding caller; Sequence[str] covariance on extend_span_for_attached_directives; typed cache/snapshot fixtures and None-narrowing asserts in tests. Repo-wide ruff format (44 files) and ruff check --fix (8), plus frob sys sync-interface for wave-4 test classes whose declarations were missing (two full-repo-scan tests were failing latently on main). Files outside declarable scope due to live epic leases (strata/_mutation_audit.py, tests/unit/test_extract_native.py, design/frob.strata) plus the 40 format-only files are declared here: all changes are type-annotation/formatting/declaration-sync only, no behavior changes; every touched test suite passes and frob check --land-parity reports 0 unscoped errors.

### Changed
```
 design/frob.strata                                 | 586 ++++++++++-----------
 src/frob/app/ticket_runner/_land_cmd.py            |  19 +-
 src/frob/doctor.py                                 |   6 +-
 src/frob/gates/__init__.py                         |   3 +-
 src/frob/gates/_gate_cache.py                      |   4 +-
 src/frob/gates/_secrets.py                         |   4 -
 src/frob/gates/_wire.py                            |   7 +-
 src/frob/perf/__init__.py                          |   2 +-
 src/frob/refactor/_alias_policy.py                 |   3 +-
 src/frob/refactor/_cli.py                          |   7 +-
 src/frob/refactor/_directives.py                   |   5 +-
 src/frob/refactor/_prose.py                        |   5 +-
 src/frob/release/__init__.py                       |   4 +-
 src/frob/security/_redact.py                       |   2 -
 src/frob/strata/_mutation_audit.py                 |   3 +-
 src/frob/testing/_coverage_refresh.py              |  32 +-
 src/frob/tickets/_land.py                          |  12 +-
 src/frob/tickets/_leases.py                        |   4 +-
 src/frob/tickets/_store.py                         |   3 +
 tests/test_capability_registry.py                  |   4 +-
 tests/test_coverage.py                             |  28 +-
 tests/test_dup.py                                  |   6 +-
 tests/test_dup_exhaustiveness.py                   |   4 +-
 tests/test_gate_cache.py                           |   8 +-
 tests/test_gates.py                                |  20 +-
 tests/test_refactor.py                             |   6 +-
 tests/test_telemetry.py                            |   7 +-
 tests/test_ticket_land.py                          |  20 +-
 tests/test_ticket_work_and_land_finish.py          |  20 +-
 tests/test_tickets_brief.py                        |   4 +-
 tests/test_tickets_evidence_cli.py                 |   4 +-
 tests/test_vet.py                                  |   9 +-
 tests/test_vet_capability.py                       |   4 +-
 tests/unit/gates/test_doc011.py                    |   4 +-
 tests/unit/perf/test_harness_main_branches.py      |   4 +-
 .../unit/perf/test_serial_pools_import_failure.py  |   4 +-
 tests/unit/strata/test_audit.py                    |   9 +-
 tests/unit/strata/test_compliance.py               |  28 +-
 tests/unit/strata/test_design_load.py              |   7 +-
 tests/unit/strata/test_native_test.py              |   8 +-
 tests/unit/strata/test_sync_may.py                 |   9 +-
 tests/unit/test_app_runners_batch6.py              |   4 +-
 tests/unit/test_check_native_cargo_runners.py      |  14 +
 tests/unit/test_check_ts_runners.py                |   8 +-
 tests/unit/test_daemon_proxy_error_paths_t1457.py  |  28 +-
 tests/unit/test_extract_native.py                  |   3 +-
 tests/unit/test_lang_primitives.py                 |   4 +-
 tests/unit/test_logging_module.py                  |   4 +-
 tests/unit/test_wire_autouse_fixture.py            |  20 +-
 tickets.md                                         |  52 +-
 50 files changed, 536 insertions(+), 529 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestDirectiveCarrier::test_attached_waiver_moves_with_symbol` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 362 warning(s), 799 waived
- error-findings: none (measured, zero errors)
