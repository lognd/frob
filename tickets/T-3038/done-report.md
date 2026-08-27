## Done report

Changed:
- src/frob/tickets/_evidence.py::_measured_bind_time_evidence_wall_clock_s

Root cause: PRODUCT bug, confirmed by reading T-3015's landed diff
(746e77f2a) -- it changed `guarded_subprocess_run` to return `Err(
ProcessGuardError.Timeout)` instead of raising `subprocess.
TimeoutExpired`. `_measured_bind_time_evidence_wall_clock_s`'s `except
subprocess.TimeoutExpired: return _TIMEOUT_S` branch (the documented
"real cost is >= this, use it as the measured floor" intent) can no
longer catch that outcome -- it falls into the generic `if guarded.
is_err: return None` branch instead, silently discarding the floor
measurement. Exactly as T-3038 described.

FIX: inside the existing `if guarded.is_err:` branch, check
`guarded.danger_err is ProcessGuardError.Timeout` first (return
`_TIMEOUT_S`) before the generic `None` fallback. Left the (now
unreachable via this call site) `except subprocess.TimeoutExpired`
branch in place, matching T-3039's sibling fix in frob.mutate.

Evidence: (bound via frob ticket evidence, designated repro)
- tests/test_tickets_mutation_evidence.py::TestMeasuredBindTimeEvidenceWallClockS::test_timeout_err_returns_the_timeout_floor
  (DESIGNATED REPRO, confirmed FAILED_AT_PARENT against ee6eb870a, the
  test-only commit, before the fix commit e7a26271e)
- tests/test_tickets_mutation_evidence.py::TestMeasuredBindTimeEvidenceWallClockS::test_oserror_still_returns_none
  (new, proves the existing OSError-returns-None behavior is unchanged)
- tests/test_tickets_mutation_evidence.py::TestMeasuredBindTimeEvidenceWallClockS::test_exec_disabled_still_returns_none
  (new, proves the existing ExecDisabled-returns-None behavior is
  unchanged)

Full tests/test_tickets_mutation_evidence.py suite (21 tests, 1 pre-
existing skip) passes.

Noted but NOT fixed (out of scope): tests/test_ticket_evidence.py::
TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree
fails independently on this tree -- same T-2394 empty-scope fixture-
drift family as T-3037, already tracked under T-3080 (T-3037's own
residue ticket). Confirmed still failing before AND after this ticket's
change; unrelated to the timeout-floor fix.

Filed: none new (widened this ticket's own scope via `frob ticket scope
--add tests/test_tickets_mutation_evidence.py` to add the regression
test, since T-3038 declared no test file scope originally).
Gates: frob check --ticket T-3038 -- see land output.

### Changed
```
 src/frob/tickets/_evidence.py           |  8 +++-
 tests/test_tickets_mutation_evidence.py | 78 +++++++++++++++++++++++++++++++++
 tickets/T-3038/ticket.md                | 16 ++++++-
 3 files changed, 99 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_mutation_evidence.py::TestMeasuredBindTimeEvidenceWallClockS::test_oserror_still_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestMeasuredBindTimeEvidenceWallClockS::test_exec_disabled_still_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestMeasuredBindTimeEvidenceWallClockS::test_timeout_err_returns_the_timeout_floor` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 71 error(s), 760 warning(s), 861 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3088/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bb/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3038, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
