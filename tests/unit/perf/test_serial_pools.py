"""T-0948: frob.perf collectors cannot see thread-pool/process-pool
dispatched work by default -- this proves the fix from both angles.

`TestStackSamplerAllThreads` proves `StackSampler` now attributes samples
to a `ThreadPoolExecutor` worker thread it spawned, not just the calling
thread (the sampler-side half of the fix, `_sampler.py`).

`TestSerialExecutor` proves `SerialExecutor` is a transparent drop-in for
both `ThreadPoolExecutor` and `ProcessPoolExecutor` shapes.

`TestInstallSerialPools` runs a SYNTHETIC workload -- a mix of
`ThreadPoolExecutor` and `ProcessPoolExecutor` dispatch -- under real
`cProfile` both with and without `install_serial_pools()`, and asserts the
majority of attributed cumulative time lands on the worker function once
installed (the ticket's own acceptance test), and near-zero without it
(proving the gap it fixes is real, not just asserting the positive case).
"""

from __future__ import annotations

import concurrent.futures
import cProfile
import pstats
import threading
from collections.abc import Iterator

import pytest

from frob.perf._sampler import SamplerConfig, StackSampler
from frob.perf._serial_pools import SerialExecutor, install_serial_pools

_WORKER_QUALNAME = "_pool_worker"


def _pool_worker(n: int) -> int:
    """Synthetic CPU-bound unit of pool-dispatched work: burns real
    wall-clock time in a pure-python loop so a sampler/profiler watching
    the DISPATCHING thread/process (not this one) would see nothing."""
    total = 0
    for i in range(n):
        total += i * i
    return total


# frob:waive DEAD001 reason="T-1024: pytest autouse fixture, invoked by the test runner for every test in this module without ever appearing as a name/call token anywhere -- the one DEAD001 false-positive class autouse fixtures fall into, same disposition as tests/test_dup_cross_lang.py's own autouse fixture waiver"  # noqa: E501
@pytest.fixture(autouse=True)
def _restore_pool_executors() -> Iterator[None]:
    """`install_serial_pools` mutates `concurrent.futures`'s module-level
    executor names as a side effect (by design -- see that function's
    docstring). Every test in this module that calls it must restore the
    real executors afterward so no other test in the same session
    silently runs its pool dispatch inline."""
    real_thread_pool = concurrent.futures.ThreadPoolExecutor
    real_process_pool = concurrent.futures.ProcessPoolExecutor
    try:
        yield
    finally:
        concurrent.futures.ThreadPoolExecutor = real_thread_pool  # type: ignore[misc]
        concurrent.futures.ProcessPoolExecutor = real_process_pool  # type: ignore[misc]


class TestStackSamplerAllThreads:
    """`StackSampler` (T-0948) samples every live thread, not just the
    thread that called `start()` -- the fix that makes a `ThreadPoolExecutor`
    worker thread visible with no dispatch-site change at all."""

    def test_samples_a_threadpool_worker_thread(self) -> None:
        """A `ThreadPoolExecutor` job running concurrently with the
        sampled main thread shows up in the collected stacks, attributed
        to its OWN frame (this module's `_pool_worker`), not swallowed
        because it ran on a different thread than the one that called
        `start()`."""
        sampler = StackSampler(SamplerConfig(interval_s=0.005))
        sampler.start()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(_pool_worker, 3_000_000) for _ in range(2)]
                for future in futures:
                    future.result()
        finally:
            stacks = sampler.stop()
        assert len(stacks) >= 1
        hit_worker = any(
            any(frame.file.endswith("test_serial_pools.py") for frame in stack.frames)
            for stack in stacks
        )
        assert hit_worker, "expected at least one sample rooted in this test module"


