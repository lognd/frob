## Done report

Two independent fixes, entirely inside `src/frob/perf/**` (no change to
`frob.gates`/`frob.check`'s own dispatch code): (1) `StackSampler`
(`_sampler.py`) now samples EVERY live thread each tick instead of only the
thread that called `start()` -- `sys._current_frames()` already returns
every OS thread's frame in the process, so a `ThreadPoolExecutor` worker
thread spawned from the same interpreter was always present in that
snapshot; the collector was simply discarding it. (2) A new
`frob.perf._serial_pools.SerialExecutor` (a same-thread,
`concurrent.futures.Executor`-shaped drop-in) plus `install_serial_pools()`,
wired into the profiling harness (`frob.perf._harness.main`, on by default,
opt out via `FROB_PERF_SERIAL_POOLS=0`) -- monkeypatches both
`concurrent.futures.ThreadPoolExecutor`/`ProcessPoolExecutor` (the
attribute-access shape `frob.check` uses) and `frob.gates`'s own bound names
for the same (the `from concurrent.futures import ...` shape) so every
pool-dispatched job runs inline, on the already-profiled thread, for the
duration of a profiling run only. This is the "serial diagnostic mode" fix
direction the ticket named, achieved with no change to `frob.gates`/
`frob.check` -- production `frob check` keeps its real parallelism
unconditionally.

Real-world verification (`frob perf profile -- python -m frob check --only
gates-native`, the process-pool-heavy stage group this ticket's own audit
measured): WITHOUT the fix (`FROB_PERF_SERIAL_POOLS=0`), total_s=17.788,
`frob perf heat` reports "237 symbol(s) attributed, 17.428s unattributed"
(98.0% of wall time unattributed -- reproduces the audit's own
237-symbols-attributed figure, on the process-pool-heavy group in
isolation). WITH the fix (default), total_s=206.943 (expected -- serial +
fully profiled trades real parallelism for full visibility), `frob perf
heat` reports "715 symbol(s) attributed, 94.260s unattributed" (45.5% of
wall time unattributed). Net: attributed symbol count 237 -> 715 (3x),
unattributed fraction 98.0% -> 45.5%. The remaining unattributed time is
largely native Rust-extension call time (`frob_core`/`strata_core`)
cProfile cannot attribute to a python source line regardless of threading
-- a different, out-of-scope gap.

Land was refused on TEST016: `install_serial_pools()`'s guard in
`_harness.main` (`os.environ.get(SERIAL_POOLS_ENV_VAR, "1") != "0"`) had a
surviving `!=` -> `==` mutant -- the bound evidence exercised the harness's
observable OUTPUT (pstats/log lines) but never asserted on that exact
comparison's decision. Added `TestHarnessSerialPoolsDecision` (`tests/unit/
perf/test_harness_sampling.py`), spying on `install_serial_pools` via
monkeypatch and asserting it IS called when the env var is unset/"1" and is
NOT called when "0" -- directly exercises both branches of the mutated
comparison. Hand-verified the kill: flipped `!=` to `==` in `_harness.py`,
all three new tests failed, reverted the edit (`sha256sum` byte-identical
before/after), tests pass again clean.

### Changed
- `src/frob/perf/_sampler.py::StackSampler.start` / `StackSampler._run`
- `src/frob/perf/_serial_pools.py::SerialExecutor` (new)
- `src/frob/perf/_serial_pools.py::install_serial_pools` (new)
- `src/frob/perf/_harness.py::main`
- `src/frob/perf/__init__.py` (re-exports)
- `docs/modules/perf.md` (new "Pool-dispatched work attribution (T-0948)" section)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision` (new, TEST016 fix)

### Evidence
- `tests/unit/perf/test_serial_pools.py::TestStackSamplerAllThreads::test_samples_a_threadpool_worker_thread` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_submit_runs_inline_and_resolves` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_submit_propagates_exceptions_via_future` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_context_manager_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_accepts_process_pool_style_kwargs` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_map_runs_eagerly_inline` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_shutdown_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_without_serial_pools_worker_is_unattributed` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_with_serial_pools_worker_is_majority_attributed` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_unset_installs_serial_pools` (pytest node id, verified passing when recorded; also verified FAILING against the `!=`->`==` mutant)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_one_installs_serial_pools` (pytest node id, verified passing when recorded; also verified FAILING against the `!=`->`==` mutant)
- `tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_zero_skips_serial_pools` (pytest node id, verified passing when recorded; also verified FAILING against the `!=`->`==` mutant)

### Captured claims
- tests: 12 passed (`uv run pytest tests/unit/perf/ -q`, 122 passed)
- gates: `frob check --ticket T-0948` clean across lint/static/gates-fast/gates-native/gates-security (0 errors; gate:TEST/TEST016 clean)
- error-findings: none (measured, zero errors)

Filed: none -- no out-of-scope work discovered.
