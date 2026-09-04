---
id: T-3786
title: fix win32 path-separator bug in frob cycle graph node ids
state: in-progress
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/cycle_runner.py
- tests/unit/test_cycle_runner_root_resolution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_cycle_runner_root_resolution.py
  reason: add the test file this fix's evidence lives in
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: append
  reason: 'BUG002 waiver: win32-only defect, cannot repro on Linux CI'
  actor: logan
  at: '2026-09-04'
  old_length: 332
  new_length: 748
evidence:
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_agree_on_a_real_cycle[src/pkg]
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_agree_on_a_real_cycle[src]
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_agree_on_a_real_cycle[.]
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_naive_relative_resolution_would_have_missed_this
- tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_run_exits_nonzero_on_a_found_cycle
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI: 5 tests in tests/unit/test_cycle_runner_root_resolution.py fail because _process_path builds graph node ids with bare str(rel_path) (backslash-separated on win32) while tests (and downstream consumers) expect POSIX-separated ids like 'src/pkg/a.py'. Same root-cause pattern as T-3784's DEPR005 fix. Part of win32 CI drain.

frob:waive BUG002 reason="win32-only defect confirmed via winrun; on Linux the designated repro tests pass at both the parent commit and the fix commit because bare str(rel_path) already produces POSIX separators on Linux -- the node-id path-separator mismatch this ticket fixes only manifests when the process runs on win32, so no Linux-repro-at-parent-commit test can demonstrate the failure this fix addresses"
