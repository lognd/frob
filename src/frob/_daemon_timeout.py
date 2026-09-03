"""Daemon-thread-backed bounded call (T-3708).

`frob.lang._run_parse_with_timeout` and `frob.vet._scan._bounded_process_dependency`
both need to run a caller-supplied callable under a wall-clock budget and,
on expiry, abandon the still-running worker rather than block the caller
past that budget -- neither tree-sitter/strata-core parses nor
`_process_dependency` expose a cancellation hook.

The straightforward way to do this is `ThreadPoolExecutor(max_workers=1)` +
`future.result(timeout=...)` + `executor.shutdown(wait=False)` on expiry.
That shape LOOKS like it abandons the worker, but does not: every worker
thread `concurrent.futures.thread` has ever created is kept in a process-
global weak registry, and the module registers its own `atexit` handler
(`_python_exit`) that unconditionally joins every thread still alive in
that registry at interpreter shutdown -- including ones a caller believes
it abandoned via `shutdown(wait=False)`. If the abandoned callable is
genuinely still blocked when the process later tries to exit, interpreter
shutdown hangs until that thread finishes. This was the actual cause of
the win32 CI ~120s post-check-pipeline gap (T-3707 ruled out `frob.gates`'
`ProcessPoolExecutor`; T-3708 traced it to this atexit-join hazard).

`_run_bounded` avoids the hazard entirely by never going through
`ThreadPoolExecutor`: it spawns a plain `daemon=True` `threading.Thread`,
which `concurrent.futures.thread` never registers and the interpreter
never joins at exit. Timeout/result/exception semantics otherwise match
`Future.result(timeout=...)` exactly, so this is a drop-in replacement at
both call sites.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import TypeVar

_T = TypeVar("_T")

#: name prefix given to every worker thread `_run_bounded` spawns, so a
#: thread dump (or the T-3708 regression test enumerating live threads)
#: can identify one at a glance.
_THREAD_NAME_PREFIX = "frob-bounded-"


# frob:ticket T-3708
# frob:tests tests/test_lang.py::TestSizeCapAndTimeout.test_timed_out_worker_is_daemon_not_registered  # noqa: E501
# frob:tests tests/vet_suite/test_scan_tree.py::TestScanTreeTimeout.test_timed_out_worker_is_daemon_not_registered  # noqa: E501
def _run_bounded(fn: Callable[[], _T], timeout: float) -> _T:
    """Run zero-arg `fn` on a dedicated daemon thread, returning its result
    within `timeout` seconds.

    Raises `concurrent.futures.TimeoutError` if `fn` has not finished
    within `timeout` -- the worker thread is abandoned, not killed (no
    Python primitive can preempt a running thread), but because it is a
    daemon thread `concurrent.futures.thread`'s atexit-registered
    `_python_exit()` never waits on it, so an abandoned, still-running
    worker cannot block interpreter shutdown (T-3708). If `fn` raises
    within the budget, that same exception is re-raised here, matching
    `Future.result()`'s propagation contract.
    """
    result_box: list[_T] = []
    error_box: list[BaseException] = []
    done = threading.Event()

    def _target() -> None:
        try:
            result_box.append(fn())
        except BaseException as exc:  # noqa: BLE001 -- propagate fn's own error surface verbatim, see module docstring
            error_box.append(exc)
        finally:
            done.set()

    worker = threading.Thread(
        target=_target, name=f"{_THREAD_NAME_PREFIX}{fn!r}", daemon=True
    )
    worker.start()
    if not done.wait(timeout=timeout):
        raise FutureTimeoutError
    if error_box:
        raise error_box[0]
    return result_box[0]
