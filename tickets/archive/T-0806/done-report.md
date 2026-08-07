## Done report

Root cause (two distinct product bugs, not fixture-only debt):

1. `frob check --json` refuses a stale/cross-worktree ticket lease
   (T-0787's `_refuse_ticket_lease_mismatch`) BEFORE `_run_all_stages`
   ever enters `_stdout_log_ctx`'s `quiet_stdout_logs()` clamp. That
   refusal path (and `--stamp-baseline`/`--stamp-coverage` via
   `_handle_stamp_modes`) calls into `frob.gitio` (branch/lease lookups),
   whose own DEBUG/INFO logging printed straight to stdout, unclamped,
   corrupting `--json`'s stdout payload on a git-less tmp_path fixture
   (`json.loads` failure observed in
   TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage).

2. `frob.gates`'s CPU-bound gates (arch/dup) run in a
   `ProcessPoolExecutor(mp_context=spawn)`. Spawn-context workers are
   FRESH interpreters that re-run `frob.logging.logger._init()` from
   scratch on import -- they never see the PARENT process's in-memory
   `quiet_stdout_logs`/`stdout_log_level` clamp (that only mutates the
   parent's own handler objects), so every worker's default-DEBUG
   per-file parse logging (`dispatching path=...`, `extracted N
   symbols...`, `parsed ...`) printed straight to the shared stdout file
   descriptor it inherits from the parent, regardless of `--json` or
   default (non-`-v`) mode. Root-caused via `strace -f -e trace=write`
   (traced the leaking `write(1, ...)` calls to a
   `multiprocessing.spawn_main` worker PID, distinct from the parent
   PID) after ruling out Python-`logging`-level causes (patched
   `sys.stdout.write`, `logging.StreamHandler.emit/handle`,
   `Logger.callHandlers` -- none fired for the leaked lines, proving they
   never went through the PARENT's logging machinery at all).

Neither cause is "missing git init in the fixture" per se, though most of
the file's OTHER fixtures (unrelated to #1/#2, but sharing the same
git-less `_make_project`/bare-`pkg.py` shape) also needed a real git
commit or a `pyproject.toml` for `working_diff`/`detect_project_type` to
resolve at all -- T-0550 (COV002/SCOPE001/TODO001 load-failure handling)
and T-0546 (CHECK001 unknown-project-type) both predate this ticket and
are intentional, unrelated hardening; the fixtures in this file had
simply never been updated to match.

Fix:
- src/frob/app/check_runner.py::run -- wraps
  `_refuse_ticket_lease_mismatch`/`_handle_stamp_modes` in the same
  `quiet_stdout_logs()` `--json` uses everywhere else (reentrant via
  T-0125's depth counter, so `_run_all_stages`'s later nested entry is a
  no-op).
- src/frob/gates/__init__.py -- new `_WORKER_STDOUT_LOG_LEVEL_ENV`;
  `_open_process_pool` stamps it with the parent's current stdout handler
  level before constructing the pool; `_run_process_gate` (the picklable
  worker entry point) reads it and clamps its OWN stdout handler before
  running the gate function.
- tests/system/test_cli_check.py -- git-init+commit (or a minimal
  `pyproject.toml` via new `_write_pyproject` helper) added to the
  fixtures that needed a real git repo / recognized project type for
  `working_diff`/`detect_project_type` to resolve cleanly, WITHOUT
  touching the shared `_make_project`/`_make_ts_project` helpers (kept
  git-less/language-agnostic, since `TestGitlessTargetGateSeverity`
  intentionally depends on that).
- Added the deferred T-0787 end-to-end test,
  TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses:
  a real `git worktree add` second checkout, a ticket started (lease
  recorded) in the main worktree, then `frob check --ticket <id>` run
  from the SECOND worktree asserts exit 1 with a refusal naming
  `frob ticket start <id>`.

Deviations / disclosed cuts:
- Two more failures in this file were found and fixed-attempted but are
  PRE-EXISTING, UNRELATED to this ticket's git-ls-files/JSON-pollution
  regression (confirmed: pass standalone/in most orderings, and their
  failure modes have nothing to do with gitio or process-pool logging):
  TestCheckTypescript::test_clean_ts_passes_tsc (needs a warn-severity
  frob.toml AND a fix to a dangling `T-0329` reference inside LANG003's
  known_gap declaration -- T-0329 does not exist as a real ticket) and
  TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
  (order-dependent: `frob.logging.logger._init()` binds
  `ext://sys.stdout`/`ext://sys.stderr` ONCE per process/xdist-worker, at
  the first `get_logger()` call -- if that happens before THIS test's own
  `capsys` fixture activates, `capsys.readouterr()` can never observe
  frob's own stderr handler). Filed as T-0818 (title:
  "test_cli_check: TS/gitless fixture debt unrelated to T-0806 (LANG003
  T-0329 dangling ref, capsys/logging init-order flake)"), left
  unfixed here -- out of this ticket's actual root-cause scope, and each
  needs its own investigation (a real product decision for #1, a
  test-isolation redesign for #2).
- `tests/system/test_cli_check.py -q` (no `-n0`, matching the coordinator's
  exact instruction) is verified fully green below EXCEPT those two
  pre-existing, filed-separately failures.

Evidence: 4 node ids bound via `frob ticket evidence T-0806` (see
Changed). `uv run --frozen pytest tests/system/test_cli_check.py -q`:
34 passed, 2 failed (the two filed-separately, pre-existing failures
above) out of 36 total.
Filed: T-0818 (unrelated TS/gitless fixture debt, see above).
Gates: `uv run --frozen frob check --ticket T-0806` clean (0 errors,
1101 warnings, 207 waived -- none new/related to this ticket's touched
files).

### Changed
```
 src/frob/app/check_runner.py   |  20 +++++-
 src/frob/gates/__init__.py     |  53 +++++++++++++-
 tests/system/test_cli_check.py | 154 +++++++++++++++++++++++++++++++++++++++++
 3 files changed, 222 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses` (pytest node id, verified passing when recorded)
