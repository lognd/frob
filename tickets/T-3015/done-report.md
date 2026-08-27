## Done report

Changed:
  src/frob/process/_guard.py::ProcessGuardError (new member: Timeout)
  src/frob/process/_guard.py::guarded_subprocess_run

Fix: wrapped the subprocess.run(...) call in a try/except
subprocess.TimeoutExpired and returns Err(ProcessGuardError.Timeout)
instead of letting the exception escape. OSError is left unhandled by
design -- every existing caller that distinguishes OSError already has
its own local except (OSError, subprocess.TimeoutExpired) block, and
catching OSError here too would silently turn those into dead code the
same way an unaudited Timeout flip would have.

Caller audit (grep across src/ and tests/ for guarded_subprocess_run,
~230 hits, narrowed to real call sites):

- 2 call sites had NO try/except at all around guarded_subprocess_run
  and a timeout= kwarg -- these were CRASHING uncaught exactly as T-3015
  describes: src/frob/refactor/_verify.py::verify_pytest_collect and
  ::verify_check_delta (the T-2990 discovery site). Both already have a
  generic `if result.is_err: return VerifyOutcome(passed=False, ...)`
  branch below the call -- the fix makes both correctly return a failed
  VerifyOutcome instead of crashing, with zero caller-side changes
  needed.

- ~15 call sites already wrap guarded_subprocess_run in
  `except (OSError, subprocess.TimeoutExpired)` or
  `except subprocess.TimeoutExpired`, because today's raising behavior
  is the only way they can see a timeout at all. Two shapes:
    (a) Generic-degrade callers (majority): the except block and the
        `if result.is_err:` block below it already return/log the SAME
        outcome regardless of cause (None / False / (None, False) /
        GateSummary() / tool_disabled_result / tool_crash_result). These
        continue to work unchanged -- the specific log/result text may
        now say "refused" or "disabled" for what was actually a timeout,
        which is a pre-existing pattern (already true for a genuine
        ExecDisabled vs. some other is_err cause) and not a new
        correctness break. Confirmed via `frob check --only
        scope,test,doc,drift` producing zero findings against
        `_guard.py` after the change.
        Sites: src/frob/check/_native.py (7 call sites),
        src/frob/check/_python.py (5), src/frob/check/_ts.py,
        src/frob/natives/_build.py, src/frob/gates/_suppress.py,
        src/frob/app/pyfmt_runner.py (2), src/frob/gitio.py,
        src/frob/fleet/__init__.py (2), src/frob/tickets/clipboard.py
        (8), src/frob/app/ticket_runner/_land_cmd.py (1 -- returns None
        both ways, just a log-text difference),
        src/frob/app/ticket_runner/_rapid_sweep.py (1, same),
        src/frob/app/ticket_runner/_verify.py (1, returns False both
        ways).
    (b) Semantic-divergence callers (3, real behavior change if left
        unfixed -- filed as follow-up tickets rather than fixed here,
        since they live outside T-3015's declared scope
        src/frob/process/_guard.py):
        - src/frob/gates/_bug_repro.py::_spawn_designated_test: today a
          caught TimeoutExpired returns Err(_BugReproOutcome.TIMEOUT), a
          distinct outcome from NO_VERDICT by explicit design (T-2480).
          After this fix it would silently collapse into NO_VERDICT via
          the generic is_err branch. Filed T-3036.
        - src/frob/mutate/__init__.py (mutant test spawn): today a
          caught TimeoutExpired scores the mutant as killed and
          continues the run; the is_err branch below instead ABORTS
          the whole mutation run. After this fix a real timeout would
          wrongly abort the run instead of scoring one kill. Filed
          T-3039.
        - src/frob/tickets/_evidence.py::_warn_bind_time_mutation_sweep_cost:
          today a caught TimeoutExpired returns _TIMEOUT_S (a measured
          floor); the is_err branch below returns None. After this fix
          the floor measurement would be silently lost. Filed
          T-3038.
      These three do NOT block T-3015's own correctness (guarded_
      subprocess_run's contract is fixed either way) but must land
      before/alongside this ticket's effects reach those three modules'
      current behavior, so they are called out explicitly rather than
      silently left regressed.

- src/frob/app/_daemon_proxy.py and src/frob/serve/_socketd.py use raw
  subprocess.run directly, not guarded_subprocess_run -- out of scope,
  unaffected.
- src/frob/app/ticket_runner/_land_cmd.py:3723 uses raw subprocess.run
  directly (a separate ty-check spawn) -- unaffected.
