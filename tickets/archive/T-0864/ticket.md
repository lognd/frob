---
id: T-0864
title: 'natives build subcommand: frob-owned maturin develop per [natives] crate with
  git-common-dir shared CARGO_TARGET_DIR'
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: high
parent: T-0735
tier: ticket
sprint: null
scope:
- src/frob/app/natives_runner.py
- src/frob/natives/**
- src/frob/__main__.py
- Makefile
- docs/modules/cli.md
- tests/unit/test_natives_build.py
- src/frob/app/config.py
- src/frob/app/app.py
- README.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: 'T-0864 adds a brand-new `frob natives` subcommand: registering it requires

    the standard CLI wiring pair every subcommand touches -- config.py''s

    Subcommand enum entry (+ any AppConfig dest fields for its argparse flags)

    and app.py''s _RUNNER_MODULE_NAMES/_dispatch_table registration for

    natives_runner. The ticket''s declared scope named the runner module and

    __main__.py''s parser wiring but omitted these two files that the same

    mechanical wiring pattern (see T-0441''s scope, which included all of

    src/frob/app/) always needs. Adding them narrowly rather than working

    around the missing wiring surface.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: src/frob/app/app.py
  reason: 'T-0864 adds a brand-new `frob natives` subcommand: registering it requires

    the standard CLI wiring pair every subcommand touches -- config.py''s

    Subcommand enum entry (+ any AppConfig dest fields for its argparse flags)

    and app.py''s _RUNNER_MODULE_NAMES/_dispatch_table registration for

    natives_runner. The ticket''s declared scope named the runner module and

    __main__.py''s parser wiring but omitted these two files that the same

    mechanical wiring pattern (see T-0441''s scope, which included all of

    src/frob/app/) always needs. Adding them narrowly rather than working

    around the missing wiring surface.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: README.md
  reason: 'DOC005 (src/frob/gates/_docblocks.py) statically binds README.md''s command

    table to the live subcommand registry -- adding `frob natives` as a real

    subcommand fails DOC005 with no matching README.md row/count update, same

    precedent as T-0441''s own scope_changes entry for the identical gate.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001/SYS102 (src/frob/strata/_selfconform.py) fails the moment
    a

    new top-level src/frob/<name> package exists with no design/frob.strata

    node whose code= glob covers it -- T-0864''s new src/frob/natives package

    is exactly that unmodeled-code case. A design/frob.strata node is the

    mechanical requirement for this ticket''s own gates-security pass, same

    precedent as T-0860''s mutate node addition.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_natives_build.py::TestBuildNatives::test_no_native_entries_is_err_no_natives
- tests/unit/test_natives_build.py::TestBuildNatives::test_no_frob_toml_is_err_no_natives
- tests/unit/test_natives_build.py::TestBuildNatives::test_not_a_git_repo_is_err
- tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives
- tests/unit/test_natives_build.py::TestBuildNatives::test_skips_native_with_no_matching_crate_dir
- tests/unit/test_natives_build.py::TestBuildNatives::test_skips_non_rust_native
- tests/unit/test_natives_build.py::TestBuildNatives::test_missing_toolchain_is_best_effort_skip
- tests/unit/test_natives_build.py::TestBuildNatives::test_exec_disabled_is_err
- tests/unit/test_natives_build.py::TestBuildNatives::test_failed_crate_build_reports_not_ok
- tests/unit/test_natives_build.py::TestCrateBuildResultAndReport::test_crate_result_ok_true_on_zero_exit
- tests/unit/test_natives_build.py::TestCrateBuildResultAndReport::test_crate_result_ok_false_on_nonzero_exit
- tests/unit/test_natives_build.py::TestCrateBuildResultAndReport::test_report_ok_vacuously_true_with_no_results
- tests/unit/test_natives_build.py::TestCrateBuildResultAndReport::test_report_ok_false_if_any_result_failed
- tests/unit/test_natives_build.py::TestNativesRunner::test_unknown_action_exits_2
- tests/unit/test_natives_build.py::TestNativesRunner::test_no_natives_declared_is_a_quiet_noop
- tests/unit/test_natives_build.py::TestNativesRunner::test_infra_failure_exits_1
- tests/unit/test_natives_build.py::TestNativesRunner::test_build_reports_success
- tests/unit/test_natives_build.py::TestNativesRunner::test_build_failure_exits_1
- tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_is_one_line_natives_build_shim
- tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_has_no_cargo_target_dir_variable
designated_repro_test: null
acceptance:
- text: GIVEN a frob-enabled repo with [natives] declared WHEN `uv run frob natives
    build` runs THEN each declared native crate compiles via maturin develop into
    the active venv using a git-common-dir-keyed shared CARGO_TARGET_DIR
  evidence:
  - tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives
- text: GIVEN two worktrees of the same clone WHEN both run `frob natives build` THEN
    they share one cargo target dir and concurrent builds are safe via cargo's own
    locking
  evidence:
  - tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives
- text: GIVEN this repo WHEN `make core` runs THEN it is a one-line shim delegating
    to `uv run frob natives build` with no cache logic left in the Makefile
  evidence:
  - tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_is_one_line_natives_build_shim
  - tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_has_no_cargo_target_dir_variable
threat: null
component: natives
---
T-0735 child 1 (the subcommand). Implement `frob natives build`: read frob.toml [natives] (load_natives already declares the native crates), run the maturin-develop-per-declared-native sequence that `make core` does today, WITH the shared-cache mechanism built in (git-common-dir keyed CARGO_TARGET_DIR so all worktrees of a clone share one cargo target dir; rely on cargo's own locking for concurrency -- T-0732's verified design). Convert THIS repo's Makefile `core` target to the one-line shim `uv run frob natives build`, removing the cache logic from the Makefile. Doctor integration: the existing native-staleness fingerprint check must point at `frob natives build` as its remedy text.