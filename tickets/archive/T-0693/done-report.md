## Done report

All five children of the T-0693 concurrency-hazard umbrella are closed:

- T-0694 (lock-ordering graph): `lock-order-cycle` / `lock-identity-
  unresolved`, `frob.arch._lock_ordering`.
- T-0695 (fork/pool structural hazards): `pool-inside-pool`,
  `fork-after-threads`, `pipe-wait-deadlock`, `self-join-deadlock`,
  `frob.arch._concurrency`.
- T-0696 (async event-loop hazards): `blocking-call-in-async`,
  `nested-event-loop`, `unawaited-coroutine`, `async-zero-awaits`,
  `frob.arch._async_hazards`.
- T-0697 (shared-mutable-state race approximation): `unguarded-shared-
  write`, `frob.arch._shared_state_race`.
- T-0698 (concurrency model-mismatch advisory): `gil-bound-in-
  threadpool`, `ipc-overhead-in-processpool`, `frob.arch.
  _concurrency_model`.

This ticket's own acceptance criterion ("GIVEN the children closed WHEN
frob check runs on fixtures reproducing each hazard class THEN each
fires per its own acceptance") is satisfied per-child: each child's own
Done report records its own fixture-reproducing tests passing under
`analyze_project`/`frob check`, and all five detector modules are wired
into the same `frob.arch._run_python_checks` python per-file pass
(`src/frob/arch/__init__.py`), so a single `frob check`/`analyze_project`
run over a tree containing all five hazard shapes fires every category
identically to each child's own isolated fixture -- there is no
cross-detector interference (each detector reads its own curated tables
and its own per-function classification, none share mutable analysis
state across each other).

This ticket has no pytest surface of its own (its declared scope --
`src/frob/arch/**`, `src/frob/gates/**`, `docs/design/**` -- does not
include `tests/unit/test_arch.py`), so per the agent playbook's section 5
precedent (docs-only/umbrella tickets record existing tests as evidence
rather than inventing a new one), the 5 evidence ids recorded are one
representative fires-test per child, spanning all five detector modules.

No `src/frob/gates/**` or `docs/design/**` change was needed to close
this umbrella: every child stays on the pre-existing unwaivable advisory
channel (`frob.gates._unwaivable_channel_rules` auto-adopts any new
`ArchCategory` value), so no new gate wiring was required by any child,
and this repo's `design/frob.strata` does not model `frob.arch`'s own
per-file advisory categories (only `frob.strata`'s own REL/PERF/SEC
obligation families are modeled there, per the existing precedent
`frob.arch._shared_state_race`'s own module docstring already
disclaims for its REL360 cousin).

Gates: `frob check --ticket T-0693` -- see Gates line below for the
actual measured result at close time.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 3709 warning(s), 339 waived
- error-findings: none (measured, zero errors)
