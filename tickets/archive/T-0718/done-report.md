## Done report

Reproduces: YES, on current main. `detect_project_type` (src/frob/check/__init__.py) had a
root-level extension-based fallback for bare C/C++ source (*.cpp/*.cc/*.c) but none for
bare *.py files -- a root with tracked .py files and no pyproject.toml/setup.py fell all
the way through to `_detect_nested_native_project_type` and returned 'unknown', which
`_dispatch_check` then reported as CHECK001 "unknown project type ... no dispatchable
language stage". Reproduced by running the three named tests before any fix: 2 of 3
(test_ticket_scoped_nonzero_exit_has_diagnostic_output, test_only_gates_passes_once_bound_and_tested)
failed exactly as described; the third (test_perf001_fixture_warns_but_check_exits_zero)
also failed on CHECK001 the same way.

Fix: added a `root.glob("*.py")` fallback to 'python' in `detect_project_type`, mirroring
the existing bare-C/C++-source fallback, right before the final
`_detect_nested_native_project_type` call. `test_no_sentinel_is_unknown` (empty tmp_path,
no .py files) still passes, so 'unknown' is still returned when there is truly nothing to
detect.

Second issue found while re-verifying: fixing project-type detection unmasked a SEPARATE,
already-known bug in `test_perf001_fixture_warns_but_check_exits_zero` -- once the fixture
correctly detects as 'python', it now reaches PRE001/SCOPE001 ("diff touches 1 file(s) but
no active ticket is derivable"), the exact hazard already named and fixed elsewhere per
T-0806 (`--stamp-coverage` leaves `frob-coverage.lock.json` uncommitted, so the next `--only
gates` run sees a dirty 1-file diff). `test_only_gates_passes_once_bound_and_tested`
already carries the T-0806 fix (commit the stamp before the second run); this perf test
did not. Applied the same fix (commit the stamp file) since the file is within this
ticket's declared scope and this was the ticket's own regression target, not a new
out-of-scope discovery.

Changed:
- src/frob/check/__init__.py::detect_project_type (frob:ticket T-0718 added; root-level
  *.py glob fallback to 'python')
- tests/unit/test_check.py::TestDetectProjectType.test_bare_py_file_no_pyproject_is_python (new regression test)
- tests/system/test_cli_perf.py::TestCheckOnlyPerf.test_perf001_fixture_warns_but_check_exits_zero
  (commit the coverage stamp before the second `--only gates` run, T-0806 pattern)

Scope: the ticket's original declared scope (src/frob/app/**, tests/system/test_cli_check.py,
tests/system/test_cli_perf.py) assumed the detector lived under src/frob/app/config.py; it
actually lives in src/frob/check/__init__.py. Extended scope via `frob ticket scope T-0718
--add src/frob/check/__init__.py --reason-file ...` and `--add tests/unit/test_check.py
--reason-file ...` (both with recorded reasons, see scope_changes above) to cover the real
fix location and the new regression test file.

Evidence:
- tests/unit/test_check.py::TestDetectProjectType (all cases) -- pass
- tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output -- pass
- tests/system/test_cli_check.py::TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested -- pass
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero -- pass
- Full `tests/unit/test_check.py` + `tests/system/test_cli_check.py` + `tests/system/test_cli_perf.py` run: 1 unrelated pre-existing failure
  (TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root),
  confirmed to fail in isolation too and self-documented in its own docstring as an
  order-dependent capsys/logging-init flake unrelated to project-type detection or this
  ticket's scope -- not touched.
- `uv run frob test --base main`: run_selected python exit=0, `frob test: recorded stability
  for 5 python test(s)`

Filed: T-0939 (bug) -- `frob check --ticket <id> --only scope` hung indefinitely
in this worktree across 3 repeated fresh invocations regardless of system load; `lslocks`
showed the same pid holding both READ and a pending WRITE* flock on .frob/derived.lock
simultaneously (a same-process flock self-deadlock via a second fd, bypassing the existing
_process_held_counts reentrancy guard in src/frob/process/_lock.py). Out of T-0718's scope
(a locking bug, not project-type detection), filed separately rather than fixed here.

Gates: `uv run frob check --ticket T-0718 --only scope` could not be run to completion in
this environment (see T-0939). As a substitute, called the same underlying
`frob.gates.scope_matches` predicate directly in a `uv run python -c` one-liner against the
loaded ticket's post-extension `scope` tuple for every file in `git status --short`
(src/frob/check/__init__.py, tests/system/test_cli_perf.py, tests/unit/test_check.py,
tickets.md): all four returned True. `uv run frob test --base main` (a separate code path
from the hanging scope stage) ran to completion cleanly.
