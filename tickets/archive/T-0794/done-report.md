## Done report

Discharge T-0695's self-join-deadlock advisory on vet/_scan.py::_run_with_timeout, same shape T-0767 used for gates/_run_combined_jobs's pool-inside-pool. _run_with_timeout is the function `_scan_dependencies_parallel` dispatches as a worker task via ThreadPoolExecutor.submit, and its own body used to construct + shutdown an inner single-worker ThreadPoolExecutor -- exactly the self-join-deadlock co-occurrence shape (dispatched-as-task + owns join/shutdown/close on a pool). Hoisted the inner pool's construction into a new `_open_single_worker_pool` helper and its submit/await/shutdown into a new `_bounded_process_dependency` helper; `_run_with_timeout` is now a pure orchestrator with two branches (timeout is None -> direct call; else -> delegate to `_bounded_process_dependency`) and no pool calls of its own. Timeout semantics (per-package bound via `fut.result(timeout=...)`, TIMEOUT verdict via `_timeout_verdict`, non-blocking `shutdown(wait=False)` on both the success and timeout paths so the caller returns within ~timeout wall-clock) are preserved verbatim -- only moved to the new helper. Added a real-repo regression test mirroring T-0767's discharge test naming/shape (`test_self_join_deadlock_discharges_on_real_repo_vet_scan`) that asserts zero fork/pool-hazard findings across all four categories on src/frob/vet, alongside the existing synthetic fire fixtures (unchanged, still green) proving the detector itself was not weakened.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_vet_scan` (pytest node id, verified passing when recorded)
