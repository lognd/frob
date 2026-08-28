## Done report

Changed:
- src/frob/mutate/__init__.py::_run_mutants

Root cause: PRODUCT bug, confirmed by reading T-3015's landed diff
(746e77f2a, guarded_subprocess_run raises subprocess.TimeoutExpired
uncaught instead of returning Err) -- it changed
`guarded_subprocess_run` to return `Err(ProcessGuardError.Timeout)`
instead of raising `subprocess.TimeoutExpired`. `_run_mutants`'s
`except subprocess.TimeoutExpired: killed += 1; continue` branch (a mutant
that hangs the test suite is legitimate kill evidence) can no longer
catch that outcome -- it now falls into the generic
`if guarded.is_err: ... return Err(MutateError.ExecDisabled)` branch,
which aborts the ENTIRE mutation run instead of scoring one mutant killed
and continuing. This is a real functional regression, exactly as T-3039
described, not stale test fragility.

FIX: inside the existing `if guarded.is_err:` branch, check
`guarded.danger_err is ProcessGuardError.Timeout` first (score killed,
continue) before falling through to the ExecDisabled-abort path. Left
the (now unreachable via this call site) `except subprocess.
TimeoutExpired` branch in place as defense-in-depth documentation, per
its own updated comment.

Evidence: (bound via frob ticket evidence, designated repro)
- tests/test_mutate.py::test_run_mutants_scores_a_timeout_as_killed_and_continues
  (DESIGNATED REPRO, confirmed FAILED_AT_PARENT against 704a05fbc, the
  test-only commit, before the fix commit e365c8107)
- tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning
  (existing ExecDisabled-abort test, unchanged, still passes)

Full tests/test_mutate.py suite (19 tests) passes.

Filed: none.
Gates: frob check --ticket T-3039 -- see land output.

### Changed
```
 src/frob/mutate/__init__.py | 18 +++++++++++++-
 tests/test_mutate.py        | 57 ++++++++++++++++++++++++++++++++++++++++++++-
 tickets/T-3039/ticket.md    |  9 +++++--
 3 files changed, 80 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_mutate.py::test_run_mutants_scores_a_timeout_as_killed_and_continues` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 66 error(s), 688 warning(s), 861 waived
- error-findings: ARCH001@src/frob/mutate/__init__.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3039, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py
