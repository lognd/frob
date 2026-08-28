## Done report

Changed:
tests/system/test_frob_self_model.py::TestFrobSelfModel.test_sys_gate_zero_violations
tests/system/test_frob_self_model.py::TestFrobSelfModel.test_fragments_module_fs_read_is_declared_not_selfaudit001
tests/system/test_frob_self_model.py::TestFrobSelfModel.test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001
tests/unit/strata/test_selfconform.py::TestRealGateGreen.test_repo_design_and_declarations_are_self_conformant
tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001.test_ticket_readiness_is_not_an_arch001_finding
tests/gates/test_scan_timeout_enforcement.py (new file: find_scan_timeout_violations + AST helpers + TestFindScanTimeoutViolations + TestRepoIsScanTimeoutClean)

Evidence:
tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_fire_on_unmarked_whole_repo_scan_call
tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_on_ordinary_fast_test
tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_when_method_level_override_present
tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_when_class_level_pytestmark_present
tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_on_synthetic_repo_fixture_test
tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_on_synthetic_tmp_path_target
tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_on_run_call_with_explicit_path_argument
tests/gates/test_scan_timeout_enforcement.py::TestRepoIsScanTimeoutClean::test_no_unmarked_whole_repo_scan_tests_in_repo
tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding

Filed:
T-3267 (migrate the AST-based scan-timeout detector out of tests/gates/test_scan_timeout_enforcement.py into a real src/frob/gates SCAN001 rule once T-3196 releases its lease on src/frob/gates/__init__.py)

## What was built

