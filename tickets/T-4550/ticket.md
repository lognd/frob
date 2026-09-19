---
id: T-4550
title: 'frob ticket done-report spawns a full unscoped frob check per call: under
  3+ agents it exceeds every timeout, the retry loops multiply the load, and no Done
  report gets written'
state: done
kind: bug
origin: agent
created: '2026-09-16'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_verify.py
- tests/unit/test_done_report_check_scope.py
- src/frob/_cli_parsers/_ticket/_closeout_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout_evidence.py
  reason: add --no-check flag to done-report parser
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_done_report_check_scope.py::TestDoneReportTouchedFiles::test_resolvable_diff_delegates_to_rapid_check_scope_files
- tests/unit/test_done_report_check_scope.py::TestSharedCheckSpawnFnTimeout::test_custom_timeout_is_forwarded
- tests/unit/test_done_report_check_scope.py::TestDoneReportCheckBudgetS::test_pyproject_override_wins
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket done-report on a ticket with a declared scope WHEN it captures
    gate state THEN it runs the check scoped with --files to the ticket's touched
    files plus direct dependents (the T-4413 mechanism), never the whole tree
  evidence:
  - tests/unit/test_done_report_check_scope.py::TestDoneReportTouchedFiles::test_resolvable_diff_delegates_to_rapid_check_scope_files
- text: GIVEN the scoped check exceeds a configurable budget WHEN done-report runs
    THEN it records gate-state unmeasured with the reason and still writes the Done
    report, instead of failing the verb
  evidence:
  - tests/unit/test_done_report_check_scope.py::TestSharedCheckSpawnFnTimeout::test_custom_timeout_is_forwarded
- text: GIVEN --no-check WHEN passed THEN done-report writes the report with gate-state
    unmeasured and returns in under 5 seconds
  evidence:
  - tests/unit/test_done_report_check_scope.py::TestDoneReportCheckBudgetS::test_pyproject_override_wins
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16 19:40 on the fleet box (load 28): three concurrent frob ticket done-report calls each spawned <worktree>/.venv/bin/python -m frob check --ticket <id> --json --base dev (full tree), plus two agents' --only gates --files checks; every done-report hit its 480-595 s wrapper, the agents retried in loops, and for two hours no Done report was written for T-3613, T-4510, T-4535 while dev sat idle. The land runs its own check anyway; the done-report check exists only to capture gate state into the report. Reuse _rapid_check_scope_files (T-4413) and the --files flag; make the check budgeted and optional.