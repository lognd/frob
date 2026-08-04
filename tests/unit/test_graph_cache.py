"""Tests for `frob.graph.cache`'s persistent parse-artifact table (T-1464)."""

from __future__ import annotations

from pathlib import Path

from frob.graph import cache as graph_cache


# frob:ticket T-1464
class TestParsedArtifacts:
    """`store_parsed_artifact`/`load_parsed_artifact` round-trip and miss."""

    def test_store_then_load_round_trips(self, tmp_path: Path) -> None:
        """A stored payload comes back byte-identical for the same key."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.store_parsed_artifact(
            conn,
            content_hash="deadbeef",
            fingerprint="frob==0.0.0",
            payload='{"path": "a.py"}',
        )
        loaded = graph_cache.load_parsed_artifact(
            conn, content_hash="deadbeef", fingerprint="frob==0.0.0"
        )
        assert loaded == '{"path": "a.py"}'

    def test_load_miss_returns_none(self, tmp_path: Path) -> None:
        """An unknown `(content_hash, fingerprint)` pair is a clean miss."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        loaded = graph_cache.load_parsed_artifact(
            conn, content_hash="nope", fingerprint="frob==0.0.0"
        )
        assert loaded is None

    def test_different_fingerprint_is_a_separate_key(self, tmp_path: Path) -> None:
        """The same content hash under a different fingerprint misses --
        the cache key must cover the parser/native version, not just
        content (T-1454's binding lesson)."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.store_parsed_artifact(
            conn,
            content_hash="deadbeef",
            fingerprint="frob==0.0.0",
            payload='{"path": "a.py"}',
        )
        loaded = graph_cache.load_parsed_artifact(
            conn, content_hash="deadbeef", fingerprint="frob==0.0.1"
        )
        assert loaded is None

    def test_store_overwrites_existing_payload(self, tmp_path: Path) -> None:
        """A second store under the same key replaces the payload
        (ON CONFLICT DO UPDATE), not a duplicate row."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.store_parsed_artifact(
            conn, content_hash="h", fingerprint="f", payload="one"
        )
        graph_cache.store_parsed_artifact(
            conn, content_hash="h", fingerprint="f", payload="two"
        )
        loaded = graph_cache.load_parsed_artifact(
            conn, content_hash="h", fingerprint="f"
        )
        assert loaded == "two"
