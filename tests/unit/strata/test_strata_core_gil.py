"""T-3457: strata_core's O(graph) `#[pyfunction]` kernels (`reachable`,
`worst_age`, `propagated_demand`, `vmodel_check`) now release the GIL for
the duration of their native computation via `py.allow_threads`, so a
Python watchdog thread (pytest-timeout's thread-method `Timer`, or any
other Python thread) can run -- and even preempt the process -- while one
of them is still computing. Before this fix, none of them released the
GIL at all (grepped `allow_threads` in strata-core/src: zero hits), so a
thread-method timeout demonstrably could NOT fire while stuck inside one
of them: T-3449 measured a real CI stall (19 minutes, un-preempted) and
reproduced it directly -- `--timeout=5 --timeout-method=thread` on a
strata_core-backed test ran to completion in 67s with the watchdog never
firing once, while a synthetic `time.sleep(20)` test with `--timeout=3`
fired correctly at 3.7s.

frob:doc docs/strata/kernel.md#strata-core
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import strata_core

# frob:ticket T-3457


def _long_chain_edges(n: int) -> list[tuple[str, str, str, float]]:
    """A single `n`-hop chain of `AgedEdge`s -- `worst_age`'s SCC/topo-sort
    DP over it is the O(graph) hot path this ticket targets. Measured
    directly on this machine: 5000 hops takes ~4s, 6000 ~6s -- long enough
    to prove GIL release without an unreasonably large fixture."""
    return [(f"f{i}", f"n{i}", f"n{i + 1}", 1.0) for i in range(n)]


class TestTimeoutFiresDuringLongNativeCall:
    """T-3457 must-fire: pytest-timeout's thread-method watchdog can now
    preempt a long strata_core call. Run as a subprocess so the
    watchdog's own `os._exit(1)` cannot tear down this test's process."""

    def test_timeout_fires_during_worst_age(self, tmp_path: Path) -> None:
        """A ~6s `worst_age` call under `--timeout=2 --timeout-method=thread`
        is killed near the 2s mark, not left to run to completion -- the
        exact regression T-3449 measured and this ticket fixes."""
        script = tmp_path / "test_long_worst_age.py"
        script.write_text(
            textwrap.dedent(
                """
                import strata_core

                def test_long_worst_age():
                    n = 6000
                    edges = [
                        (f"f{i}", f"n{i}", f"n{i + 1}", 1.0)
                        for i in range(n)
                    ]
                    strata_core.worst_age(edges, f"n{n}")
                """
            ),
            encoding="utf-8",
        )
        t0 = time.monotonic()
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-p",
                "no:xdist",
                "-q",
                "--timeout=2",
                "--timeout-method=thread",
                str(script),
            ],
            capture_output=True,
            text=True,
            timeout=9,
        )
        elapsed = time.monotonic() - t0

        # Before T-3457's fix, `worst_age` held the GIL for the WHOLE ~6s
        # call (measured directly against this same shape), so the
        # watchdog thread never got a chance to run at all and the
        # subprocess would still be mid-computation past the 2s deadline.
        # With the GIL released, the watchdog preempts it near the
        # deadline -- bounded here well under the full uninterrupted
        # computation time, with headroom for process startup.
        assert elapsed < 5.0, (
            f"pytest-timeout did not preempt the long strata_core call in "
            f"time (took {elapsed}s) -- the GIL is likely being held for "
            f"the whole native call again: stdout={result.stdout!r} "
            f"stderr={result.stderr!r}"
        )
        assert "Timeout" in result.stdout, (
            f"expected pytest-timeout's stack-dump marker in stdout: {result.stdout!r}"
        )


class TestGilActuallyReleased:
    """T-3457 must-fire: a plain background Python thread is demonstrably
    scheduled WHILE the native call is still running -- direct proof the
    GIL is released, independent of pytest-timeout's own machinery above."""

    def test_background_thread_runs_during_worst_age(self) -> None:
        """A ticker thread accumulates many ticks over the course of a
        multi-second `worst_age` call; if the GIL were held for the whole
        call (the pre-fix behavior), the ticker would get essentially none."""
        edges = _long_chain_edges(5000)  # ~4s direct call, measured
        ticks = 0
        stop = threading.Event()

        def _ticker() -> None:
            nonlocal ticks
            while not stop.is_set():
                ticks += 1
                time.sleep(0.01)

        thread = threading.Thread(target=_ticker, daemon=True)
        thread.start()
        try:
            t0 = time.monotonic()
            strata_core.worst_age(edges, "n5000")
            elapsed = time.monotonic() - t0
        finally:
            stop.set()
            thread.join(timeout=2)

        assert elapsed > 1.0, f"fixture too fast to prove anything ({elapsed}s)"
        assert ticks > 5, (
            f"background thread only ticked {ticks} time(s) during a "
            f"{elapsed}s native call -- the GIL does not appear to be "
            f"released"
        )


class TestResultsUnchanged:
    """T-3457 must-stay-quiet: `py.allow_threads` is a pure concurrency
    change -- every kernel's return value is bit-for-bit identical to
    before this ticket."""

    def test_worst_age_result_unchanged(self) -> None:
        """Mirrors `worst_age_takes_the_stalest_path`'s shape in
        strata-core/src/lib.rs's own Rust unit tests, called across the
        pyo3 FFI boundary this time."""
        edges = [
            ("f1", "truth", "replica", 300.0),
            ("f2", "replica", "view", 30.0),
            ("f3", "truth", "view", 0.0),
        ]
        age, path = strata_core.worst_age(edges, "view")
        assert age == 330.0
        assert path == ["truth", "f1", "replica", "f2", "view"]

    def test_reachable_result_unchanged(self) -> None:
        """Mirrors `reachable_returns_witness_paths`'s shape in
        strata-core/src/lib.rs's own Rust unit tests."""
        edges = [
            ("f1", "a", "b", False, True),
            ("f2", "b", "c", False, True),
        ]
        paths = strata_core.reachable(edges, "a", False)
        assert paths["c"] == ["a", "f1", "b", "f2", "c"]

    def test_propagated_demand_result_unchanged(self) -> None:
        """Mirrors `propagated_demand_chain_multiplies_fanout`'s shape in
        strata-core/src/lib.rs's own Rust unit tests."""
        edges: list[tuple[str, str, str, float | None, float]] = [
            ("f1", "src", "a", 10.0, 2.0),
            ("f2", "a", "b", None, 3.0),
        ]
        value, _witness = strata_core.propagated_demand(edges, "b")
        assert value == 60.0
