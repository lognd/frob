## Done report

Verified the deadlock this ticket describes no longer reproduces: T-0982
(landed as b9f86f74, commit 43ed42a6) already fixed the exact mechanism
described here -- derived_state_write_lock's reentrancy registry was
process-local and blind to ProcessPoolExecutor workers, causing a real
flock(LOCK_EX) deadlock against the parent's SHARED hold. T-0982's fix
stamps an env marker with the owner's held registry keys before
constructing the process pool (_open_process_pool in
src/frob/gates/__init__.py), and a worker consults that marker in
_process_already_holds (src/frob/process/_lock.py) to bypass its own lock
acquisition exactly like the same-process nested case, while an
independent process's worker still takes a real exclusive lock.

Confirmed no re-implementation is needed:
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance already
  covers this exact scenario end to end with a REAL ProcessPoolExecutor
  worker under a parent SHARED holder
  (test_real_pool_worker_under_parent_shared_holder_completes), plus the
  negative case that an independent process without the marker still
  blocks (test_independent_process_without_marker_still_blocks). Ran the
  full file foreground: 12 passed, 0 failed.
- [dup].enforce=true is now live in this repo's own frob.toml (flipped by
  T-0974, commit 15e0e91c, specifically because T-0982 made it safe to do
  so) -- frob check's own clones stage runs under exactly the topology
  this ticket describes (dup_gate dispatched into _PROCESS_POOL_GATES)
  with no hang, which would be impossible if the deadlock still existed.

No code changes made under this ticket; closing as fixed-by-T-0982 with
the above evidence rather than re-implementing (b) from the plan, which
T-0982 already built.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 4719 warning(s), 333 waived
- error-findings: none (measured, zero errors)
