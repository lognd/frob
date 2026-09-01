---
id: T-3662
title: 'win32: FMT001/PERF004 file fields carry native-separator paths'
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/gates/__init__.py
- tests/gates_suite/test_fix_engine.py
- tests/gates_suite/test_run.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_fmt001_file_is_posix_shaped_for_a_nested_path
- tests/gates_suite/test_run.py::TestOptInGates::test_perf_gate_file_is_posix_shaped_for_a_nested_path
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_relative_to_as_posix_normalizes_a_windows_shaped_path
designated_repro_test: tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_fmt001_file_is_posix_shaped_for_a_nested_path
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI run 33521416410 (tracked by T-3659): three tests fail with a native-separator-vs-POSIX-separator mismatch on win32 only, all the same root-cause shape:

1. tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean
   - expects applied[0].file == "src/m.py", gets 'src\\m.py'
   - root cause: src/frob/gates/_fmt_directives.py's _relpath_for_change(path, root) does `return str(path.relative_to(root))` -- str() on a Windows Path renders backslashes. Every other FixApplied/Violation.file convention in this codebase is repo-relative POSIX (as _fix_engine_scope.py's own scope-matching and _waive.py's exact-string waiver matching both assume). Fix: use `path.relative_to(root).as_posix()`.

2. tests/gates_suite/test_run.py::TestOptInGates::test_perf_gate_reports_a_repo_relative_file_not_absolute
   - expects v.file == "src/a.py", gets 'src\\a.py'
   - root cause: src/frob/gates/__init__.py's _relativize_perf_violation_file(root, violation) does `rel = Path(violation.file).relative_to(root); rel_str = str(rel)`. Same bug, same fix: `.as_posix()` instead of `str()`.

3. tests/gates_suite/test_run.py::TestOptInGates::test_frob_waive_perf004_suppresses_the_named_finding
   - `frob:waive PERF004` fails to suppress the finding on win32 -- direct downstream consequence of bug #2: `_apply_waivers`/`_match_waiver`'s file-level fallback does exact string equality between the waiver's graph-derived edge src (POSIX, via `.as_posix()` elsewhere) and `violation.file` (backslash-carrying on win32 per bug #2), so they never match. Fixing #2 should also fix this one; kept as a separate acceptance case since it demonstrates the actual user-visible waiver-defect T-2314 (perf_gate's own docstring) exists to prevent, not just the raw path-string assertion.

Fix direction (product, not test): both producers construct `Violation.file`/`FixApplied.file` from `str(a_pathlib_Path)` after a `.relative_to()` call instead of `.as_posix()`. Grep both files (_fmt_directives.py, gates/__init__.py) for any other `str(...relative_to(...))` call sites in the same family and fix those too if found, since this is exactly the class of bug T-2314's own docstring in gates/__init__.py already names as "every other gate... uses a repo-relative path" -- these two producers are the outliers.

Traceback evidence: scratchpad/win-33521-failures.txt lines 3050-3316 (fmt001), lines 18418-18694 (perf_gate absolute), lines 19519-19783 (waive004 perf004).

References T-3659 (tracking ticket for this campaign).