"""Unit tests for frob.dup._cache's content-addressed + LRU cache (docs/modules/dup.md)."""

from __future__ import annotations

import multiprocessing
import multiprocessing.synchronize
import time
from pathlib import Path

import pytest

from frob.dup import _cache
from frob.process._lock import derived_state_lock


# frob:waive DEAD001 reason="pytest autouse fixture (T-0565): invoked by the test runner for every test in this module without ever appearing as a name/call token anywhere -- the one DEAD001 false-positive class build_reference_graph's sig_tokens+body_tokens broadening cannot see"  # noqa: E501
@pytest.fixture(autouse=True)
def _close_cached_connections():
    """Every dup-cache connection is process-cached by resolved path
    (T-0191); tests use a fresh `tmp_path` each time, so nothing leaks
    across tests, but close explicitly so each test starts from a clean
    connection pool rather than relying on garbage collection."""
    yield
    _cache._close_all()


class TestFingerprintRoundTrip:
    def test_put_then_get_returns_same_payload(self, tmp_path: Path):
        # frob:tests src/frob/dup/_cache.py::get_fingerprint kind="unit"
        # frob:tests src/frob/dup/_cache.py::put_fingerprint kind="unit"
        result = _cache.put_fingerprint(tmp_path, "digestA", "r3", ("abc123",))
        assert result.is_ok, result.err
        assert _cache.get_fingerprint(tmp_path, "digestA", "r3") == ["abc123"]

    def test_get_miss_returns_none(self, tmp_path: Path):
        assert _cache.get_fingerprint(tmp_path, "nope", "r3") is None

    def test_different_rungs_do_not_clobber_each_other(self, tmp_path: Path):
        # Regression for the fixed primary-key bug (docs/modules/dup.md's
        # Implementation notes): a digest with more than one cached rung
        # must keep both, not silently drop all but the last write.
        _cache.put_fingerprint(tmp_path, "digestB", "r3", ("hash-value",))
        _cache.put_fingerprint(tmp_path, "digestB", "r4fp", (1, 2, 3))
        assert _cache.get_fingerprint(tmp_path, "digestB", "r3") == ["hash-value"]
        assert _cache.get_fingerprint(tmp_path, "digestB", "r4fp") == [1, 2, 3]

    # frob:tests src/frob/dup/_cache.py::put_fingerprint kind="unit"
    def test_same_digest_and_rung_overwrites_prior_payload(self, tmp_path: Path):
        # INSERT OR REPLACE cache-hit path: re-putting the same (digest,
        # rung) key must replace the stored payload, not error or duplicate
        # the row.
        first = _cache.put_fingerprint(tmp_path, "digestC", "r3", ("old",))
        assert first.is_ok, first.err
        second = _cache.put_fingerprint(tmp_path, "digestC", "r3", ("new", "payload"))
        assert second.is_ok, second.err
        assert _cache.get_fingerprint(tmp_path, "digestC", "r3") == ["new", "payload"]

    # frob:tests src/frob/dup/_cache.py::put_fingerprint kind="unit"
    def test_connect_error_is_propagated_without_writing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # When `_connect` fails (e.g. a corrupt cache DB), `put_fingerprint`
        # must short-circuit on the Err branch and return it mapped to
        # Unit, rather than dereferencing a connection that doesn't exist.
        from typani import Err

        from frob.dup._models import DupError

        monkeypatch.setattr(_cache, "_connect", lambda root: Err(DupError.CacheCorrupt))
        result = _cache.put_fingerprint(tmp_path, "digestD", "r3", ("x",))
        assert result.is_err
        assert result.err == DupError.CacheCorrupt
        # No connection was ever opened/cached for this root.
        assert _cache._db_path(tmp_path).resolve() not in _cache._conn_cache

    def test_get_fingerprint_connect_error_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/dup/_cache.py::get_fingerprint kind="unit"
        # A failed `_connect` (corrupt cache DB) is a miss, not a raised
        # exception -- `get_fingerprint`'s conn_r.is_err branch.
        from typani import Err

        from frob.dup._models import DupError

        monkeypatch.setattr(_cache, "_connect", lambda root: Err(DupError.CacheCorrupt))
        assert _cache.get_fingerprint(tmp_path, "digestE", "r3") is None


