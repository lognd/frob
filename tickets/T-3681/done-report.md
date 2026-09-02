## Done report

Repointed docs/modules/process.md's frob:describes anchors for DerivedStateLockUnavailable, _derived_lock_path, and derived_state_lock from src/frob/process/_lock.py to src/frob/process/_derived_lock.py (T-3628 moved these symbols; DRIFT002 x3).

Root-caused the frob ack UnknownRef failure on src/frob/process/_derived_lock.py::_process_already_holds: NOT a defect in acknowledge()'s edge-endpoint check -- that check correctly requires a ref to be a doc/tests/ticket edge endpoint, and this private symbol had none after T-3628's split dropped its only edge (its frob.lock entries were stale leftovers from before the gap existed). Fixed by adding a frob:tests directive pointing at TestDerivedStateWriteLock.test_standalone_rebuild_takes_exclusive, its actual covering test, which restores the edge. Isolated the cause with a controlled comparison: acking the sibling public symbol derived_state_lock succeeded right after the doc repoint alone, while _process_already_holds kept failing with UnknownRef until the frob:tests anchor was added, under both incremental and full graph rebuilds.

Evidence: tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_standalone_rebuild_takes_exclusive (pytest -k test_standalone_rebuild_takes_exclusive: 1 passed).

Filed: none -- no separate frob defect; the fix is in T-3681's own scope.

Gates: frob check --only drift clean for this scope (0 DRIFT errors, down from 4). frob check --only coverage clean for this scope. frob check --ticket T-3681 shows only pre-existing repo-wide errors unrelated to this ticket (COV001 on src/frob/check/__init__.py -- T-3682's own target, COV003 on T-3604, DEPR006, PERF003/PERF004, REL001/T-3411 -- a user decision, WAIVE011, claude-config-drift).

### Changed
```
 docs/modules/process.md           |  6 ++---
 frob.lock                         | 48 ++++++++++++++++++++++++++++++++++++++-
 src/frob/process/_derived_lock.py |  1 +
 3 files changed, 51 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_standalone_rebuild_takes_exclusive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 8 error(s), 4271 warning(s), 909 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/check/__init__.py, COV003@tests/test_ci_workflow_matrix.py, DEPR006@frob-deprecated-baseline.lock.json, PERF003@src/frob/refactor/_scan.py, PERF004@src/frob/refactor/_scan_carry.py, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json
