## Done report

Changed:
- tests/system/conftest.py::run (Popen with start_new_session=True +
  preexec_fn=arm_parent_death_signal on POSIX; os.killpg on
  TimeoutExpired; Windows keeps the pre-fix subprocess.run shape,
  since preexec_fn/start_new_session/killpg are POSIX-only and
  PDEATHSIG has no Windows equivalent)

Two independent mechanisms, matching the ticket's own PLAN section
verbatim:
1. `preexec_fn=arm_parent_death_signal` (reused unchanged from
   frob.process._reap, the same helper T-2849 already uses for
   forkserver self-arming -- no second "die with my parent"
   implementation) -- closes the HARD-kill case: pytest-timeout's
   thread method calls os._exit(1) on the whole worker on an
   outer-timeout hit, which never runs run()'s own except block, so
   nothing in Python gets a chance to kill the child. Imported at
   MODULE scope so preexec_fn is an already-resolved callable, not a
   post-fork import (avoids the classic fork+thread import-lock
   deadlock risk, since pytest-timeout's own timeout thread is
   exactly such a thread in this process).
2. `start_new_session=True` + `os.killpg` on TimeoutExpired -- closes
   the GRANDCHILD case named directly in the ticket's plan:
   subprocess.run's own default timeout handling kills only the
   tracked child pid, never descendants a frob invocation spawns
   itself (a chunked check's own subprocess calls, a forkserver
   pool).

Demonstrated (not simulated): TestRunHelperOrphanCleanup::
test_timeout_kills_the_whole_process_group_not_just_the_direct_child
monkeypatches conftest.FROB to a helper script that spawns its own
real child process (a `sleep 300` stand-in, mirroring T-2991's own
local repro), writes that grandchild's real pid to a file, then lets
run() time out. Test asserts the grandchild pid is actually dead
(os.kill(pid, 0) raises ProcessLookupError) after run()'s
TimeoutExpired handling runs -- this is the exact class of process
the real CI incident's "Terminate orphan process" lines named.
test_run_arms_pdeathsig_and_uses_a_new_session pins the Popen kwargs
directly (preexec_fn is arm_parent_death_signal, start_new_session is
True) so a future refactor that silently drops either cannot pass
even if the timing-based test above happens not to catch it.

Verified no regression: all 4 pre-existing tests in
tests/system/test_run_helper_env_leak.py still pass unchanged,
including test_run_expiry_raises_a_named_loud_error (the exact
TimeoutExpired->RuntimeError contract T-2980 established). Ran
tests/system/test_cli_check.py as a broader smoke check; 8 failures
there are PRE-EXISTING and unrelated to this diff -- confirmed by
running the identical failing tests against the unmodified
conftest.py (git checkout --) and reproducing the SAME failures
(a host-wide "N other check(s) already running" concurrency refusal
from live fleet contention, and gate:PRE/REF/SCOPE errors on a
from-scratch /tmp git repo with no ticket branch -- both unrelated to
run()'s subprocess-launch mechanics).

Evidence:
- tests/system/test_run_helper_env_leak.py::TestRunHelperOrphanCleanup::test_timeout_kills_the_whole_process_group_not_just_the_direct_child
- tests/system/test_run_helper_env_leak.py::TestRunHelperOrphanCleanup::test_run_arms_pdeathsig_and_uses_a_new_session

Filed: none.

Gates: `frob check --json --ticket T-2991` clean (0 errors) for
tests/system/conftest.py and tests/system/test_run_helper_env_leak.py.
`frob check --only lint` clean for both files after a ruff-format
pass.

### Changed
```
 tests/system/conftest.py                 | 108 ++++++++++++++++++++++++++----
 tests/system/test_run_helper_env_leak.py | 109 +++++++++++++++++++++++++++++++
 tickets/T-2991/ticket.md                 |  19 +++++-
 3 files changed, 224 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/system/test_run_helper_env_leak.py::TestRunHelperOrphanCleanup::test_timeout_kills_the_whole_process_group_not_just_the_direct_child` (pytest node id, verified passing when recorded)
- `tests/system/test_run_helper_env_leak.py::TestRunHelperOrphanCleanup::test_run_arms_pdeathsig_and_uses_a_new_session` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 57 error(s), 505 warning(s), 853 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DUP001@tests/system/conftest.py, I001@/home/logan/projects/frob/.claude/worktrees/t2991/tests/test_narrative_migrate.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2991, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/gates/_narrative_blocks.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md
