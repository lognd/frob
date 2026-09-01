"""Tests for `frob.graph.cache`'s persistent parse-artifact table (T-1464)."""

from __future__ import annotations

import subprocess
import sys
import time
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


# frob:ticket T-3607
_SIBLING_READER_SCRIPT = """
import sqlite3
import sys
import time
from pathlib import Path

from frob.graph import cache as graph_cache

path = Path(sys.argv[1])
deadline = time.monotonic() + float(sys.argv[2])
conn = graph_cache.connect_readonly(path)
while time.monotonic() < deadline:
    try:
        graph_cache.load_parsed_artifact(conn, content_hash="h", fingerprint="f")
    except (graph_cache.CacheLocked, sqlite3.OperationalError):
        # A benign race with a concurrent _recreate mid-swap (schema not
        # applied yet, or the file momentarily missing) -- exactly what
        # production already treats as a plain cache miss
        # (_load_cached_artifact_payload); reopen and keep reading. The
        # ONLY failure this test cares about is the process dying from a
        # fatal SIGNAL (SIGBUS/SIGSEGV), never a caught Python exception.
        try:
            conn = graph_cache.connect_readonly(path)
        except sqlite3.OperationalError:
            pass
    time.sleep(0.001)
"""


# frob:ticket T-3607
class TestRecreateConcurrentReaderSurvives:
    """Positive control for the T-3607 SIGBUS incident: a sibling PROCESS
    with an already-open, long-lived WAL reader connection must survive
    `_recreate` running concurrently in a different process against the
    SAME cache path -- the exact shape production hit (a `ProcessPool
    Executor` worker's process-lifetime `_artifact_cache_connection`
    crashed on a plain `SELECT` while a sibling worker's `connect()`
    concurrently unlinked-and-recreated the db/`-wal`/`-shm` files this
    reader had memory-mapped). Before T-3607's rename-based quarantine
    swap, this test reliably killed the sibling process with a fatal
    signal (SIGBUS/SIGSEGV, a negative `returncode`) under enough
    iterations; after the fix the sibling always exits 0 -- rename never
    invalidates another process's already-open fd/mmap the way an
    in-place unlink-then-recreate-at-the-same-path can."""

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_sibling\
    # _reader_survives_concurrent_recreate
    def test_sibling_reader_survives_concurrent_recreate(self, tmp_path: Path) -> None:
        """A real sibling process reading in a tight loop never dies from
        a signal while this process repeatedly `_recreate`s the same
        cache path underneath it (T-3607)."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache.store_parsed_artifact(
            conn, content_hash="h", fingerprint="f", payload="one"
        )

        reader = subprocess.Popen(
            [sys.executable, "-c", _SIBLING_READER_SCRIPT, str(path), "2.0"],
        )
        try:
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                conn = graph_cache._recreate(graph_cache._open(path), path)
                graph_cache._apply_schema(conn, None, path)
                graph_cache.store_parsed_artifact(
                    conn, content_hash="h", fingerprint="f", payload="one"
                )
        finally:
            reader.wait(timeout=30)

        assert reader.returncode == 0, (
            f"sibling reader died with returncode={reader.returncode} "
            "(a negative value is a fatal signal, e.g. -7 = SIGBUS) -- "
            "the T-3607 concurrent-recreate-vs-live-reader race reproduced"
        )

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_quarant\
    # ined_sidecars_are_renamed_not_unlinked
    def test_quarantined_sidecars_are_renamed_not_unlinked(
        self, tmp_path: Path
    ) -> None:
        """`_recreate` renames the old db/`-wal`/`-shm` aside (a quarantined
        sibling file survives immediately after) instead of unlinking them
        in place -- the mechanism that makes the concurrent-reader test
        above safe."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache._recreate(conn, path)

        quarantined = list(tmp_path.glob("cache.db.stale-*"))
        assert quarantined, "expected a quarantined sidecar after _recreate"
        assert path.exists(), "_recreate must still leave a fresh db at path"

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_sweep_r\
    # emoves_only_old_quarantined_sidecars
    def test_sweep_removes_only_old_quarantined_sidecars(self, tmp_path: Path) -> None:
        """`_sweep_stale_quarantined_sidecars` removes a quarantined sidecar
        older than the sweep age, and leaves a fresh one alone."""
        path = tmp_path / "cache.db"
        old = tmp_path / "cache.db.stale-111-aaaaaaaa"
        old.write_bytes(b"x")
        old_time = time.time() - graph_cache._STALE_SWEEP_AGE_SECONDS - 60
        import os

        os.utime(old, (old_time, old_time))

        fresh = tmp_path / "cache.db.stale-222-bbbbbbbb"
        fresh.write_bytes(b"x")

        graph_cache._sweep_stale_quarantined_sidecars(path)

        assert not old.exists()
        assert fresh.exists()
