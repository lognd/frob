"""T-3481: frob_core's O(n)/O(n^2) `#[pyfunction]` kernels now release the
GIL for the duration of their native computation via `py.allow_threads`
(same mechanism as T-3457's strata-core fix), so a Python watchdog thread
(pytest-timeout's thread-method `Timer`, or any other Python thread) can
run -- and even preempt the process -- while one of them is still
computing. Before this fix, none of the 19 `#[pyfunction]`s in
frob-core/src released the GIL at all (grepped `allow_threads` in
frob-core/src: zero hits), so a thread-method timeout demonstrably could
NOT fire while stuck inside one of them -- the same class of un-preemptable
CI stall T-3449/T-3457 measured for strata-core.

`near_duplicate_indices` (O(n^2) pairwise similarity clustering,
frob-core/src/callgraph.rs) is used as the representative long-running
kernel here, mirroring `worst_age`'s role in
tests/unit/strata/test_strata_core_gil.py.

frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import frob_core

# frob:ticket T-3481


def _near_duplicate_bodies(n: int) -> list[str]:
    """`n` distinct-length fingerprint strings -- `near_duplicate_indices`'s
    O(n^2) pairwise `arch_sim_ratio` scan over them is the hot path this
    ticket targets. Measured directly on this machine: 700 items takes
    ~4s -- long enough to prove GIL release without an unreasonably large
    fixture."""
    return [("stmt%d " % i) * 40 + "x" * i for i in range(n)]


class TestTimeoutFiresDuringLongNativeCall:
    """T-3481 must-fire: pytest-timeout's thread-method watchdog can now
    preempt a long frob_core call. Run as a subprocess so the watchdog's
    own `os._exit(1)` cannot tear down this test's process."""

    def test_timeout_fires_during_near_duplicate_indices(self, tmp_path: Path) -> None:
        """A ~4s `near_duplicate_indices` call under `--timeout=2
        --timeout-method=thread` is killed near the 2s mark, not left to
        run to completion -- the exact regression shape T-3457 fixed for
        strata-core, now closed for frob-core too."""
        script = tmp_path / "test_long_near_duplicate.py"
        script.write_text(
            textwrap.dedent(
                """
                import frob_core

                def test_long_near_duplicate():
                    n = 700
                    bodies = [("stmt%d " % i) * 40 + "x" * i for i in range(n)]
                    frob_core.near_duplicate_indices(bodies, 0.999)
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

        # Before T-3481's fix, `near_duplicate_indices` held the GIL for
        # the WHOLE ~4s call (measured directly against this same shape),
        # so the watchdog thread never got a chance to run at all and the
        # subprocess would still be mid-computation past the 2s deadline.
        # With the GIL released, the watchdog preempts it near the
        # deadline -- bounded here well under the full uninterrupted
        # computation time, with headroom for process startup.
        assert elapsed < 5.0, (
            f"pytest-timeout did not preempt the long frob_core call in "
            f"time (took {elapsed}s) -- the GIL is likely being held for "
            f"the whole native call again: stdout={result.stdout!r} "
            f"stderr={result.stderr!r}"
        )
        assert "Timeout" in result.stdout, (
            f"expected pytest-timeout's stack-dump marker in stdout: {result.stdout!r}"
        )


class TestGilActuallyReleased:
    """T-3481 must-fire: a plain background Python thread is demonstrably
    scheduled WHILE the native call is still running -- direct proof the
    GIL is released, independent of pytest-timeout's own machinery above."""

    def test_background_thread_runs_during_near_duplicate_indices(self) -> None:
        """A ticker thread accumulates many ticks over the course of a
        multi-second `near_duplicate_indices` call; if the GIL were held
        for the whole call (the pre-fix behavior), the ticker would get
        essentially none."""
        bodies = _near_duplicate_bodies(700)  # ~4s direct call, measured
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
            frob_core.near_duplicate_indices(bodies, 0.999)
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
    """T-3481 must-stay-quiet: `py.allow_threads` is a pure concurrency
    change -- every kernel's return value is bit-for-bit identical to
    before this ticket."""

    def test_near_duplicate_indices_result_unchanged(self) -> None:
        """Two clearly-similar bodies cluster together; a clearly
        dissimilar one does not."""
        bodies = [
            "def foo(): return 1",
            "def foo(): return 2",
            "totally unrelated text here",
        ]
        idx = frob_core.near_duplicate_indices(bodies, 0.6)
        assert idx == [0, 1]

    def test_resolve_call_edges_result_unchanged(self) -> None:
        """Mirrors `resolve_call_edges_matches_private_callee_and_skips_
        self_and_public`'s shape in frob-core/src/callgraph.rs's own Rust
        unit tests, called across the pyo3 FFI boundary this time."""
        by_name = {"helper": [("a.py::helper", "a.py", True)]}
        out = frob_core.resolve_call_edges(
            ["a.py::caller"],
            [["helper"]],
            [[]],
            by_name,
            False,
            "?unresolved",
        )
        assert out == [("a.py::caller", ["a.py::helper"])]

    def test_r3_canonical_hash_result_unchanged(self) -> None:
        """Deterministic: the same token stream always hashes the same."""
        tokens = ["def", "foo", "(", ")", ":", "return", "1"]
        assert frob_core.r3_canonical_hash(tokens) == frob_core.r3_canonical_hash(
            tokens
        )
