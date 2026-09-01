## Done report

T-3648's CREATE_NEW_PROCESS_GROUP-only fix was not enough: run
33513484322's diag caught the real SIGINT arriving ~1.5s in, right after
the first tool spawn. A new process group still shares the console with
its parent -- any console-attached child (e.g. the tool child spawned via
`ruff`/`uv`) can signal every process on that console via
GenerateConsoleCtrlEvent regardless of group membership. Added
CREATE_NO_WINDOW (0x08000000, ORed with CREATE_NEW_PROCESS_GROUP) so
win32 tool spawns have no console to signal ours through -- the check
pipeline's children are all non-interactive with piped stdio, so nothing
is lost.

Evidence: 4 new tests in TestWin32IsolateConsoleGroup (test_no_op_on_
non_win32, test_sets_new_process_group_on_win32,
test_sets_create_no_window_on_win32,
test_never_overrides_an_explicit_creationflags), plus the 3 pre-existing
tests in that class re-verified. `uv run frob test --base main`: 6/6
touched-set python tests pass. `uv run frob check --ticket T-3651 --only
prework` and `--only coverage`: no findings against
src/frob/process/_guard.py or tests/unit/test_process_guard.py.
Repo-wide gates-fast/native/security/lint findings observed this session
are pre-existing and unrelated (grepped both filenames, zero hits).
`uv run frob check --only ty` flagged the new bitmask assertion
(unsupported-operator on dict[str, object]); fixed by narrowing to int
before the & check, re-verified clean.

Filed: none.

### Changed
```
 src/frob/process/_guard.py       | 51 +++++++++++++++++++++++----------------
 tests/unit/test_process_guard.py | 52 +++++++++++++++++++++++++++++++---------
 tickets/T-3651/ticket.md         |  5 ++++
 3 files changed, 76 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_no_op_on_non_win32` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_sets_new_process_group_on_win32` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_sets_create_no_window_on_win32` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_never_overrides_an_explicit_creationflags` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 13 error(s), 4234 warning(s), 898 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3651, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
