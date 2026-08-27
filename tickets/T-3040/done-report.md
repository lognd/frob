## Done report

Changed:
- tests/system/test_system.py (test_cycle_no_cycle_exits_zero,
  test_cycle_detects_cycle, test_cycle_suggest_flag)

Root cause: TEST fixture drift, not a product defect -- confirmed by
reading src/frob/app/cycle_runner.py's `run()` and `_resolve_project_
root` (T-2588): resolving `<path>` to its enclosing real project root
(nearest `pyproject.toml`, else the enclosing git repo) before measuring
imports is DELIBERATE, load-bearing design -- the whole point of T-2588
was that resolving edges relative to an arbitrary subdirectory instead of
the real project root silently dropped intra-project edges and printed a
false "no cycles found". Refusing (exit 2) rather than silently
measuring the wrong root on an unresolvable path is exactly what T-2588
wanted. The three `test_cycle_*` fixtures build a bare `tmp_path`
containing only a `.py` file -- no `pyproject.toml`, no git repo -- which
genuinely cannot resolve and correctly refuses.

Reproduced directly (both issues): `frob cycle` on a bare tmp_path exits
2 as documented; on a tmp_path WITH a `pyproject.toml` marker added
(minimal real-project fixture), a real cycle exits 1, not 0 -- confirmed
by reading `run()`'s own docstring ("exits 1 (not 0) when real cycles
are found, so this is finally usable in a gate/hook/script"). So
`test_cycle_detects_cycle`/`test_cycle_suggest_flag` carried a SECOND,
independent piece of drift beyond the missing root: both asserted
`returncode == 0` on a found cycle, which was never correct once that
exit-1 contract landed.

FIX: added a `pyproject.toml` marker file to each fixture's tmp_path
(making it a resolvable project root of its own, matching how a real
project is laid out) and corrected the two cycle-found tests' expected
exit code from 0 to 1.

Evidence: (bound via frob ticket evidence)
- tests/system/test_system.py::test_cycle_no_cycle_exits_zero
- tests/system/test_system.py::test_cycle_detects_cycle
- tests/system/test_system.py::test_cycle_suggest_flag

Full tests/system/test_system.py suite (36 tests) passes.

Filed: none -- src/frob/app/cycle_runner.py's behavior is correct as
designed, no product-side follow-up needed.
Gates: frob check --ticket T-3040 -- see land output.

### Changed
```
 tests/system/test_system.py | 20 ++++++++++++++++++--
 tickets/T-3040/ticket.md    |  6 +++++-
 2 files changed, 23 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/system/test_system.py::test_cycle_no_cycle_exits_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_system.py::test_cycle_detects_cycle` (pytest node id, verified passing when recorded)
- `tests/system/test_system.py::test_cycle_suggest_flag` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 69 error(s), 717 warning(s), 862 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bb/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3040, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
