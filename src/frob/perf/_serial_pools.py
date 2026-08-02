"""Serial-executor monkeypatch: the ProcessPoolExecutor half of T-0948's
fix (`_sampler.py`'s module docstring covers the ThreadPoolExecutor half).

`frob check`'s gate dispatch (`frob.check`/`frob.gates`) fans CPU-heavy
gates out onto a `ProcessPoolExecutor` -- fresh spawned interpreters, each
started via `multiprocessing`'s `spawn` context (`frob.gates._open_process_
pool`'s `mp_context=spawn`, T-0581's fork-safety fix). A `cProfile.Profile`
enabled in the profiling harness's own process (`frob.perf._harness`) has
no way to see time spent in a SEPARATE interpreter -- that gap is what the
T-0928 audit measured as the majority of `frob perf heat`'s "unattributed"
bucket (237 symbols attributed, 30.349s unattributed of a ~60s artifact).

Rather than editing `frob.gates`/`frob.check`'s pool-construction call
sites (out of T-0948's `src/frob/perf/**` scope, and it would permanently
change production gate-dispatch behavior for a profiling-only need), this
module replaces `ThreadPoolExecutor`/`ProcessPoolExecutor` with a
same-process, same-thread `SerialExecutor` for the DURATION of a profiled
run only (`install_serial_pools`, called from `frob.perf._harness.main`
under `FROB_PERF_SERIAL_POOLS=1`, on by default for `profile_command`).
Every "pool-dispatched" job then runs inline, on the thread that is
already under `cProfile`/`StackSampler` instrumentation -- turning the
unattributed cross-process/cross-thread gap into ordinary, fully-visible
call stack. This is the documented "serial diagnostic mode" the T-0948
audit named as an acceptable fix direction: profiling passes trade real
wall-clock parallelism for complete CPU-time attribution, which is exactly
what a profiling pass wants.
"""

# frob:waive INV006 preset="split-carried-prose"
from __future__ import annotations

import concurrent.futures
from collections.abc import Callable, Iterable, Iterator
from typing import Any, TypeVar

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["SERIAL_POOLS_ENV_VAR", "SerialExecutor", "install_serial_pools"]

# frob:doc docs/modules/perf.md#pool-dispatched-work-attribution-t-0948
#: The generic result type `SerialExecutor.submit`/`map` run and return --
#: no behavior of its own, just typing plumbing for the drop-in shape.
T = TypeVar("T")

# frob:doc docs/modules/perf.md#pool-dispatched-work-attribution-t-0948
#: Set to "1" (the profiling harness's default) to have `install_serial_
#: pools` replace both pool executors with `SerialExecutor` for the life
#: of the profiled process.
SERIAL_POOLS_ENV_VAR = "FROB_PERF_SERIAL_POOLS"


