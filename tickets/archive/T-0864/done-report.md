## Done report

frob owns building its native crates: new frob natives build subcommand reads [[native]] entries from frob.toml and runs maturin develop --uv --release per crate with CARGO_TARGET_DIR keyed off git rev-parse --git-common-dir so all worktrees share one cargo cache (T-0732 design). Makefile core: is now a one-line shim over it. Missing toolchain is a best-effort skip; infra failures are Err values. Covered by 20 unit tests including a static assertion over the real Makefile recipe.

### Changed
```
 Makefile                         |  75 +++-----
 README.md                        |   3 +-
 design/frob.strata               |  56 ++++++
 docs/modules/cli.md              |  57 ++++++
 src/frob/__main__.py             |  23 +++
 src/frob/app/app.py              |   2 +
 src/frob/app/config.py           |  11 ++
 src/frob/app/natives_runner.py   |  66 +++++++
 src/frob/natives/__init__.py     |  26 +++
 src/frob/natives/_build.py       | 229 ++++++++++++++++++++++++
 tests/unit/test_natives_build.py | 363 +++++++++++++++++++++++++++++++++++++++
 tickets.md                       | 180 ++++++++++++++++++-
 12 files changed, 1038 insertions(+), 53 deletions(-)
```

### Evidence
- `tests/unit/test_natives_build.py::TestBuildNatives::test_no_native_entries_is_err_no_natives` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_no_frob_toml_is_err_no_natives` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_not_a_git_repo_is_err` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_skips_native_with_no_matching_crate_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_skips_non_rust_native` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_missing_toolchain_is_best_effort_skip` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_exec_disabled_is_err` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_failed_crate_build_reports_not_ok` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestCrateBuildResultAndReport::test_crate_result_ok_true_on_zero_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestCrateBuildResultAndReport::test_crate_result_ok_false_on_nonzero_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestCrateBuildResultAndReport::test_report_ok_vacuously_true_with_no_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestCrateBuildResultAndReport::test_report_ok_false_if_any_result_failed` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativesRunner::test_unknown_action_exits_2` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativesRunner::test_no_natives_declared_is_a_quiet_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativesRunner::test_infra_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativesRunner::test_build_reports_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestNativesRunner::test_build_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_is_one_line_natives_build_shim` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_has_no_cargo_target_dir_variable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