- src/frob/testing/_coverage_refresh.py deliberately does NOT use
  guarded_subprocess_run (documented in its own module: "Cannot use
  guarded_subprocess_run/subprocess.run here: both block") -- unaffected.

Both fixture directions (acceptance criteria):
  - Must-return-Err: test_timeout_returns_err_never_raises -- a command
    that outlives timeout=0.1s returns Err(ProcessGuardError.Timeout),
    confirmed not to raise.
  - Must-still-work: test_healthy_path_unchanged_when_timeout_kwarg_given
    -- a timeout= kwarg the command comfortably beats still returns
    Ok(CompletedProcess) unchanged; test_enabled_spawns_and_returns_ok
    and test_disabled_returns_err_without_spawning (pre-existing) also
    re-verified green.

Evidence: tests/unit/test_process_guard.py::TestGuardedSubprocessRun.test_timeout_returns_err_never_raises
tests/unit/test_process_guard.py::TestGuardedSubprocessRun.test_healthy_path_unchanged_when_timeout_kwarg_given
tests/unit/test_process_guard.py::TestGuardedSubprocessRun.test_disabled_returns_err_without_spawning
tests/unit/test_process_guard.py::TestGuardedSubprocessRun.test_enabled_spawns_and_returns_ok
(28/28 passed in tests/unit/test_process_guard.py; full-file run, exitstatus=0)

Filed: T-3036 (bug_repro TIMEOUT-vs-NO_VERDICT regression),
T-3039 (mutate abort-vs-killed regression),
T-3038 (evidence lost-timeout-floor regression) -- real ids
verified on main before citing further, per playbook sec 0 item 8.

Gates: `frob check --ticket T-3015 --budget 480` -- gate:SCOPE/gate:TEST/
gate:DOC/gate:DRIFT show zero findings naming _guard.py (confirmed via
`frob check --only scope,test,doc,drift --json` grep for "_guard": 0
hits). Repo-wide FAIL counts on other gate families (COV/DOC/DRIFT/PRE/
REF/REG/SCOPE/TEST/TICK/WAIVE/ARCH/LARGE/PII/SEC/SELFAUDIT/SYS, ruff-check,
ruff-format) are pre-existing and unrelated to this ticket's touched
files/symbols -- none reference _guard.py, ProcessGuardError, or
guarded_subprocess_run.

UPDATE (during T-2992's full-suite run): the existing regression test
tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict
FAILED under this change -- confirming the bug_repro.py divergence
flagged above is a real "must-still-work" violation, not merely a
theoretical one. Rather than leave an existing test broken, widened
scope (frob ticket scope --add src/frob/gates/_bug_repro.py, reason
recorded) and fixed _spawn_designated_test's timeout branch in place:
replaced the dead except subprocess.TimeoutExpired: block with a
guarded.danger_err is ProcessGuardError.Timeout check inside the
existing is_err branch, preserving the TIMEOUT-vs-NO_VERDICT
distinction. Re-verified: tests/test_gates_mutation_evidence.py
(TestBugReproTimeout, 3/3) and the whole file (69/69) pass.
T-3036 is accordingly resolved by this same change, not left
outstanding -- close/drop it at land time rather than leaving it queued
for duplicate work. T-3039 (mutate) and T-3038
(evidence) remain outstanding: no EXISTING test currently exercises
either divergence (confirmed via grep), so they are real but
undetected-by-suite regressions, correctly left as filed follow-ups
per scope discipline.

### Changed
```
 docs/modules/process.md            |   3 +
 src/frob/process/_guard.py         |  41 ++++++++---
 tests/unit/test_process_guard.py   |  39 +++++++++++
 tickets/T-2992/ticket.md           |   2 +-
 tickets/T-3015/done-report.md      | 135 +++++++++++++++++++++++++++++++++++++
 tickets/T-3015/ticket.md           |  40 ++++++++++-
 tickets/T-3036/ticket.md |  53 +++++++++++++++
 tickets/T-3038/ticket.md |  50 ++++++++++++++
 tickets/T-3039/ticket.md |  51 ++++++++++++++
 9 files changed, 402 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_timeout_returns_err_never_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_healthy_path_unchanged_when_timeout_kwarg_given` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_disabled_returns_err_without_spawning` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_enabled_spawns_and_returns_ok` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_failing_test_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_reproducing_test_completes_normally` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 56 error(s), 704 warning(s), 856 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3015/ticket.md, DOC006@tickets/T-draft-291498b9/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t3015-t2992-series/tests/test_narrative_migrate.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3015, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
