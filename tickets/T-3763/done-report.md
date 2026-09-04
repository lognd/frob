## Done report

win32 CI fails these tests because scan_for_live_worktree_process (and the test's own _proc_test_cwd_matches helper) read /proc/<pid>/cwd directly, which does not exist on Windows -- genuinely POSIX-only. Added skipif(sys.platform==win32) at method level on all 5 affected tests. Verified on Linux: all 19 tests in the file still pass (skips don't fire here).

### Changed
```
 tests/unit/test_land_finish_guard.py | 25 +++++++++++++++++++++++++
 tickets/T-3763/ticket.md             | 19 +++++++++++++++++--
 2 files changed, 42 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse::test_refuses_on_a_live_process_and_names_the_pid` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_refuses_to_remove_a_worktree_a_live_process_is_cwd_into` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_force_removes_despite_a_live_process` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_finish_worktree_force_requires_reason_when_guard_would_fire` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4317 warning(s), 919 waived
- error-findings: COV003@tests/test_ci_workflow_matrix.py