class TestVerdictRoundTrip:
    def test_put_then_get_returns_same_payload(self, tmp_path: Path):
        # frob:tests src/frob/dup/_cache.py::get_verdict kind="unit"
        # frob:tests src/frob/dup/_cache.py::put_verdict kind="unit"
        result = _cache.put_verdict(
            tmp_path, "d1", "d2", "r4", 0, (0.9, ((0, 0), (1, 1))), 200_000
        )
        assert result.is_ok, result.err
        payload = _cache.get_verdict(tmp_path, "d1", "d2", "r4", 0)
        assert payload is not None
        assert payload[0] == 0.9

    def test_lookup_is_order_independent(self, tmp_path: Path):
        # verdicts are keyed by (min(d1,d2), max(d1,d2), ...) -- either
        # argument order must hit the same cached row.
        _cache.put_verdict(tmp_path, "zzz", "aaa", "r4", 0, (0.5, ()), 200_000)
        assert _cache.get_verdict(tmp_path, "aaa", "zzz", "r4", 0) is not None
        assert _cache.get_verdict(tmp_path, "zzz", "aaa", "r4", 0) is not None

    def test_get_miss_returns_none(self, tmp_path: Path):
        assert _cache.get_verdict(tmp_path, "x", "y", "r4", 0) is None

    def test_put_verdict_evicts_lru_rows_beyond_cache_entries(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/dup/_cache.py::put_verdict kind="unit"
        # Drives the count > cache_entries eviction branch: with a cap of
        # 2, a 3rd insert must evict the least-recently-used row.
        _cache.put_verdict(tmp_path, "a1", "a2", "r4", 0, (0.1, ()), 2)
        _cache.put_verdict(tmp_path, "b1", "b2", "r4", 0, (0.2, ()), 2)
        result = _cache.put_verdict(tmp_path, "c1", "c2", "r4", 0, (0.3, ()), 2)
        assert result.is_ok, result.err
        assert _cache.get_verdict(tmp_path, "a1", "a2", "r4", 0) is None
        assert _cache.get_verdict(tmp_path, "b1", "b2", "r4", 0) is not None
        assert _cache.get_verdict(tmp_path, "c1", "c2", "r4", 0) is not None

    def test_put_verdict_connect_error_is_propagated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/dup/_cache.py::put_verdict kind="unit"
        from typani import Err

        from frob.dup._models import DupError

        monkeypatch.setattr(_cache, "_connect", lambda root: Err(DupError.CacheCorrupt))
        result = _cache.put_verdict(tmp_path, "x1", "x2", "r4", 0, (0.1, ()), 200_000)
        assert result.is_err
        assert result.err == DupError.CacheCorrupt


class TestFingerprintInvalidation:
    """T-0517: a `dup.db` written under a different frob/grammar version
    fingerprint must not serve its cached rows to the current process."""

    # frob:tests tests/unit/test_dup_cache.py::TestFingerprintInvalidation.test_stale_fingerprint_row_is_not_served kind="unit"  # noqa: E501
    def test_stale_fingerprint_row_is_not_served(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Seed a poisoned row under a wrong-version fingerprint, bypassing
        # the version check entirely (as a pre-T-0517 db on disk would
        # already have done), then reconnect under the CURRENT fingerprint
        # and prove the poisoned row is gone rather than served.
        monkeypatch.setattr(
            _cache, "_compute_fingerprint", lambda: "wrong-version==0.0.0"
        )
        put_result = _cache.put_fingerprint(
            tmp_path, "poisoned-digest", "r3", ("stale",)
        )
        assert put_result.is_ok, put_result.err
        assert _cache.get_fingerprint(tmp_path, "poisoned-digest", "r3") == ["stale"]

        # Force a fresh connection (a new process would open one from
        # scratch) so `_check_fingerprint` runs against the current,
        # un-monkeypatched fingerprint.
        _cache._close_all()
        monkeypatch.undo()
        assert _cache.get_fingerprint(tmp_path, "poisoned-digest", "r3") is None

    # frob:tests tests/unit/test_dup_cache.py::TestFingerprintInvalidation.test_matching_fingerprint_row_still_served kind="unit"  # noqa: E501
    def test_matching_fingerprint_row_still_served(self, tmp_path: Path) -> None:
        # Same-version reconnect (the normal case) must NOT wipe rows.
        _cache.put_fingerprint(tmp_path, "fresh-digest", "r3", ("current",))
        _cache._close_all()
        assert _cache.get_fingerprint(tmp_path, "fresh-digest", "r3") == ["current"]


class TestConnectionReuse:
    """T-0191: get/put no longer reopen `.frob/dup.db` on every call -- one
    connection is cached per resolved db path for the process's lifetime."""

    def test_repeated_calls_reuse_one_connection(self, tmp_path: Path):
        # frob:tests src/frob/dup/_cache.py::_connect kind="unit"
        _cache.put_fingerprint(tmp_path, "d1", "r3", ("x",))
        _cache.put_fingerprint(tmp_path, "d2", "r3", ("y",))
        conn1 = _cache._connect(tmp_path).danger_ok
        conn2 = _cache._connect(tmp_path).danger_ok
        assert conn1 is conn2

    # frob:ticket T-0565
    def test_close_all_drops_cached_connections(self, tmp_path: Path):
        # T-0565: the `frob:tests` directive binding this test to
        # `_cache._close_all` moved to sit above `_close_all` itself
        # (src/frob/dup/_cache.py) -- the DSL convention binds `Edge.src`
        # to the symbol the comment sits ABOVE, so a directive placed here
        # (above the TEST method) bound backwards, from the test to the
        # source symbol, which `frob.gates._dead_symbols` never treats as
        # "the source symbol is wired" (it only reads `edge.src` for a
        # TESTS/INVARIANT edge).
        _cache.put_fingerprint(tmp_path, "d3", "r3", ("z",))
        before = _cache._connect(tmp_path).danger_ok
        _cache._close_all()
        after = _cache._connect(tmp_path).danger_ok
        assert before is not after
        # the underlying file survives -- _close_all only drops the
        # in-process handle, not the data.
        assert _cache.get_fingerprint(tmp_path, "d3", "r3") == ["z"]


# frob:ticket T-1224
def _simulate_standalone_rebuild_then_write(
    root_str: str,
    compute_seconds: float,
    compute_started: "multiprocessing.synchronize.Event",
    wrote: "multiprocessing.synchronize.Event",
) -> None:
    """Helper process (must be top-level to be picklable by
    `multiprocessing.Process`, mirroring `tests/unit/test_process_lock.py`'s
    `_hold_exclusive_then_signal` precedent): mimics a standalone
    `find_clones` call's shape -- a long read/compute phase (no lock held)
    followed by one real cache write (`put_fingerprint`, which DOES take a
    real cross-process EXCLUSIVE `derived_state_write_lock` internally,
    T-1224). Signals `compute_started` right before the sleep so the parent
    can probe for an exclusive hold DURING the compute phase, and `wrote`
    once the write has completed."""
    compute_started.set()
    time.sleep(compute_seconds)
    _cache.put_fingerprint(Path(root_str), "digest-standalone", "r3", ("v",))
    wrote.set()


class TestWriteLockGranularity:
    """T-1224: `derived_state_write_lock` is now taken individually inside
    `put_fingerprint`/`put_verdict`, around just the write, rather than
    around `find_clones`'s entire rung ladder. Before this fix, a
    standalone rebuild held a real cross-process EXCLUSIVE lock for its
    WHOLE computation, stalling any concurrent SHARED reader (e.g. a
    sibling agent's `frob check`) for that whole duration (observed ~240s
    under profiling with four concurrent agents). This test proves a
    concurrent SHARED reader is NOT blocked during the standalone
    rebuild's compute phase -- only (briefly) during its actual write."""

    def test_shared_reader_not_blocked_during_standalone_compute_phase(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_dup_cache.py::TestWriteLockGranularity.test_shared_reader_not_blocked_during_standalone_compute_phase  # noqa: E501
        # frob:ticket T-1386
        ctx = multiprocessing.get_context("spawn")
        compute_started = ctx.Event()
        wrote = ctx.Event()
        compute_seconds = 2.0
        proc = ctx.Process(
            target=_simulate_standalone_rebuild_then_write,
            args=(str(tmp_path), compute_seconds, compute_started, wrote),
        )
        proc.start()
        try:
            assert compute_started.wait(timeout=10), (
                "helper process never signaled it started its compute phase"
            )
            # The helper is now mid-"compute" (sleeping, no lock held under
            # T-1224's granular locking). A concurrent SHARED reader must be
            # able to acquire `derived_state_lock` promptly here -- assert
            # the CAUSAL claim (the acquire happens before the helper's
            # write completes) rather than a wall-clock bound: a duration
            # threshold flakes under load (T-1386, observed 1.26s against a
            # 1.0s bound on a busy box) even though the granularity fix
            # itself is sound. If the acquire instead blocks until AFTER
            # `wrote` fires, `derived_state_write_lock` has regressed to
            # wrapping the whole rebuild again (the pre-T-1224 behavior
            # this ticket fixes), not just the write.
            with derived_state_lock(tmp_path, exclusive=False):
                acquired_before_write = not wrote.is_set()
            assert acquired_before_write, (
                "shared reader did not acquire until AFTER the helper's "
                "write completed -- the exclusive write lock appears to be "
                "held for the whole computation again, not just the write "
                "(T-1224 regression)"
            )
            assert wrote.wait(timeout=10), "helper process never completed its write"
        finally:
            proc.join(timeout=10)
        assert _cache.get_fingerprint(tmp_path, "digest-standalone", "r3") == ["v"]
