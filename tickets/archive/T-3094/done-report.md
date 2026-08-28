## Done report

Changed:
- src/frob/tickets/_worktree_guard.py::apply_agent_env
- src/frob/tickets/_worktree_guard.py::warn_if_xdist_bound_missing

Diagnosis (before any fix): _bounded_xdist_workers/agent_env_exports
compute the T-2221 fleet-aware xdist bound correctly -- a live fleet
context always produced a real value, ruling out failure mode (d), a
detection bug. The broken link is failure mode (b): agent_env_exports's
only consumers anywhere in the codebase (frob agent env's CLI, and
ticket work's hint line) both only ever PRINT the export as shell text
for a human/agent to eval. Nothing anywhere calls os.environ[...] = ...
with the result. Confirmed live: sourcing the export via
eval "$(uv run frob agent env <path>)" sets the var in that one shell,
but the next, separate command invocation in this dispatched agent's own
harness does not inherit it -- shell state does not persist between
commands here, so even a compliant eval never reaches the process that
later runs pytest.

Fix: apply_agent_env(root) mutates the CURRENT process's os.environ
directly (in addition to returning the dict agent_env_exports already
returned), so any in-process subprocess.run/Popen spawn of pytest
inherits the bound automatically -- no eval hop needed. Verified via the
exact evidence standard the ticket specifies: a real child process
spawned the ordinary way, its LIVE /proc/<pid>/environ read while
running, confirmed to carry PYTEST_XDIST_AUTO_NUM_WORKERS=3 after
apply_agent_env ran with 3 live peer leases present (against a throwaway
fake repo, not the real fleet's lease store). warn_if_xdist_bound_missing
is the loud half: logs ERROR when a fleet context is detected but the
bound is absent from the CURRENT process's environment.

Does NOT retroactively fix a raw shell pytest an agent types in a LATER,
unrelated command -- that class of gap still needs either the eval
mechanism or (residue, below) apply_agent_env/warn_if_xdist_bound_missing
wired into frob's own pytest-spawn call sites, which spans files outside
this ticket's single-file scope.

Evidence:
- tests/test_worktree_guard.py::TestApplyAgentEnv::test_mutates_current_process_env_under_fleet_context
- tests/test_worktree_guard.py::TestApplyAgentEnv::test_must_stay_quiet_no_fleet_context_leaves_env_unset
- tests/test_worktree_guard.py::TestApplyAgentEnv::test_child_subprocess_inherits_the_bound
- tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_fire_fleet_context_with_bound_missing_logs_error
- tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_bound_present_no_log
- tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_no_fleet_context_no_log

Test-first proof (manual, pre-commit): before either new function
existed, pytest tests/test_worktree_guard.py failed collection with
ImportError: cannot import name 'apply_agent_env' -- confirmed FAILED at
the parent commit. --designate-repro could not auto-verify this
post-commit because the test and fix landed in the same commit (T-2025's
documented systematic limitation for a newly-added test); the fail-at-
parent proof above was captured manually before committing instead.

Filed: T-3099 -- wire apply_agent_env/warn_if_xdist_bound_missing
into the actual pytest-spawn call sites (_verify.py, _collect.py,
_coverage_refresh.py, mutate_runner.py, perf_runner.py, CLI main,
agent-playbook.md) -- out of scope here (multiple files outside
src/frob/tickets/_worktree_guard.py).

Gates: frob check --ticket T-3094 to run at land.

### Changed
```
 docs/modules/tickets-data-storage.md |  37 ++++++++++
 src/frob/tickets/_worktree_guard.py  | 103 +++++++++++++++++++++++++++
 tests/test_worktree_guard.py         | 131 +++++++++++++++++++++++++++++++++++
 tickets/T-3094/ticket.md             |  22 +++++-
 tickets/T-3099/ticket.md   |  74 ++++++++++++++++++++
 5 files changed, 366 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestApplyAgentEnv::test_mutates_current_process_env_under_fleet_context` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestApplyAgentEnv::test_must_stay_quiet_no_fleet_context_leaves_env_unset` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestApplyAgentEnv::test_child_subprocess_inherits_the_bound` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_fire_fleet_context_with_bound_missing_logs_error` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_bound_present_no_log` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_no_fleet_context_no_log` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 80 error(s), 761 warning(s), 862 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@src/frob/tickets/_land_compose.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_land_compose.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bk/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3094, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE001@src/frob/tickets/_worktree_guard.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