1. THREE named tests (T-3247's original CI failures) got measured @pytest.mark.timeout(300) overrides:
   - test_sys_gate_zero_violations: 27.11s local baseline; CI's own faulthandler dump caught it still inside build_graph at the 100s mark.
   - test_repo_design_and_declarations_are_self_conformant: src/frob/vet/_capability_core.py's own T-2798 docstring already measured this call chain at 94.25s of a 111.09s isolated sweep; windows CI's dump stamped "Timeout (0:01:40)" on this exact test.
   - test_ticket_readiness_is_not_an_arch001_finding: 52.98s local baseline (a real `frob check --only arch` subprocess spawn); also needed `timeout=300` passed explicitly to tests/system/conftest.py::run, since its own DEFAULT_RUN_TIMEOUT_S (T-2980) independently caps an unadorned call at 100s regardless of the pytest-level mark.

2. THE GATE (the actual point of the ticket): tests/gates/test_scan_timeout_enforcement.py::find_scan_timeout_violations. Enumeration method: parses every tests/**/test_*.py file with Python's `ast` module, resolves each test function's direct Call targets through that FILE'S OWN `from ... import` statements against a small, explicit _WHOLE_REPO_SCAN_ENTRYPOINTS set (frob.graph.build_graph, frob.strata._selfconform.check_self_conformance, frob.vet._capability_core.scan_file_capabilities, tests.system.conftest.run), then checks for an effective @pytest.mark.timeout (method or class-level pytestmark). No hand-maintained test-name list (unlike the pre-existing, unrelated tests/conftest.py::_SELF_SCAN_HEAVY_NAME_SUBSTRINGS, which exists for xdist GROUPING, not timeout bounding).

   Real-vs-synthetic-target discrimination (required -- a naive "calls build_graph" check flags ~50+ fast tmp_path-based tests across the suite): build_graph/check_self_conformance/scan_file_capabilities are only counted when their root argument is structurally derived from __file__ (Path(__file__).resolve()... , resolved through one hop of module-level Name indirection) -- the idiom this repo's own suite already uses for "this test's own real checked-out location", as opposed to a tmp_path fixture (which resolves to nothing and is correctly excluded). `run(...)` has no root parameter to inspect, so it is judged by argument shape instead: only `run("check", <string-literal-flags-only>)` counts (verified: 17 other `run("check", str(tmp_path), ...)` call sites elsewhere in tests/system/test_cli_check.py etc. all pass a non-literal path arg and are correctly excluded).

   TestRepoIsScanTimeoutClean::test_no_unmarked_whole_repo_scan_tests_in_repo runs the enumerator against the REAL tests/ tree and asserts zero violations -- this IS the gate: a future whole-repo-scan test added without @pytest.mark.timeout fails this test by name/file/line, in the normal suite, with no separate tool to remember to run. It found 2 more real instances beyond the 3 originally named (test_fragments_module_fs_read_is_declared_not_selfaudit001, test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001, both in test_frob_self_model.py, same build_graph(_REPO_ROOT, ...) shape) -- fixed with the same 300s override.

   Not wired into `frob check` (src/frob/gates/__init__.py::_assemble_gate_report) because that file is under a live T-3196 scope lease; T-3267 tracks migrating it there. frob:waive WIRE001 (with follow_up="T-3267") on each of the 8 private helpers, since they are wired -- find_scan_timeout_violations calls them, just from within this same test file.

## Investigation findings (report-only, per the ticket)

1. xdist worker-death crashing the loadscope scheduler: CONFIRMED upstream pytest-xdist defect, not something to work around locally. https://github.com/pytest-dev/pytest-xdist/issues/714 and https://github.com/pytest-dev/pytest-xdist/issues/1189 describe the identical KeyError<WorkerController> shape under --dist loadgroup/loadscope when a worker terminates improperly and a replacement worker's registered_collections was never initialized. This repo's own mitigation is exactly right: keep worker death from happening at all (per-test timeouts bounding whole-repo scans, this ticket) rather than trying to make the scheduler survive a death it does not reliably survive upstream.

2. T-3192's own positive control (test_ordinary_fast_test_is_unaffected) failure on the 2026-08-28 windows run: COLLATERAL from the same abort, not an independent defect. Evidence (from the cached CI log, /tmp/gh-cli-cache/run-log-33169097371-1787918217.zip, build (windows-latest)/13_Test (windows_macos).txt):
   - The failure appears ONLY in the SUITE-RESULT-FAILED partial list emitted at the exact same INTERNALERROR/KeyError<WorkerController gw6> abort this ticket investigates (line 358-362 of that log).
   - That same partial list also names tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately -- T-0742's own already-fixed, known-good test -- proving (per T-3246's own finding) this list is not a reliable "real failures" set on an aborted run.
   - No FAILURES section or traceback for this test appears anywhere in the log -- no evidence of a genuine assertion failure, only its presence in the partial/incomplete failing-set snapshot.
   - Checked and ruled out an alternative hypothesis (that the nested `timeout -s ABRT ...` subprocess this test spawns inherits pyproject.toml's own -n auto/--timeout=120 addopts, paying the same xdist cost): measured directly that pytest's rootdir/ini discovery is keyed off the TARGET test file's path, not cwd -- a target file outside the repo tree (tmp_path) does not pick up this repo's pyproject.toml at all. Not the mechanism.
   Not filed separately; this is the SAME root cause T-3247 already covers (xdist worker death under whole-repo-scan pressure), not a second one.

## Gates

frob check --ticket T-3247: zero errors on every touched file (tests/system/test_frob_self_model.py, tests/unit/strata/test_selfconform.py, tests/system/test_fleet_status_ticket_readiness_arch001.py, tests/gates/test_scan_timeout_enforcement.py). Remaining non-error notes on these files are pre-existing/waived (COV006 module-constant-drift-lock waivers already in test_selfconform.py, unrelated to this change; DUP002 warning between the two build_graph(_REPO_ROOT,...) tests in test_frob_self_model.py -- pre-existing test bodies, only my added comment text triggered the near-duplicate detector, left as a warning not an error).

FMT001 (11 sites, long frob:tests directive lines) -- waived, same precedent as src/frob/app/_json_guard.py.
WIRE001 (8 sites) -- waived with follow_up="T-3267".
frob:invariant terminates added on the one recursive helper (_derives_from_dunder_file), PERF005/PERF006 clean.

Not run: full-repo `frob check`/`frob test --base main` (host under T-3256's measured contention; this worktree's own native strata_core extension is also unbuilt, a pre-existing worktree-provisioning gap unrelated to this ticket -- several test_frob_self_model.py/test_selfconform.py tests fail on native-missing ModuleNotFoundError in this worktree regardless of this ticket's changes, confirmed by reproducing the identical failure before making any edit).

### Changed
```
 tests/gates/test_scan_timeout_enforcement.py       | 601 +++++++++++++++++++++
 .../test_fleet_status_ticket_readiness_arch001.py  |  12 +
 tests/system/test_frob_self_model.py               |  28 +
 tests/unit/strata/test_selfconform.py              |  13 +
 tickets/T-3247/ticket.md                           |  10 +-
 5 files changed, 663 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 18 error(s), None warning(s), None waived
- error-findings: CYCLE001@src/frob/__init__.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py, unresolved-import@src/frob/arch/_abstraction.py, unresolved-import@src/frob/gates/_vmodel.py, unresolved-import@src/frob/graph/_core.py, unresolved-import@tests/test_arch_near_duplicate_native.py, unresolved-import@tests/unit/strata/test_capacity.py, unresolved-import@tests/unit/test_arch_python_native.py, unresolved-import@tests/unit/test_capability_native.py, unresolved-import@tests/unit/test_dup_core.py, unresolved-import@tests/unit/test_extract_native.py, unresolved-import@tests/unit/test_lang_strata.py
