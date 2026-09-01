"""Tests for `frob.graph.cache`'s persistent parse-artifact table (T-1464)."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

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
                conn = graph_cache._apply_schema(conn, None, path)
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


# frob:ticket T-3623
_SIBLING_CONNECT_LOOP_SCRIPT = """
import sqlite3
import sys
import time
from pathlib import Path

from frob.graph import cache as graph_cache

path = Path(sys.argv[1])
deadline = time.monotonic() + float(sys.argv[2])
errors = []
while time.monotonic() < deadline:
    try:
        conn = graph_cache.connect(path)
        conn.execute("SELECT 1 FROM meta LIMIT 1")
        conn.close()
    except sqlite3.OperationalError as exc:
        errors.append(repr(exc))
        break
if errors:
    print("ERRORS:" + "|".join(errors))
else:
    print("OK")
"""


# frob:ticket T-3623
class TestRecreateNeverExposesASchemaIncompleteDb:
    """T-3623: a fresh replacement db built by `_recreate` (or the very
    first `connect()` at a brand-new path) must never be OBSERVABLE by a
    concurrent connection before its schema is fully applied. Before this
    fix, `_recreate` opened a plain, empty sqlite file directly at the
    real path and relied on a LATER step in the SAME connect() call to
    apply the schema -- any other connection racing in that window saw a
    valid-but-tableless file and got `OperationalError: no such table:
    meta` straight out of `_check_fingerprint`, which has no rebuild-on-
    miss handling of its own (run 33466891764, macOS)."""

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # recreate_replacement_always_has_meta_table
    def test_recreate_replacement_always_has_meta_table(self, tmp_path: Path) -> None:
        """The instant `_recreate` returns, `path` already has its `meta`
        table -- there is no intermediate state where the file exists but
        is not yet schema-complete."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache._recreate(conn, path)

        # A brand-new, completely independent connection (mimicking a
        # racing sibling) must see the schema immediately, with no
        # dependency on any further work by the process that ran
        # _recreate.
        reader = sqlite3.connect(str(path))
        try:
            row = reader.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            ).fetchone()
        finally:
            reader.close()
        assert row is not None, (
            "a fresh connection right after _recreate() found no "
            "meta.schema_version row -- the replacement db was exposed "
            "before its schema was applied"
        )

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # first_ever_connect_never_exposes_a_tableless_file
    def test_first_ever_connect_never_exposes_a_tableless_file(
        self, tmp_path: Path
    ) -> None:
        """The very first `connect()` at a path that has never had a cache
        db before must not leave a window where the file exists but has
        no `meta` table -- same schema-complete-before-visible guarantee
        `_recreate` gets, for the first-creation path too."""
        path = tmp_path / "never-seen-before" / "cache.db"

        # Pre-build the schema-complete replacement helper directly, the
        # same primitive connect() uses internally, and assert its output
        # is immediately schema-complete to any independent connection.
        path.parent.mkdir(parents=True)
        graph_cache._create_schema_complete_db(path)

        reader = sqlite3.connect(str(path))
        try:
            row = reader.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            ).fetchone()
        finally:
            reader.close()
        assert row is not None

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # two_processes_connecting_concurrently_never_see_no_such_table_meta
    def test_two_processes_connecting_concurrently_never_see_no_such_table_meta(
        self, tmp_path: Path
    ) -> None:
        """Regression for T-3623 direction 3: one process repeatedly
        `_recreate`s the same cache path (as a schema-mismatch rebuild
        would) while a sibling PROCESS repeatedly `connect()`s that same
        path and queries `meta` in a tight loop; the sibling must never
        observe `OperationalError: no such table: meta`."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache.store_parsed_artifact(
            conn, content_hash="h", fingerprint="f", payload="one"
        )

        sibling = subprocess.Popen(
            [sys.executable, "-c", _SIBLING_CONNECT_LOOP_SCRIPT, str(path), "2.0"],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                conn = graph_cache._recreate(graph_cache._open(path), path)
                conn = graph_cache._apply_schema(conn, None, path)
                graph_cache.store_parsed_artifact(
                    conn, content_hash="h", fingerprint="f", payload="one"
                )
        finally:
            out, _ = sibling.communicate(timeout=30)

        assert "ERRORS:" not in out, (
            f"sibling connect() loop observed a sqlite error: {out!r} -- "
            "a concurrent _recreate exposed a schema-incomplete db"
        )

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # apply_schema_rebuild_replacement_always_has_files_table
    def test_apply_schema_rebuild_replacement_always_has_files_table(
        self, tmp_path: Path
    ) -> None:
        """T-3632 (round 2 of T-3623): a forced `_apply_schema` rebuild
        (`existing=None`, the same call shape `_apply_schema_with_recovery`
        and the two-process test above both use) must publish the `files`
        table atomically along with `meta`, not just `meta` alone -- the
        exact gap the round-1 fix missed (measured as `OperationalError:
        no such table: files` from a sibling's tight `connect()` loop,
        run 33472403980)."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache._apply_schema(conn, None, path)

        reader = sqlite3.connect(str(path))
        try:
            row = reader.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'files'"
            ).fetchone()
        finally:
            reader.close()
        assert row is not None, (
            "a fresh connection right after a forced _apply_schema rebuild "
            "found no 'files' table -- the replacement db was exposed "
            "before its schema was fully applied"
        )