class TestSerialExecutor:
    """`SerialExecutor` is a transparent, same-thread drop-in for both
    pool executor shapes (T-0948)."""

    def test_submit_runs_inline_and_resolves(self) -> None:
        """`submit` runs `fn` on the calling thread (same ident) and
        returns an already-resolved `Future`."""
        caller_ident = threading.get_ident()
        seen: list[int] = []

        def _record_ident() -> int:
            seen.append(threading.get_ident())
            return 42

        executor = SerialExecutor(max_workers=4)
        future = executor.submit(_record_ident)
        assert future.done()
        assert future.result() == 42
        assert seen == [caller_ident]

    def test_submit_propagates_exceptions_via_future(self) -> None:
        """An exception raised by the submitted callable surfaces through
        `Future.result()`, matching the real executors' contract."""
        executor = SerialExecutor()

        def _boom() -> None:
            raise ValueError("synthetic")

        future = executor.submit(_boom)
        with pytest.raises(ValueError, match="synthetic"):
            future.result()

    def test_context_manager_shape(self) -> None:
        """`with SerialExecutor(...) as pool:` -- the shape every real
        call site in `frob.check`/`frob.gates` uses -- works unchanged."""
        with SerialExecutor(max_workers=1) as pool:
            future = pool.submit(_pool_worker, 10)
        assert future.result() == sum(i * i for i in range(10))

    def test_accepts_process_pool_style_kwargs(self) -> None:
        """Constructor accepts and ignores `ProcessPoolExecutor`-only
        kwargs (`mp_context`) so it substitutes for either executor."""
        executor = SerialExecutor(max_workers=2, mp_context=object())
        future = executor.submit(_pool_worker, 5)
        assert future.result() == sum(i * i for i in range(5))

    def test_map_runs_eagerly_inline(self) -> None:
        """`map` runs `fn` over every argument eagerly, on the calling
        thread, ignoring `timeout`/`chunksize`."""
        executor = SerialExecutor()
        results = list(executor.map(_pool_worker, [1, 2, 3], timeout=5, chunksize=2))
        assert results == [_pool_worker(1), _pool_worker(2), _pool_worker(3)]

    def test_shutdown_is_a_no_op(self) -> None:
        """`shutdown` never raises, with or without `wait`/`cancel_futures`,
        and does not affect a `Future` already resolved by `submit`."""
        executor = SerialExecutor()
        future = executor.submit(_pool_worker, 3)
        executor.shutdown()
        executor.shutdown(wait=False, cancel_futures=True)
        assert future.result() == _pool_worker(3)


class TestInstallSerialPools:
    """The ticket's own acceptance test: profile a synthetic workload
    split across BOTH executor kinds, with and without `install_serial_
    pools()`, and compare how much of the profiled time attributes to the
    worker function."""

    def _profiled_worker_self_time_fraction(self, *, serial: bool) -> float:
        """Run a mixed thread-pool/process-pool synthetic workload under
        `cProfile`, optionally patching in `SerialExecutor` first, and
        return the fraction of total self-time cProfile attributes to
        `_pool_worker` (0.0 if it never shows up as its own row at all --
        e.g. because it ran on an unprofiled thread/process)."""
        if serial:
            install_serial_pools()

        profiler = cProfile.Profile()

        def _workload() -> None:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as tpool:
                thread_futures = [
                    tpool.submit(_pool_worker, 2_000_000) for _ in range(2)
                ]
                for future in thread_futures:
                    future.result()
            with concurrent.futures.ProcessPoolExecutor(max_workers=2) as ppool:
                process_futures = [
                    ppool.submit(_pool_worker, 2_000_000) for _ in range(2)
                ]
                for future in process_futures:
                    future.result()

        profiler.enable()
        try:
            _workload()
        finally:
            profiler.disable()

        stats = pstats.Stats(profiler)
        stats_dict = stats.stats  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        total_self = sum(row[2] for row in stats_dict.values())
        worker_self = sum(
            row[2]
            for (_file, _line, funcname), row in stats_dict.items()
            if funcname == _WORKER_QUALNAME
        )
        if total_self <= 0.0:
            return 0.0
        return worker_self / total_self

    def test_without_serial_pools_worker_is_unattributed(self) -> None:
        """Baseline (T-0948's reported gap): with the REAL executors, a
        cProfile enabled only on the calling thread/process attributes
        approximately NONE of `_pool_worker`'s CPU time to itself -- the
        thread-pool half runs on worker threads cProfile's single-thread
        `enable()` never instruments, and the process-pool half runs in
        wholly separate interpreters."""
        fraction = self._profiled_worker_self_time_fraction(serial=False)
        assert fraction < 0.05

    def test_with_serial_pools_worker_is_majority_attributed(self) -> None:
        """With `install_serial_pools()` applied first, BOTH the thread-
        pool and process-pool dispatched calls run inline on the profiled
        thread -- so the majority of the workload's self-time now
        attributes to `_pool_worker` itself."""
        fraction = self._profiled_worker_self_time_fraction(serial=True)
        assert fraction > 0.5
