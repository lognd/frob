"""Unit tests for frob.dup._cache's content-addressed + LRU cache (docs/dup.md)."""

from __future__ import annotations

from pathlib import Path

from frob.dup import _cache


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
        # Regression for the fixed primary-key bug (docs/dup.md's
        # Implementation notes): a digest with more than one cached rung
        # must keep both, not silently drop all but the last write.
        _cache.put_fingerprint(tmp_path, "digestB", "r3", ("hash-value",))
        _cache.put_fingerprint(tmp_path, "digestB", "r4fp", (1, 2, 3))
        assert _cache.get_fingerprint(tmp_path, "digestB", "r3") == ["hash-value"]
        assert _cache.get_fingerprint(tmp_path, "digestB", "r4fp") == [1, 2, 3]


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