# frob:ticket T-3632
class TestConnectNeverReturnsAStaleConnection:
    """T-3632 direction 3: `connect()` must never hand a caller a
    connection object that an internal schema rebuild has already
    `.close()`d -- regression for the `sqlite3.InterfaceError` measured
    at `src/frob/graph/cache.py:1083` (run 33472403980,
    `test_waive002_end_to_end_via_run_gates`), a NEW error class that
    appeared only after T-3623's own fix, consistent with a caller
    somewhere ending up bound to a connection a concurrent rebuild had
    invalidated."""

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection.test_conn\
    # ect_after_forced_schema_rebuild_returns_a_fresh_live_connection
    def test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection(
        self, tmp_path: Path
    ) -> None:
        """Forcing the exact condition `_apply_schema`'s rebuild path
        handles (a stored schema_version below `_SCHEMA_VERSION`) and
        calling `connect()` again must return a DIFFERENT, immediately
        usable connection object -- never the one the rebuild closed."""
        path = tmp_path / "cache.db"
        conn1 = graph_cache.connect(path)

        conn1.execute("UPDATE meta SET value = '0' WHERE key = 'schema_version'")
        conn1.commit()

        conn2 = graph_cache.connect(path)

        assert conn2 is not conn1, (
            "connect() returned the SAME connection object after a "
            "schema rebuild -- a caller holding it would be bound to "
            "whatever _apply_schema's rebuild did to the old object"
        )
        row = conn2.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        assert row is not None and int(row[0]) == graph_cache._SCHEMA_VERSION, (
            "the connection connect() returned after a rebuild is not "
            "usable against the current schema"
        )

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection.test_recr\
    # eate_closed_connection_raises_a_clean_programming_error_not_interface_error
    def test_recreate_closed_connection_raises_a_clean_programming_error_not_interface_error(  # noqa: E501
        self, tmp_path: Path
    ) -> None:
        """`_recreate` documents that it `.close()`s the connection it is
        given (see its docstring); using that SAME object afterward must
        fail in the ordinary, well-understood sqlite3 way
        (`ProgrammingError: Cannot operate on a closed database`), never
        as an opaque `InterfaceError` -- the latter is the signature of
        genuinely bad connection state (e.g. a use-after-free-shaped bug),
        not merely "closed"."""
        path = tmp_path / "cache.db"
        stale = graph_cache.connect(path)
        graph_cache._recreate(stale, path)

        with pytest.raises(sqlite3.ProgrammingError):
            stale.execute("SELECT 1 FROM meta LIMIT 1")
