## Done report

(rollup close)

Measured against the real repo today, not child-count alone:

- The motivating bug (T-1614, a runs_last ticket, structurally
  unreachable while 83+ queued tickets existed) is itself state: done
  (tickets/archive/T-1614). Verified via `frob ticket show T-1614`.
- The exact positive control this epic exists to make true --
  `test_milestoned_runs_last_doable_once_same_milestone_work_terminal`
  and the sibling carve-out
  `test_runs_last_sibling_carve_out_preserved_within_a_milestone` -- both
  pass: `uv run pytest -q tests/test_tickets_milestone_runs_last.py
  tests/test_gates_milestone.py` -> 35 passed, 0 failed.
- Semver ordering is a real ordered comparison, not a string compare:
  `tests/test_tickets_milestone_sort.py` explicitly asserts "1.10.0" >
  "1.9.0" (`test_...backwards`) and passes: 11 passed, 0 failed.
- MILE001-004 gates are real, wired code (src/frob/gates/_milestone.py,
  registered in src/frob/gates/__init__.py under "frob:enforces
  CHK-GATE-MILE001/003" etc.), not just documented.
- M6 (REL001 open-milestone-cut refusal) is real: found at
  src/frob/gates/_debt_deprecated.py::_release_open_milestone_violations,
  wired into release_gate, with a positive control (open ticket in the
  cut milestone fires) and three negative controls (different milestone,
  terminal ticket, no open tickets) all passing per
  tickets/archive/T-2581/done-report.md.
- All seven children (T-2574, T-2576..T-2581 / M1-M6) are archived,
  state: done.

Verification commands run:
  frob ticket show T-1614 -> [done]
  uv run pytest -q tests/test_tickets_milestone_runs_last.py tests/test_gates_milestone.py
    -> SUITE-RESULT exitstatus=0 collected=35 failed=0
  uv run pytest -q tests/test_tickets_milestone_sort.py
    -> SUITE-RESULT exitstatus=0 collected=11 failed=0
  git grep -n MILE00 -- src/frob/gates
    -> src/frob/gates/_milestone.py (MILE001/003), __init__.py wiring,
       src/frob/gates/_debt_deprecated.py (M6 release gate)

This ticket (T-2573) is an epic with no independent acceptance criteria
array of its own; its claim was verified directly against the motivating
bug plus the mechanism's own positive/negative controls above.

Filed: none new.
Gates: no new code in this closing change.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 62 error(s), 645 warning(s), 863 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py
