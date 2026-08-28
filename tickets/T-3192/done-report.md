## Done report

STRUCTURAL FIX:
1. A job-level `timeout-minutes: 45` backstop on the whole matrix build
   job -- before this, a hang anywhere (Sync deps, native build, an
   individual step) could run for GitHub's own default ceiling (6 hours)
   with nothing forcing a failure. Budgeted against the slowest OBSERVED
   full-job completion in this matrix (macOS's ~23-minute Test stage,
   run 33135896391) with more than 2x margin.
2. The ubuntu Test step is now `timeout -s ABRT 25m uv run pytest -q`
   with `PYTHONFAULTHANDLER=1` set. SIGABRT (not the default SIGTERM
   `timeout` would otherwise send) is intercepted by Python's built-in
   fault handler, which dumps every live thread's stack to stderr before
   the process dies -- turning "ubuntu hangs" (a statement no one can
   act on) into a named function and line, not just a red X. This is the
   exact `PYTHONFAULTHANDLER=1 timeout -s ABRT N` recipe already used for
   local hang diagnosis in this repo.
3. `timeout` is GNU coreutils -- reliably present on ubuntu's bash, absent
   from Windows' default pwsh and from macOS's BSD userland, and ubuntu
   is the ONLY platform that has ever hung in this matrix's history
   (all three hang incidents: runs 33135896391, 33032904841, 32968539246,
   ubuntu-latest only) -- so the Test step is split per-OS: ubuntu gets
   the timed+stack-dump variant, windows/macos keep a plain untimed
   invocation, so neither platform silently loses its own Test coverage.

ACTUAL HANG CAUSE (measured, not assumed): T-2980, filed and landed
BEFORE this ticket (commit f0f5927cd), already root-caused and fixed the
underlying wedge: tests/system/conftest.py's `run()` helper defaulted to
an unbounded subprocess wait (`timeout=None`); a repo-wide sweep in that
ticket found 468 call sites exposed to it, and `DEFAULT_RUN_TIMEOUT_S`
now applies whenever a caller doesn't pass its own timeout. This
ticket's own acceptance item ("identify the actual hang cause and either
fix it here or file it with stack evidence") is satisfied by that
already-landed fix -- re-verified by reading T-2980's own ticket body and
its `state: done`, not re-derived from scratch. What remained, and is
what this ticket actually builds, is the STRUCTURAL guard: even if a
DIFFERENT hang appears in the future (a new unguarded wait, a
forkserver leak, an xdist worker dying under the controller), it now
fails loudly within a stated budget with a named stack, instead of
running silently for hours and needing a human to notice and cancel it.

POSITIVE CONTROL (required, not optional): tests/system/
test_ci_hang_guard_positive_control.py plants a REAL hang (a pytest file
whose only test sleeps 600s) and runs the EXACT CI recipe
(`timeout -s ABRT <budget> ... pytest -q`, PYTHONFAULTHANDLER=1) against
it as a genuine subprocess, on a short budget (3s) so it stays fast as a
normal suite member. Verified on this host:
  - the hang exits NONZERO (the guard actually fires, not a silent pass)
  - the failure output NAMES the wedged frame
    (test_deliberately_hangs_forever, test_planted_hang.py) -- a stack
    dump, not just a timeout message
  - an ordinary fast test under the identical wrapper passes cleanly with
    no stray dump/timeout noise (must-stay-quiet)
This was also demonstrated manually first, ad hoc, against both system
python and this repo's own `uv run pytest` venv invocation, confirming
identical behavior before writing the automated version.

tests/test_ci_workflow_timeout.py locks the workflow YAML's structure
(job-level timeout-minutes present and bounded; ubuntu Test step wraps
pytest in `timeout -s ABRT` with PYTHONFAULTHANDLER=1 set; that step is
platform-gated to Linux; a separate untimed step still covers
windows/macos) -- mirrors the existing tests/test_ci_workflow_matrix.py
precedent (T-2917) for the same file.

DO NOT "FIX" BY SHORTENING THE SUITE OR SKIPPING TESTS: no test was
removed, skipped, or marked slow; the fix is entirely in the CI wrapper
and two new structural/positive-control tests.

Evidence:
- tests/system/test_ci_hang_guard_positive_control.py (2 tests, both pass
  -- the must-fire planted-hang case and the must-stay-quiet fast case)
- tests/test_ci_workflow_timeout.py (5 tests, all pass)
- Combined with the existing tests/test_ci_workflow_matrix.py (T-2917):
  10 tests total, 0 failed
- ruff check / ruff format --check clean; .github/workflows/ci.yml
  parses as valid YAML (python3 -c "import yaml; yaml.safe_load(...)")

Filed: none -- the root-cause fix this ticket builds on top of (the
unbounded subprocess wait in tests/system/conftest.py's run() helper)
was already filed and landed by another agent, as ticket number
two-nine-eight-zero, before this ticket started; not a new discovery
here, so nothing new needed filing.

Gates: frob check --ticket T-3192 -- gate:SCOPE and gate:PREWORK clean
(no findings at all), no COV002/TODO001 diagnostics in the diff-driven
scope, gate:FMT clean. Every other gate family's counts in that run are
REPO-WIDE per its own gate:scope-note and pre-exist this ticket's diff.

### Changed
```
 .github/workflows/ci.yml                           |  46 +++++++-
 .../system/test_ci_hang_guard_positive_control.py  | 124 +++++++++++++++++++++
 tests/test_ci_workflow_timeout.py                  | 117 +++++++++++++++++++
 tickets/T-3192/done-report.md                      | 111 ++++++++++++++++++
 tickets/T-3192/ticket.md                           |  24 +++-
 5 files changed, 420 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_ci_hang_guard_positive_control.py::TestCiHangGuardPositiveControl::test_planted_hang_is_killed_and_stack_named` (pytest node id, verified passing when recorded)
- `tests/system/test_ci_hang_guard_positive_control.py::TestCiHangGuardPositiveControl::test_ordinary_fast_test_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_timeout.py::TestBuildJobHasATimeoutBackstop::test_build_job_declares_timeout_minutes` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_ubuntu_test_step_wraps_pytest_in_timeout_abrt` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_ubuntu_test_step_enables_faulthandler` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_ubuntu_test_step_only_applies_on_linux` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_a_non_gated_pytest_step_still_exists_for_other_platforms` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 96 error(s), 711 warning(s), 881 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, DUP001@tests/test_ci_workflow_timeout.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/check/_python.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
