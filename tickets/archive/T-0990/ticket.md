---
id: T-0990
title: 'ARCH103: resolve 2 newly-live findings blocking promotion (perf_runner/_open_process_pool)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/perf_runner.py
- src/frob/gates/__init__.py
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_resolves_a_real_python_hot_frame
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_json_output_is_valid_json
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_autodetects_cpuprofile_format
- tests/test_gates.py::TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks
designated_repro_test: null
threat: null
component: null
---
T-0979 resolved its own 2 named ARCH103 sites (which had moved, post
T-0976/T-0985 refactor, from `format_paths`/`build_natives` into their
newly-extracted per-item helpers `_format_one_path`
(src/frob/gates/_fmt_directives.py) and `_build_one_crate`
(src/frob/natives/_build.py)) via genuine extraction/waiver, and would
have promoted `[gates.severity] ARCH103 = "error"` next -- except a
fresh, unscoped `frob check --only gates-native --json` re-measure
turned up 2 OTHER live unwaived ARCH103 findings that are outside
T-0979's declared scope:

- src/frob/app/perf_runner.py:272 `_collect_stacks_from_file` (3 decision
  points)
- src/frob/gates/__init__.py:10703 `_open_process_pool` (4 decision
  points)

These are not part of T-0977's original 24-finding hand-off list (that
list's remaining 2 were the ones T-0979 just resolved) -- they appear to
be newly-introduced mixed-concern shapes from unrelated recent changes
to those two files. Promoting ARCH103 to error with these 2 unwaived
would immediately red `main`.

Scope: src/frob/app/perf_runner.py, src/frob/gates/__init__.py,
frob.toml.

Resolve each (extract a real cohesive helper, or add an honest
`frob:waive ARCH103 reason="..."` with a real structural argument,
matching the precedent this whole ARCH103 burn-down chain has used),
then promote `[gates.severity] ARCH103 = "error"` in frob.toml once
truly zero unwaived live findings remain repo-wide (verify via a fresh
`frob check --only gates-native --json`).