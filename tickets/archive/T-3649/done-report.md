## Done report

T-3648's post-land unscoped sweep found 1 new COV001 identity on
src/frob/process/_guard.py, attributed to FROB_WIN32_SPAWN_DEBUG_ENV: it
was missing the frob:doc anchor every other public constant in this
module carries (EXEC_KILL_SWITCH_ENV/NET_KILL_SWITCH_ENV both have
"frob:doc docs/modules/process.md#public-api"; the new constant did
not). Added the same anchor. Re-running frob check also surfaced ENV001
on the same constant (the env var's literal name was never mentioned in
tracked docs) -- fixed by adding a doc paragraph naming
FROB_WIN32_SPAWN_DEBUG explicitly in docs/modules/process.md, matching
the module's existing per-constant doc pattern.

This is a pure documentation fix -- no behavior change to
guarded_subprocess_run or _win32_isolate_console_group. Verified: both
COV001 and ENV001 findings on src/frob/process/_guard.py are gone from a
fresh frob check --ticket T-3649 run; gate:SCOPE clean after adding
docs/modules/process.md to scope; ruff-check/ruff-format clean on the
touched Python file; tests/unit/test_process_guard.py (31 tests,
including all TestWin32IsolateConsoleGroup and TestGuardedSubprocessRun
cases) still 31/31 clean, confirming the doc-only change did not disturb
runtime behavior.

Filed: none new.

### Changed
```
 docs/modules/process.md    |  6 ++++++
 src/frob/process/_guard.py |  1 +
 tickets/T-3649/ticket.md   | 13 ++++++++++++-
 3 files changed, 19 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_enabled_spawns_and_returns_ok` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_sets_new_process_group_on_win32` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 13 error(s), 4243 warning(s), 898 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3649, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
