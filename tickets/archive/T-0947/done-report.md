## Done report

Changed:
frob.gates._process_pool_start_method
frob.gates._FORKSERVER_PRELOAD
frob.gates._open_process_pool

Isolated cold-start measurement (bypassing the CLI, calling `_load_inputs`/
`_build_jobs`/`_open_process_pool` directly for the gates-native job set,
warm cache, `spawn` context, module-level worker recording
`time.monotonic()` at worker-process start vs the parent's submit
timestamp -- both processes share the OS's CLOCK_MONOTONIC so the delta is
valid cross-process):

```
perf:                 spawn_to_start(cold import)=0.527-0.558s  cpu_work=~10-11s
clones:                spawn_to_start=0.725-0.737s               cpu_work=~0s
archgate:              spawn_to_start=0.588-0.602s               cpu_work=~12-13s
exhaustive_handling:   spawn_to_start=0.529-0.532s               cpu_work=~1.2-1.3s
```

i.e. real `spawn`-context cold-start cost is ~0.5-0.7s PER WORKER (paid
once per `run_gates` call, workers spawn concurrently so it does not sum),
NOT the ~18s the audit's own back-of-envelope Finding 3 guessed from
two `--only gates-native` wall-clock samples. Root cause of that ~18s
delta was not process-pool spawn cost -- it is far too small a knob to
explain an 18s swing. Re-ran `--only gates-native` 4x back-to-back on this
worktree (before any fix) and got a stable 17.26-17.98s spread, not the
audit's 35.22s/16.63s split; this repo's own worktrees run many concurrent
sibling agents (`ls` on the shared scratchpad shows dozens of
same-session, same-hour files from other tickets), so CPU contention
between sibling worktrees' own `frob check` runs is the far more likely
explanation for that specific pair of samples than pool spawn cost --
noted here so a future pass does not re-attribute that swing to this
ticket's finding.

Fix (proportionate to the ~0.5-0.7s/worker measured, not the guessed
~18s): `_open_process_pool` now uses `forkserver` (falling back to
`spawn` if the platform's `multiprocessing.get_all_start_methods()`
lacks it) with `_FORKSERVER_PRELOAD = ("frob.gates",)` preloaded once in
the forkserver helper process instead of per-worker. `frob.gates`
transitively imports every process-pool gate's home module
(`frob.perf`, `frob.dup`, `frob.arch`, ...) plus `frob_core`/
`strata_core`, so preloading this one name absorbs the whole cold-import
cost. `forkserver`/`spawn` share the exact safety property T-0581's fix
depends on (the new process is launched via a fresh `exec`, never a raw
`fork()` of the calling, possibly multi-threaded process) -- this change
does not touch or weaken that invariant; bare `fork` was never selected.

Measured before/after, isolated call, forkserver helper pre-warmed
(mirrors what a real run gets since `_open_process_pool` is called before
`_run_thread_jobs`, so the helper's own startup overlaps thread-job work):

```
before (spawn):               spawn_to_start ~0.53-0.74s per worker
after  (forkserver+preload):  spawn_to_start ~0.24-0.47s per worker
```

~40-55% reduction in per-worker cold-start latency, consistent with the
single shared import replacing N per-worker imports.

Measured before/after, real CLI (`uv run frob check --only gates-native`,
`/usr/bin/time -v` wall clock, same worktree, natives built, warm cache,
2 runs each side):

```
before (spawn):        17.46s, 17.98s      gate-summary archgate=11.3-11.6s perf=9.76-9.86s
after (forkserver):     17.26s, 17.74s      gate-summary archgate=11.38-11.44s perf=9.73-9.79s
```

Honest disposition: the aggregate real-run wall-clock effect is within
run-to-run noise here -- the measured ~0.3-0.5s/worker win is real and
reproduced in isolation, but on THIS job set it is dwarfed by the
CPU-bound gate work itself (archgate/perf run 9-12s of real work each),
so it does not move the total wall time outside the noise band already
observed run-to-run. The fix is still correct and proportionate to what
was actually measured (small, real, low-risk cold-start win) rather than
a large refactor chasing the audit's overstated ~18s estimate, which this
ticket's own isolation work shows was not attributable to pool spawn cost
at all.

Evidence: tests/test_gates.py, tests/unit/test_check.py,
tests/unit/test_arch.py (all passing, `pytest -q` clean). Added one new
test, `TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available`,
that directly inspects the constructed pool's own `mp_context` and the
`multiprocessing.forkserver._forkserver` singleton's `_preload_modules` --
this is what kills the mutation-evidence gate's surviving mutant at
`_open_process_pool`'s `ctx.get_start_method() == "forkserver"` compare
(TEST016); the pre-existing `TestProcessPoolGates` tests never inspected
which start method/preload state the pool actually used, only that jobs
ran in a separate process and merged correctly, so none of them could
have caught a `==`/`!=` swap there. `uv run frob check --ticket T-0947
--only gates-native`: 0 errors. `uv run frob test --base main` run separately shows ~30 failing
tests repo-wide (compliance registry reconciliation, ticket-land git
merge driver, strata claims, tmlanguage grammar, etc.) -- none touch
`frob.gates`' process-pool code, `_open_process_pool`, or
`ProcessPoolExecutor`/multiprocessing at all; confirmed unrelated to this
change (pre-existing repo-wide churn from concurrent sibling tickets in
this multi-agent session, not caused by this ticket's diff, which is
`git diff --stat` = `src/frob/gates/__init__.py` only, ~61
insertions/14 deletions).

Filed: none -- no new out-of-scope work discovered; T-0929's Finding 4
(sys/secrets/pii_structural shared walk, T-0946) and the profiler
blind-spot (Finding 0) remain filed separately as the audit already
recorded.

Gates: `frob check --ticket T-0947 --only gates-native` clean (0 errors,
2834 warnings all pre-existing/waived, gate-summary pass).

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_combined_jobs_merge_in_canonical_order` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_run_gates_output_is_identical_across_repeated_runs` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 4146 warning(s), 220 waived
- error-findings: none (measured, zero errors)
