## Done report

Changed:
  src/frob/verify/_quarantine.py::_RUFF_DETERMINISTIC_AUTOFIX_RULES
  src/frob/verify/_quarantine.py::_trivial_autofixable_rules
  src/frob/verify/_quarantine.py::_is_trivial_unattributed
  src/frob/verify/_quarantine.py::raise_quarantine (severity filter added to body)
  src/frob/gates/_waive.py::_KNOWN_GATE_RULES (F401 registered)
  docs/modules/tickets-verify-sweep.md (Proportional to the trigger section)

Evidence:
  tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_trivial_unattributed_ruff_finding_alone_does_not_raise
  tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_trivial_unattributed_unused_import_finding_does_not_raise
  tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_attributed_trivial_finding_still_raises
  tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_unattributed_non_trivial_finding_still_raises
  tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_mixed_batch_drops_only_the_trivial_unattributed_finding
  tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_unattributed_frob_gate_autofix_rule_is_deliberately_not_exempt

The land-refusal surfacing acceptance item (naming quarantine, the
undisposed finding, and the dispose command) was already shipped by
T-2049 (done) -- `_land_cmd._quarantine_override_ceilings`'s ERROR line
and `_quarantine_undisposed_summary`; verified present on main, not
re-implemented here.

Filed: none (mixed-path-shape investigation reported in the series
summary, judged not to need a new ticket -- T-2312 already ships a
diagnostic hint for it).

Gates: frob check --ticket T-3025 clean for every touched file (162
pre-existing repo-wide errors unrelated to this change remain, per
--ticket's own scoping note). frob:waive LARGE001 added at
src/frob/verify/_quarantine.py:3, reason inline.

### Changed
```
 docs/modules/tickets-verify-sweep.md |  18 +++++
 frob.lock                            |  20 +++++-
 src/frob/gates/_waive.py             |   5 ++
 src/frob/verify/_quarantine.py       |  95 +++++++++++++++++++++++++-
 tests/unit/verify/test_quarantine.py | 127 +++++++++++++++++++++++++++++++++++
 tickets/T-3025/ticket.md             |  47 ++++++++++++-
 6 files changed, 309 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_trivial_unattributed_ruff_finding_alone_does_not_raise` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_trivial_unattributed_unused_import_finding_does_not_raise` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_attributed_trivial_finding_still_raises` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_unattributed_non_trivial_finding_still_raises` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_mixed_batch_drops_only_the_trivial_unattributed_finding` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_unattributed_frob_gate_autofix_rule_is_deliberately_not_exempt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 61 error(s), 853 warning(s), 875 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/entity_architecture.md, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3015/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3025/src/frob/narrative/_cli.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3025, REF001@docs/strata/entity_architecture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@tests/unit/strata/entity_arch/storage_cheap.strata, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
