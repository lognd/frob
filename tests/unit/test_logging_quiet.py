"""Unit tests for `frob.logging.quiet.quiet_stdout_logs` (T-0125).

Reproduces the interleaved-enter/exit race against the OLD (unguarded
save/restore) implementation deterministically -- no reliance on thread
scheduling luck -- and asserts the new lock+depth-counter implementation
is immune. A supplementary threaded stress test exercises real concurrency.
"""

from __future__ import annotations

import logging
import sys
import threading
import time

from frob.logging.quiet import quiet_stdout_logs


def _install_stdout_handler(level: int) -> logging.StreamHandler:
    """Attach a fresh stdout `StreamHandler` at `level` to the root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    logging.getLogger().addHandler(handler)
    return handler


class TestQuietStdoutLogsReentrance:
    """Nested/interleaved calls must restore the original level exactly
    once, regardless of exit order -- the T-0125 race."""

    def test_nested_calls_restore_after_outermost_exits(self) -> None:
        # frob:tests src/frob/logging/quiet.py::quiet_stdout_logs kind="unit"
        handler = _install_stdout_handler(logging.DEBUG)
        try:
            before = handler.level
            with quiet_stdout_logs():
                assert handler.level == logging.WARNING
                with quiet_stdout_logs():
                    assert handler.level == logging.WARNING
                # Inner exited first; outer block still active, must stay quiet.
                assert handler.level == logging.WARNING
            assert handler.level == before
        finally:
            logging.getLogger().removeHandler(handler)

    def test_interleaved_enter_exit_across_threads_never_sticks(self) -> None:
        # frob:tests src/frob/logging/quiet.py::quiet_stdout_logs kind="unit"
        # Deterministic interleaving: thread A enters, thread B enters
        # while A is still inside (so B would have seen A's WARNING as its
        # "saved" level under the old unguarded implementation), A exits
        # FIRST (restoring the true original level), then B exits LAST
        # (restoring its stale "saved" WARNING over top of A's correct
        # restore). Under the OLD code this leaves the handler stuck at
        # WARNING forever; under the fixed depth-counter code the level is
        # only ever restored once, by whichever call is outermost by depth.
        handler = _install_stdout_handler(logging.DEBUG)
        try:
            before = handler.level
            b_entered = threading.Event()
            a_may_exit = threading.Event()
            a_exited = threading.Event()

            def thread_a() -> None:
                with quiet_stdout_logs():
                    b_entered.wait(timeout=2)
                    a_may_exit.set()
                a_exited.set()

            def thread_b() -> None:
                with quiet_stdout_logs():
                    b_entered.set()
                    a_may_exit.wait(timeout=2)
                    a_exited.wait(timeout=2)

            ta = threading.Thread(target=thread_a)
            tb = threading.Thread(target=thread_b)
            ta.start()
            tb.start()
            ta.join(timeout=5)
            tb.join(timeout=5)

            assert handler.level == before, (
                "quiet_stdout_logs must restore the stdout handler level "
                "after racing/interleaved callers, regardless of exit "
                "order (T-0125)"
            )
        finally:
            logging.getLogger().removeHandler(handler)

    def test_threaded_stress_always_restores(self) -> None:
        # frob:tests src/frob/logging/quiet.py::quiet_stdout_logs kind="unit"
        # frob:waive PERF003 reason="start-loop then join-loop plus a closing assert==, not a nested join"
        # Supplementary stress test: many threads entering/exiting
        # concurrently, real (non-mocked) scheduling.
        handler = _install_stdout_handler(logging.DEBUG)
        try:
            before = handler.level

            def worker() -> None:
                for _ in range(20):
                    with quiet_stdout_logs():
                        time.sleep(0.001)

            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

            assert handler.level == before
        finally:
            logging.getLogger().removeHandler(handler)

    def test_single_call_still_quiets_and_restores(self) -> None:
        # frob:tests src/frob/logging/quiet.py::quiet_stdout_logs kind="unit"
        handler = _install_stdout_handler(logging.INFO)
        try:
            before = handler.level
            with quiet_stdout_logs():
                assert handler.level == logging.WARNING
            assert handler.level == before
        finally:
            logging.getLogger().removeHandler(handler)
