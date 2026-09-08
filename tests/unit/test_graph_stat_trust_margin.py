"""Tests for `frob.graph`'s measured stat-trust margin (T-4279).

Kept in its own small file rather than `tests/test_gate_cache.py` (which
already carries T-4257's own `TestStatKeyCoarseClockSafety` tests):
adding a new file to a narrowly-scoped ticket avoids dragging a large,
heavily cross-referenced shared test file's own unrelated private-helper
fan-out into this ticket's scope (the same SCOPE002 "probable
under-capture" cascade measured and documented while working the sibling
ticket T-4282).
"""

from __future__ import annotations

import time
from pathlib import Path

import frob.graph as graph_module


class TestProbeMtimeGranularityNs:
    """`_probe_mtime_granularity_ns` (T-4279): measures the mount's
    OBSERVED mtime-update granularity via real writes, not a synthetic
    `os.utime` round trip (which measures storage precision, a different
    and here irrelevant property -- see the function's own docstring)."""

    # frob:tests src/frob/graph/__init__.py::_probe_mtime_granularity_ns
    def test_real_probe_returns_a_plausible_small_value(self, tmp_path: Path) -> None:
        """Smoke test against this repo's own real dev mount: whatever
        the measured granularity is, it must be a positive value drawn
        from the declared candidate list, never wildly larger than any
        of them (which would signal a probe bug, not a genuinely coarse
        mount -- this repo's CI/dev filesystems are all sub-second)."""
        granularity_ns = graph_module._probe_mtime_granularity_ns(tmp_path)
        assert granularity_ns is not None
        assert granularity_ns in graph_module._MTIME_GRANULARITY_CANDIDATES_NS
        assert granularity_ns <= 1_000_000_000, (
            "this repo's own test/CI filesystems are not FAT/HFS+-grade "
            "coarse; a value this large signals a probe bug"
        )

    # frob:tests src/frob/graph/__init__.py::_probe_mtime_granularity_ns
    def test_all_samples_colliding_falls_back_to_loop_span(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-4279 obligation [2]'s conservative-lower-bound path: if every
        write in the probe loop reports the identical timestamp (the
        worst real-world case: a mount coarser than the whole loop's own
        wall-clock span), the function must not silently report a tiny
        granularity -- it derives one from the loop's own elapsed time
        instead, still rounded up to a real candidate bucket."""
        frozen_ns = 1_700_000_000_000_000_000

        class _FrozenStat:
            st_mtime_ns = frozen_ns

        real_write_bytes = Path.write_bytes

        def _write_then_freeze(self, data):  # noqa: ANN001, ANN202
            return real_write_bytes(self, data)

        monkeypatch.setattr(Path, "write_bytes", _write_then_freeze)
        monkeypatch.setattr(Path, "stat", lambda self: _FrozenStat())  # noqa: ARG005

        granularity_ns = graph_module._probe_mtime_granularity_ns(tmp_path)
        # every timestamp identical -> loop_elapsed_ns (a small real
        # duration) is the measured gap, rounded up to a real bucket;
        # never None on a fast local filesystem's own loop timing.
        assert granularity_ns is not None
        assert granularity_ns in graph_module._MTIME_GRANULARITY_CANDIDATES_NS

    # frob:tests src/frob/graph/__init__.py::_probe_mtime_granularity_ns
    def test_unwritable_root_returns_none(self, tmp_path: Path) -> None:
        """`.frob/` cannot be created under a read-only root -- degrades to
        `None`, never raises."""
        import sys

        import pytest

        if sys.platform == "win32":
            pytest.skip("chmod-based read-only simulation is POSIX-specific")
        readonly_root = tmp_path / "readonly"
        readonly_root.mkdir()
        readonly_root.chmod(0o555)
        try:
            assert graph_module._probe_mtime_granularity_ns(readonly_root) is None
        finally:
            readonly_root.chmod(0o755)


class TestMtimeGranularityCaching:
    """`_mtime_granularity_ns` (T-4279): measure once, cache both
    in-process and on disk under `<root>/.frob/`."""

    # frob:tests src/frob/graph/__init__.py::_mtime_granularity_ns
    def test_second_call_does_not_reprobe(self, tmp_path: Path, monkeypatch) -> None:
        graph_module._mtime_granularity_cache.clear()
        calls = {"n": 0}
        real_probe = graph_module._probe_mtime_granularity_ns

        def _counting_probe(root):  # noqa: ANN001, ANN202
            calls["n"] += 1
            return real_probe(root)

        monkeypatch.setattr(graph_module, "_probe_mtime_granularity_ns", _counting_probe)

        first = graph_module._mtime_granularity_ns(tmp_path)
        second = graph_module._mtime_granularity_ns(tmp_path)
        assert first == second
        assert calls["n"] == 1, "the second call must hit the in-process cache"

    # frob:tests src/frob/graph/__init__.py::_mtime_granularity_ns
    def test_on_disk_cache_survives_a_fresh_in_process_cache(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Simulates a fresh process (empty in-process cache) reading back
        a previous process's on-disk sidecar file, never re-probing."""
        graph_module._mtime_granularity_cache.clear()
        first = graph_module._mtime_granularity_ns(tmp_path)
        assert first is not None

        graph_module._mtime_granularity_cache.clear()  # simulate a new process

        def _fail_if_called(root):  # noqa: ANN001, ANN202, ARG001
            raise AssertionError("must not re-probe: the on-disk cache is fresh")

        monkeypatch.setattr(graph_module, "_probe_mtime_granularity_ns", _fail_if_called)
        second = graph_module._mtime_granularity_ns(tmp_path)
        assert second == first

    # frob:tests src/frob/graph/__init__.py::_mtime_granularity_ns
    def test_unmeasurable_result_is_not_persisted_to_disk(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A transient probe failure (`None`) must not be written to the
        on-disk sidecar -- that would permanently pin every future
        invocation to "never trust the fast path" even after the
        underlying cause (e.g. a momentarily read-only root) clears."""
        graph_module._mtime_granularity_cache.clear()
        monkeypatch.setattr(
            graph_module, "_probe_mtime_granularity_ns", lambda root: None  # noqa: ARG005
        )
        result = graph_module._mtime_granularity_ns(tmp_path)
        assert result is None
        cache_file = (
            tmp_path.resolve()
            / ".frob"
            / graph_module._MTIME_GRANULARITY_CACHE_FILENAME
        )
        assert not cache_file.exists()


class TestStatTrustMarginAndTrustworthy:
    """`_stat_trust_margin_ns`/`_stat_trustworthy` (T-4279): the margin is
    derived from measured granularity, and an unmeasurable granularity
    must refuse to trust a stat match at all -- the safe default,
    obligation [2]."""

    # frob:tests src/frob/graph/__init__.py::_stat_trust_margin_ns
    def test_margin_is_granularity_times_safety_multiplier(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            graph_module, "_mtime_granularity_ns", lambda root: 1_000_000  # noqa: ARG005
        )
        margin = graph_module._stat_trust_margin_ns(tmp_path)
        assert margin == 1_000_000 * graph_module._STAT_TRUST_SAFETY_MULTIPLIER

    # frob:tests src/frob/graph/__init__.py::_stat_trust_margin_ns
    def test_margin_is_none_when_granularity_unmeasurable(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            graph_module, "_mtime_granularity_ns", lambda root: None  # noqa: ARG005
        )
        assert graph_module._stat_trust_margin_ns(tmp_path) is None

    # frob:tests src/frob/graph/__init__.py::_stat_trustworthy
    def test_none_margin_never_trusts_regardless_of_age(self) -> None:
        """T-4279 obligation [2]: granularity unmeasurable -> always fall
        through to the content hash, no matter how old the stat entry
        looks -- there is no measurement to trust it against."""
        ancient_mtime_ns = 0  # the Unix epoch: about as "old" as it gets
        assert graph_module._stat_trustworthy(ancient_mtime_ns, None) is False

    # frob:tests src/frob/graph/__init__.py::_stat_trustworthy
    def test_stat_within_margin_is_not_trusted(self) -> None:
        now_ns = time.time_ns()
        margin_ns = 250_000_000
        assert graph_module._stat_trustworthy(now_ns, margin_ns) is False

    # frob:tests src/frob/graph/__init__.py::_stat_trustworthy
    def test_stat_past_margin_is_trusted(self) -> None:
        margin_ns = 250_000_000
        old_mtime_ns = time.time_ns() - margin_ns - 1_000_000_000
        assert graph_module._stat_trustworthy(old_mtime_ns, margin_ns) is True

    # frob:tests src/frob/graph/__init__.py::_stat_trustworthy
    def test_coarse_granularity_widens_the_untrusted_window(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-4279 obligation [1], the acceptance criterion this whole
        ticket is about: on a filesystem whose granularity is coarser
        than the OLD fixed 250ms margin (a simulated 2-second-granularity
        mount, matching the ticket's own "older removable formats"
        example), a stat pair recorded 1 second ago -- outside the old
        fixed margin, but comfortably inside a granularity-derived one --
        must NOT be trusted. The old fixed-250ms behavior would have
        wrongly trusted it and returned a stale verdict."""
        monkeypatch.setattr(
            graph_module, "_mtime_granularity_ns", lambda root: 2_000_000_000  # noqa: ARG005
        )
        margin_ns = graph_module._stat_trust_margin_ns(tmp_path)
        one_second_ago_ns = time.time_ns() - 1_000_000_000
        assert graph_module._stat_trustworthy(one_second_ago_ns, margin_ns) is False
