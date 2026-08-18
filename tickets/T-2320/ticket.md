---
id: T-2320
title: 'frob quality check: split ruff-check/ruff-format skip flags + add a real ruff-autofix/format
  write mode'
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/_python.py
- src/frob/check/__init__.py
- src/frob/gates/_fix_engine*.py
- src/frob/_cli_parsers/_check.py
- src/frob/app/config.py
- tests/unit/test_check.py
- src/frob/app/check_runner.py
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check.py
  reason: unit tests for the ruff-check/ruff-format skip split and the new ruff-autofix
    write mode
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/check_runner.py
  reason: CLI dispatch wiring for --fix-ruff / split skip flags, and their doc coverage
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/commands/check.md
  reason: CLI dispatch wiring for --fix-ruff / split skip flags, and their doc coverage
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_check_runs_only_format
- tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_format_runs_only_check
- tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_both_returns_empty
- tests/unit/test_check.py::TestRunRuffSplitSkip::test_neither_skipped_runs_both_unchanged
- tests/unit/test_check.py::TestRunRuffAutofix::test_success_runs_fix_then_format_via_uv_run
- tests/unit/test_check.py::TestRunRuffAutofix::test_missing_binary_yields_two_typed_results
- tests/unit/test_check.py::TestRunRuffAutofix::test_kill_switch_disabled_yields_two_typed_results
- tests/unit/test_check.py::TestRunRuffAutofix::test_check_fix_nonzero_exit_still_runs_format
- tests/unit/test_check.py::TestDispatchCheckPythonThreadsRuffSplit::test_python_dispatch_threads_ruff_split
- tests/unit/test_check.py::TestDispatchCheckPythonThreadsRuffSplit::test_default_ruff_split_flags_unchanged
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_fix_ruff_flag_short_circuits_run
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_without_the_flag_falls_through
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_reports_results_and_exits_clean
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_unavailable_tool_exits_nonzero
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_remaining_lint_violations_do_not_fail_the_command
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ccbf43756717c1d9d72a6e82a1adfb2837efa97a
---
Split from T-2252. `_run_ruff` (src/frob/check/_python.py) bundles
ruff-check and ruff-format under one `--skip-ruff` flag with no way to
skip them independently, and `frob quality check --fix`
(src/frob/gates/_fix_engine*.py) only applies frob's own narrow,
targeted Tier-A deterministic fixers -- never a general `ruff check --fix`
across all fixable rule categories. Neither is an equivalent to
Makefile's `format:`/`lint-fix:` targets (`ruff check --fix` + `ruff
format`).

Needed before T-2244's `format:`/`lint:`/`lint-fix:`/`typecheck:` Makefile
leaves can repoint cleanly:
- Split the ruff stage's skip flag into independent
  `--skip-ruff-check`/`--skip-ruff-format` (currently one bundled
  `--skip-ruff`).
- Add a real ruff-autofix-and-format WRITE mode (a genuine `ruff check
  --fix` + `ruff format` pass, distinct from the existing narrow Tier-A
  fixers) so `format:`/`lint-fix:` have something to repoint to.

Also note: this repo's tree currently has ~120 files that would be
reformatted by `ruff format --check` (verified directly) -- repointing
`lint:`/`typecheck:` through `frob quality check`'s bundled ruff stage as
originally proposed would turn a currently-passing Makefile target into a
failing one on pre-existing, out-of-scope formatting diffs. Whoever picks
this up should either accept that one-time reformat as part of the
migration or keep `lint:` scoped to ruff-check only via the new split
flag.