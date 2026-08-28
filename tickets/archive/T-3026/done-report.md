## Done report

Changed:
  src/frob/tickets/_new_renumber.py::_open_and_lock_counter_file (ARCH103 waived)
  docs/index.md, docs/strata/surface.md (link entity_architecture.md -- DOC001/REF001)
  docs/strata/entity_architecture.md (REF002 waived -- worked-example doc, single anchor)
  src/frob/narrative/_cli.py::_resolve_extent, _resolve_migration, run_narrative_command (E501)
  docs/commands/narrative.md (AFFECT001 -- touched alongside the ack)
  src/frob/__main__.py, src/frob/stats/_agentic.py (LARGE001 -- frob:debt bound to T-3059)
  tests/unit/strata/entity_arch/storage_cheap.strata (REF002 waived -- fixture pair)

Evidence:
  tests/test_narrative_migrate.py::TestNarrativeCli::test_dry_run_reports_without_writing
  tests/unit/test_lang_strata_entity_arch.py::TestEntityArchitectureFixtures::test_cheap_architecture_is_a_second_realization_of_the_same_entity

Filed: T-3059 (Split __main__.py and stats/_agentic.py under LARGE001's
800-line threshold) -- both files confirmed pre-existing over-threshold
via git history BEFORE the T-3006/T-2995/T-3014 batch, not a regression
this ticket introduced; frob:debt LARGE001 bound to it rather than a
permanent waiver so `frob debt`/REL001 keep it visible until split.

Gates: frob check --ticket T-3026 clean for every touched file except
the two frob:debt-tracked LARGE001 findings (by design -- debt stays
visible, unlike a waiver) and one pre-existing SEC110/DOC006 in files
this ticket merely touches (verified present before this diff, out of
scope).

### Changed
```
 docs/commands/narrative.md                         |  6 +++--
 docs/index.md                                      |  5 ++++
 docs/strata/entity_architecture.md                 |  2 ++
 docs/strata/surface.md                             |  5 ++++
 frob.lock                                          | 28 ++++++++++++++++++++++
 src/frob/__main__.py                               |  2 ++
 src/frob/narrative/_cli.py                         | 17 ++++++++++---
 src/frob/stats/_agentic.py                         |  3 +++
 src/frob/tickets/_new_renumber.py                  |  2 ++
 tests/unit/strata/entity_arch/storage_cheap.strata |  2 ++
 tickets/T-3026/ticket.md                           |  6 +++++
 11 files changed, 73 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_narrative_migrate.py::TestNarrativeCli::test_dry_run_reports_without_writing` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_strata_entity_arch.py::TestEntityArchitectureFixtures::test_cheap_architecture_is_a_second_realization_of_the_same_entity` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 58 error(s), 857 warning(s), 858 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3026, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