# frob:doc docs/modules/perf.md#pool-dispatched-work-attribution-t-0948
# frob:tests tests/unit/perf/test_serial_pools.py::TestSerialExecutor
class SerialExecutor:
    """A `concurrent.futures.Executor`-shaped drop-in that runs every job
    immediately, inline, on the calling thread -- accepts and ignores
    `ThreadPoolExecutor`/`ProcessPoolExecutor`'s constructor kwargs
    (`max_workers`, `mp_context`, ...) so it is a transparent substitute
    at either call site."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Accept and discard any `ThreadPoolExecutor`/`ProcessPoolExecutor`
        constructor arguments -- this executor has no pool to configure."""
        _log.debug("SerialExecutor: constructed (args=%r, kwargs=%r)", args, kwargs)

    # frob:doc docs/modules/perf.md#pool-dispatched-work-attribution-t-0948
    # frob:tests tests/unit/perf/test_serial_pools.py::TestSerialExecutor.test_submit_runs_inline_and_resolves  # noqa: E501
    def submit(
        self, fn: Callable[..., T], /, *args: Any, **kwargs: Any
    ) -> "concurrent.futures.Future[T]":
        """Run `fn(*args, **kwargs)` immediately and return an
        already-resolved `Future` -- same call happens on the SAME thread
        `submit` was called from, so it composes with a profiler/sampler
        that is already instrumenting that thread."""
        future: concurrent.futures.Future[T] = concurrent.futures.Future()
        try:
            result = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - propagate via Future, not raise here
            future.set_exception(exc)
        else:
            future.set_result(result)
        return future

    # frob:doc docs/modules/perf.md#pool-dispatched-work-attribution-t-0948
    # frob:tests tests/unit/perf/test_serial_pools.py::TestSerialExecutor.test_map_runs_eagerly_inline  # noqa: E501
    def map(
        self,
        fn: Callable[..., T],
        *iterables: Iterable[Any],
        timeout: float | None = None,
        chunksize: int = 1,
    ) -> Iterator[T]:
        """Serial equivalent of `Executor.map`: eagerly runs `fn` over
        `iterables` on the calling thread, ignoring `timeout`/`chunksize`
        (there is no pool to chunk work across)."""
        return iter([fn(*args) for args in zip(*iterables, strict=False)])

    # frob:doc docs/modules/perf.md#pool-dispatched-work-attribution-t-0948
    # frob:tests tests/unit/perf/test_serial_pools.py::TestSerialExecutor.test_shutdown_is_a_no_op  # noqa: E501
    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        """No-op: there is no pool/process to tear down."""

    def __enter__(self) -> "SerialExecutor":
        """Support the `with SerialExecutor(...) as pool:` shape both real
        executors use."""
        return self

    def __exit__(self, *exc_info: object) -> bool:
        """Calls `shutdown()`; never suppresses an exception from the
        `with` body."""
        self.shutdown()
        return False


# frob:doc docs/modules/perf.md#pool-dispatched-work-attribution-t-0948
# frob:tests tests/unit/perf/test_serial_pools.py::TestInstallSerialPools.test_with_serial_pools_worker_is_majority_attributed  # noqa: E501
# frob:waive AFFECT001 reason="T-1371 only widens the already-documented 'safe to call even if frob.gates fails to import' contract to cover any import-time surprise, not just ImportError -- no observable behavior change, so docs/modules/perf.md#pool-dispatched-work-attribution-t-0948 needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
def install_serial_pools() -> None:
    """Replace `ThreadPoolExecutor`/`ProcessPoolExecutor` with
    `SerialExecutor` everywhere frob's gate dispatch looks them up --
    both the `concurrent.futures.ThreadPoolExecutor(...)` attribute-access
    call shape (`frob.check`) and the `from concurrent.futures import
    ThreadPoolExecutor, ProcessPoolExecutor` bound-name shape
    (`frob.gates`). Meant to be called once, early, from the profiling
    harness (`frob.perf._harness.main`) before the profiled workload runs
    -- never from production `frob check` code, which must keep its real
    parallelism. Safe to call even if `frob.gates` fails to import (logs
    and continues with only the `concurrent.futures` patch applied)."""
    concurrent.futures.ThreadPoolExecutor = SerialExecutor  # type: ignore[misc,assignment]  # ty: ignore[invalid-assignment]  # noqa: E501
    concurrent.futures.ProcessPoolExecutor = SerialExecutor  # type: ignore[misc,assignment]  # ty: ignore[invalid-assignment]  # noqa: E501
    _log.info("install_serial_pools: concurrent.futures pool executors patched serial")
    try:
        import frob.gates as _frob_gates
    except ImportError:
        _log.warning(
            "install_serial_pools: frob.gates import failed, only the "
            "concurrent.futures-level patch is active"
        )
        return
    except Exception:
        # "Safe to call even if frob.gates fails to import" (this
        # function's own docstring) covers any import-time surprise, not
        # just `ImportError` (EXHAUST001, T-1371).
        _log.warning(
            "install_serial_pools: frob.gates import raised unexpectedly, "
            "only the concurrent.futures-level patch is active"
        )
        return
    _frob_gates.ThreadPoolExecutor = SerialExecutor  # type: ignore[attr-defined]  # ty: ignore[invalid-assignment]  # noqa: E501
    _frob_gates.ProcessPoolExecutor = SerialExecutor  # type: ignore[attr-defined]  # ty: ignore[invalid-assignment]  # noqa: E501
    _log.info("install_serial_pools: frob.gates bound pool executor names patched")
