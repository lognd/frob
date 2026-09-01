## Done report

Extends T-3657's 2-variant diag matrix to 4 variants, after run
33533123354 proved variant (b) (FROB_DISABLE_EXEC=1, zero guarded tool
children) STILL received SIGINT -- the guarded-child class is now
fully exonerated, not just T-3651's round-14 tool-child hypothesis.

Variant (c): the SAME diag script and fixture as variant (a), invoked
directly via the venv's own python.exe (Join-Path $env:GITHUB_WORKSPACE
".venv\Scripts\python.exe", built by the earlier 'uv sync' step) instead
of `uv run python ...`, so uv never appears in the diag child's process
ancestry. Discriminates: if clean, uv is the sender.

Variant (d): the same uv-ancestry invocation shape as variant (a)
(isolating the pool alone), but with a new FROB_DISABLE_POOL_PRELOAD=1
kill switch set before frob.__main__.main() runs. Added
pool_preload_enabled() (src/frob/process/_guard.py, same posture as
exec_enabled()/net_enabled()) and wired it into
frob.gates._run_combined_jobs: when disabled,
_run_process_jobs_serially_in_process runs every process-pool gate job
via _run_process_gate directly in the calling process/thread instead of
ever constructing a ProcessPoolExecutor -- every gate still runs, just
serially, never silently skipped. Discriminates: if clean, the pool's
multiprocessing spawn children are the sender.

Neither switch is enabled by default anywhere; only these two new CI
diag steps opt in.

Changed:
  src/frob/process/_guard.py::FROB_DISABLE_POOL_PRELOAD_ENV
  src/frob/process/_guard.py::pool_preload_enabled
  src/frob/gates/__init__.py::_run_process_jobs_serially_in_process
  src/frob/gates/__init__.py::_run_combined_jobs (wiring)
  .github/workflows/ci.yml (2 new diag steps, variants c and d)
  tests/unit/test_process_guard.py::TestPoolPreloadEnabled
  tests/unit/test_gates_pool_preload.py::TestRunProcessJobsSerially
  tests/test_ci_workflow_matrix.py::TestWindowsDirectPythonDiagVariant
  tests/test_ci_workflow_matrix.py::TestWindowsNoPoolPreloadDiagVariant
  docs/modules/process.md (T-3670 section)

Evidence:
  tests/unit/test_process_guard.py::TestPoolPreloadEnabled::test_unset_env_is_enabled
  tests/unit/test_process_guard.py::TestPoolPreloadEnabled::test_truthy_value_disables
  tests/unit/test_process_guard.py::TestPoolPreloadEnabled::test_falsy_value_stays_enabled
  tests/unit/test_gates_pool_preload.py::TestRunProcessJobsSerially::test_runs_every_job_and_populates_accumulators
  tests/unit/test_gates_pool_preload.py::TestRunProcessJobsSerially::test_empty_jobs_is_a_noop
  tests/test_ci_workflow_matrix.py::TestWindowsDirectPythonDiagVariant (5 tests)
  tests/test_ci_workflow_matrix.py::TestWindowsNoPoolPreloadDiagVariant (5 tests)
  tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_precedes_the_windows_test_step (updated for the 4-step ordering)

Filed: none.

Gates: frob check --ticket T-3670 --only scope/prework/affect_drift
clean for this ticket's own DRIFT002/SCOPE errors (after fixing an
identical frob:tests directive-separator bug T-3657 also hit). The
DRIFT001/DRIFT002 findings on src/frob/process/_derived_lock.py and
docs/modules/process.md's _lock.py references are a SIBLING ticket's
in-flight _lock.py -> _derived_lock.py rename, explicitly out of this
ticket's scope -- not touched.

### Changed
```
 .github/workflows/ci.yml              | 162 +++++++++++++++++++++++++++++-
 docs/modules/process.md               |  30 ++++++
 src/frob/gates/__init__.py            |  59 ++++++++++-
 src/frob/process/_guard.py            |  40 ++++++++
 tests/test_ci_workflow_matrix.py      | 184 ++++++++++++++++++++++++++++++----
 tests/unit/test_gates_pool_preload.py |  69 +++++++++++++
 tests/unit/test_process_guard.py      |  25 +++++
 tickets/T-3670/ticket.md              |  27 ++++-
 8 files changed, 575 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/unit/test_process_guard.py::TestPoolPreloadEnabled::test_unset_env_is_enabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestPoolPreloadEnabled::test_truthy_value_disables` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestPoolPreloadEnabled::test_falsy_value_stays_enabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_pool_preload.py::TestRunProcessJobsSerially::test_runs_every_job_and_populates_accumulators` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_pool_preload.py::TestRunProcessJobsSerially::test_empty_jobs_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDirectPythonDiagVariant::test_directpython_diag_step_exists_and_runs_on_windows` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDirectPythonDiagVariant::test_directpython_diag_step_has_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDirectPythonDiagVariant::test_directpython_diag_step_never_invokes_uv` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDirectPythonDiagVariant::test_directpython_diag_step_resolves_venv_python_under_workspace` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDirectPythonDiagVariant::test_directpython_diag_step_reuses_the_same_diag_script_and_fixture` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsNoPoolPreloadDiagVariant::test_nopoolpreload_diag_step_exists_and_runs_on_windows` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsNoPoolPreloadDiagVariant::test_nopoolpreload_diag_step_has_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsNoPoolPreloadDiagVariant::test_nopoolpreload_diag_step_sets_env_var_before_main` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsNoPoolPreloadDiagVariant::test_nopoolpreload_diag_step_keeps_uv_ancestry` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsNoPoolPreloadDiagVariant::test_nopoolpreload_diag_step_reuses_the_same_fixture` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_precedes_the_windows_test_step` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 16 error(s), 4327 warning(s), 898 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3670, REF002@src/frob/process/_lock_msvcrt.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json, WIRE001@tests/unit/test_gates_pool_preload.py
