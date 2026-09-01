## Done report

Completed ARCH102's 3-cluster split of src/frob/process/_lock.py: cluster 1 (msvcrt, done and verified before this session), cluster 3's remaining 4 of 8 symbols (DerivedStateLockUnavailable, _canonical_registry_key, derived_state_lock, derived_state_write_lock), cluster 2 (portable flock primitive) staying in _lock.py per plan. Was blocked on T-3660 (promoted -> T-3650, landed this session fixing the self-import carry-forward defect) plus a deeper structural circular-import shape T-3650 does not cover: the moved derived_state_lock/derived_state_write_lock bodies need cluster-2 primitives (fcntl/msvcrt/portable_flock_acquire/portable_flock_release/_lock_local/_log) that stay in _lock.py forever, and _lock.py's own re-export shim for the moved symbols needs them back -- any module-level carry-forward import the split tool auto-generates is genuinely circular against that shim regardless of import order. Filed T-3653 (dest-file stale-import mirror of T-3650) and T-3656 (coordinator-reported string-literal-editing defect) as separate tool gaps, both fixed inline where they blocked this ticket's own moves (T-3653) or filed for a different series (T-3656, no touch to tests/conftest.py per the coordinator's scope note). The final 2 symbols were cut via script (T-3594's established precedent for this exact circular-import shape, never hand-retyped) with the same local-import-at-call-time pattern already proven for cluster 3's first 4 symbols. Also fixed two pre-existing bugs surfaced while verifying: _lock_msvcrt.py's frozen from-import broke monkeypatch.setattr(_lock_mod, ...) in the test suite (switched to reading through the module object), and _lock.py's __all__ listed held_registry_keys with no shim import bringing it back into scope.

### Changed
```
 frob.lock                          |   4 +-
 src/frob/gates/__init__.py         |   6 +-
 src/frob/process/_derived_lock.py  | 410 ++++++++++++++++++++++++++++++++++
 src/frob/process/_lock.py          | 437 ++-----------------------------------
 src/frob/process/_lock_msvcrt.py   |  68 ++++++
 tickets/T-3628/ticket.md           |  65 +-----
 tickets/T-3660/ticket.md |  95 ++++++++
 7 files changed, 600 insertions(+), 485 deletions(-)
```

### Evidence
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_two_threads_serialize_exclusive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_standalone_rebuild_takes_exclusive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestPortableFlock::test_windows_blocking_reentry_raises_instead_of_hanging_forever` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLockPlatformBackends::test_no_lock_primitive_refuses_loudly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 19 error(s), 4241 warning(s), 896 waived
- error-findings: AFFECT001@src/frob/process/_derived_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, E402@/home/logan/projects/frob/.claude/worktrees/t-3628/src/frob/process/_lock.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3628/src/frob/gates/__init__.py, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3628, REF002@src/frob/process/_lock_msvcrt.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, SELFAUDIT001@src/frob/process/_derived_lock.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
