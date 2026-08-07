## Done report

## Done report

Changed:
src/frob/process/_lock.py::_canonical_registry_key
src/frob/process/_lock.py::_process_already_holds
src/frob/process/_lock.py::derived_state_lock
docs/modules/process.md#derived-state-lock-t-0859
tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey.test_shared_unresolved_then_nested_write_resolved_does_not_deadlock
tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey.test_write_resolved_then_nested_shared_unresolved_agrees

Root cause confirmed: frob.check's outer derived_state_lock(root, exclusive=False)
call and frob.graph.build_graph's nested derived_state_write_lock(root) call reached
the SAME on-disk checkout through two DIFFERENT Path spellings (build_graph does
`root = root.resolve()` before locking; the outer check-side root was not resolved).
_process_already_holds/derived_state_write_lock's process-wide reentrancy registry
(_process_held_counts) was keyed on `str(_derived_lock_path(root))` -- spelling-
sensitive -- so the resolved-root caller's reentrancy check read False even though
the unresolved-root caller's SHARED hold was outstanding in this same process, and
it went on to attempt a real second flock(LOCK_EX) against its own process's
LOCK_SH, self-deadlocking. Fix: added `_canonical_registry_key` (resolves the lock
path before keying) and switched `_process_already_holds` and the increment/
decrement sites in `derived_state_lock` to use it for the `_process_held_counts`
dict only -- the actual `os.open`/`flock` path and the thread-local re-entrancy
dict are unchanged (flock is inode-scoped, so different spellings of the same file
already serialized correctly at the OS level; only the in-process dict lookup was
spelling-sensitive). Also fixed a pre-existing stale `frob:tests` directive in
`derived_state_write_lock`'s docstring that named a test method
(`test_concurrent_other_process_writer_still_blocked`) that did not match the
actual test (`test_concurrent_separate_process_writer_still_blocked`), which
DRIFT002 flagged once prework ran.

Evidence:
- tests/unit/test_process_lock.py (all 10 tests, includes T-0918's 3
  TestDerivedStateWriteLock tests + 2 new T-0933 regression tests) --
  `uv run pytest -q tests/unit/test_process_lock.py` -> 10 passed
- Real check-path reproduction/verification (timeout-wrapped, per dispatch
  instructions): `timeout 180 uv run frob check --only scope --ticket T-0933`
  and `timeout 180 uv run frob check --only prework --ticket T-0933` both
  COMPLETE in <1s (drift=0.01s/0.02s, scope/prework=0.00s in the gate timing
  breakdown) -- no hang, confirming the T-0933 self-deadlock is fixed on the
  actual dispatch path, not just in the synthetic unit tests.
- Full `timeout 180 uv run frob check --ticket T-0933 --base main`: all
  gates pass except a single pre-existing, out-of-scope PARSE002 finding on
  `tests/fixtures/lang/broken.py` (an intentionally-malformed fixture file,
  untouched by this diff, unrelated to T-0933's scope).
- `timeout 180 uv run frob test --base main`: python suite PASS, exit=0,
  1.51s (touched-set selection included test_process_lock.py + the process
  parse interface test).

Filed: none

Gates: frob check --ticket T-0933 clean except pre-existing out-of-scope
PARSE002 (tests/fixtures/lang/broken.py, known-intentionally-malformed
fixture, not touched by this ticket's scope).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_standalone_rebuild_takes_exclusive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_nested_inside_shared_holder_does_not_deadlock` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_concurrent_separate_process_writer_still_blocked` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey::test_shared_unresolved_then_nested_write_resolved_does_not_deadlock` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey::test_write_resolved_then_nested_shared_unresolved_agrees` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4148 warning(s), 219 waived
- error-findings: PARSE002@tests/fixtures/lang/broken.py
