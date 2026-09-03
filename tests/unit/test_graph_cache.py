"""Tests for `frob.graph.cache`'s persistent parse-artifact table (T-1464)."""

from __future__ import annotations

import os
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
# frob:ticket T-3700
# T-3700: the meta read is issued through the cache API (`get_root`, which
# routes through `_run_with_stale_reconnect`), NOT a bare `conn.execute`.
# A raw execute on a connection a sibling's `os.replace` stranded on the
# pre-rebuild inode is fundamentally undefendable (sqlite resolves a hot
# rollback journal by PATH against the replaced-in inode and raises
# `disk I/O error` / `no such table: meta` before the module ever sees it);
# the invariant this pins is the production one -- a caller reading through
# the cache's own API never surfaces a raw sqlite error of these shapes,
# it reopens-and-retries or raises a typed `CacheLocked`. `iters` counts
# successful connect+read round trips so the harness can assert real work
# happened rather than an empty loop trivially "passing".
_SIBLING_CONNECT_LOOP_SCRIPT = """
import sqlite3
import sys
import time
from pathlib import Path

from frob.graph import cache as graph_cache

path = Path(sys.argv[1])
deadline = time.monotonic() + float(sys.argv[2])
errors = []
iters = 0
while time.monotonic() < deadline:
    try:
        conn = graph_cache.connect(path)
        graph_cache.get_root(conn)
        conn.close()
        iters += 1
    except graph_cache.CacheLocked:
        # A clean, typed contention error is an ACCEPTED outcome under
        # sustained load -- it is exactly what the bounded retry raises
        # once its budget is exhausted, never a raw sqlite escape.
        iters += 1
    except sqlite3.DatabaseError as exc:
        # T-3706: was `except sqlite3.OperationalError`, which does NOT
        # catch sqlite's "file is not a database" torn-read shape --
        # sqlite raises that as a bare DatabaseError, the PARENT class,
        # not an OperationalError subclass. The narrower catch let that
        # shape crash this child process silently (stdout just stops,
        # no OK:/ERRORS: line, no captured traceback -- run 33680767948,
        # macOS). Catching DatabaseError here means any future escape of
        # this kind reports as an assertable ERRORS: line instead of a
        # bare "sibling did not print an OK: result line" AssertionError
        # with no diagnostic content.
        errors.append(repr(exc))
        break
if errors:
    print("ERRORS:" + "|".join(errors))
else:
    print("OK:" + str(iters))
"""


# frob:ticket T-3623
# frob:ticket T-3700
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

    # frob:ticket T-3700
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # two_processes_connecting_concurrently_never_see_no_such_table_meta
    # reason: two-process sqlite recreate/connect race sized to a wall-clock
    # window (3.0s); underlying bug fixed through 9 rounds (T-3623/T-3700),
    # residual failure is timing starvation under xdist CI load, not a
    # deterministic defect.
    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_two_processes_connecting_concurrently_never_see_no_such_table_meta(
        self, tmp_path: Path
    ) -> None:
        """Regression for T-3623 direction 3 (T-3700 round 7 hardening):
        one process repeatedly `_recreate`s AND force-`_apply_schema`s the
        same cache path (two atomic `os.replace`s per iteration, as a
        schema-mismatch rebuild would) while a sibling PROCESS repeatedly
        `connect()`s that same path and reads `meta` through the cache API
        in a tight loop; the sibling must never surface a raw
        `OperationalError` of the `no such table: meta` or `disk I/O error`
        shape.

        T-3700: run 33633092156 (ubuntu, under heavy parallel CI load)
        still saw both shapes escape here even after rounds 1-6. The
        remaining windows were the one-shot (unguarded) final
        `_check_fingerprint` in `_check_fingerprint_with_recovery` and the
        post-connect `meta` read (`get_root`) issued as a raw
        `conn.execute` outside the stale-reconnect wrapper. To reproduce
        the load-timing race more reliably off CI this runs MORE sibling
        churn (spawns TWO concurrent recreating processes are not needed --
        the single-process double-replace per iteration already publishes
        a fresh inode faster than the sibling can connect) and asserts the
        sibling completed real round trips, so a silently empty loop cannot
        pass vacuously."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache.store_parsed_artifact(
            conn, content_hash="h", fingerprint="f", payload="one"
        )

        duration = 3.0
        sibling = subprocess.Popen(
            [
                sys.executable,
                "-c",
                _SIBLING_CONNECT_LOOP_SCRIPT,
                str(path),
                str(duration),
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                conn = graph_cache._recreate(graph_cache._open(path), path)
                conn = graph_cache._apply_schema(conn, None, path)
                graph_cache.store_parsed_artifact(
                    conn, content_hash="h", fingerprint="f", payload="one"
                )
        finally:
            out, _ = sibling.communicate(timeout=30)

        assert "ERRORS:" not in out, (
            f"sibling connect()+get_root() loop surfaced a raw sqlite error: "
            f"{out!r} -- a concurrent _recreate exposed a schema-incomplete "
            "db or stranded the sibling's handle (T-3700)"
        )
        # The sibling routes its logging to stdout too (fingerprint-
        # invalidation INFO lines under this churn), so scan for the
        # single result marker line rather than assuming it is the whole
        # of stdout.
        ok_lines = [line for line in out.splitlines() if line.startswith("OK:")]
        assert ok_lines, f"sibling did not print an OK: result line: {out!r}"
        assert int(ok_lines[-1].split(":", 1)[1].strip()) > 0, (
            f"sibling loop completed zero connect+read round trips ({out!r}) "
            "-- the race harness did no real work, so a green result is vacuous"
        )

    # frob:ticket T-3706
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # run_with_stale_reconnect_recovers_from_bare_database_error
    def test_run_with_stale_reconnect_recovers_from_bare_database_error(
        self, tmp_path: Path
    ) -> None:
        """T-3706 (round 8, macOS run 33680767948): sqlite raises the
        "file is not a database" torn-read shape as a bare
        `sqlite3.DatabaseError` -- the PARENT exception class, not a
        subclass of `OperationalError` -- confirmed directly here rather
        than assumed. `_run_with_stale_reconnect` used to catch only
        `OperationalError`, so this shape escaped its retry loop uncaught
        even though `_is_stale_or_corrupt_connection` already matched the
        message (T-3634). This deterministically forces the shape (no
        timing dependency, unlike the two-process test above) and asserts
        the retry loop recovers instead of propagating."""
        assert not issubclass(sqlite3.DatabaseError, sqlite3.OperationalError), (
            "sqlite3.DatabaseError became a subclass of OperationalError -- "
            "this test's premise (why the narrower catch missed it) no "
            "longer holds; re-check whether the widened catch is still needed"
        )
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)

        calls = {"n": 0}

        def op(_conn: sqlite3.Connection) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.DatabaseError("file is not a database")
            return "recovered"

        result = graph_cache._run_with_stale_reconnect(conn, op, what="test op")
        assert result == "recovered"
        assert calls["n"] == 2, (
            "op should have been retried exactly once after the bare DatabaseError"
        )

    # frob:ticket T-3706
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # check_fingerprint_with_recovery_recovers_from_bare_database_error
    def test_check_fingerprint_with_recovery_recovers_from_bare_database_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3706: same widened-catch fix, for the fingerprint recovery
        loop specifically (`_check_fingerprint_with_recovery` /
        `_recover_fingerprint_connection`) -- the second escape point
        T-3700 hardened but still typed too narrowly."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)

        calls = {"n": 0}
        real_check_fingerprint = graph_cache._check_fingerprint

        def flaky_check_fingerprint(c: sqlite3.Connection, p: Path) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.DatabaseError("file is not a database")
            real_check_fingerprint(c, p)

        monkeypatch.setattr(graph_cache, "_check_fingerprint", flaky_check_fingerprint)

        result = graph_cache._check_fingerprint_with_recovery(conn, path)
        assert isinstance(result, sqlite3.Connection)
        assert calls["n"] == 2, (
            "_check_fingerprint should have been retried exactly once "
            "after the bare DatabaseError"
        )

    # frob:ticket T-3733
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # run_with_stale_reconnect_recovers_from_interface_error
    def test_run_with_stale_reconnect_recovers_from_interface_error(
        self, tmp_path: Path
    ) -> None:
        """T-3733 (round 9, macOS CI run 33729699769): a stale/closed
        sqlite connection raises `sqlite3.InterfaceError('bad parameter
        or other API misuse')` -- confirmed directly here rather than
        assumed to be a SIBLING of `sqlite3.DatabaseError` under
        `sqlite3.Error`, not a subclass of it. `_run_with_stale_reconnect`
        used to catch only `DatabaseError` (T-3706), so this shape still
        escaped its retry loop uncaught. This deterministically forces the
        shape (no timing dependency) and asserts the retry loop recovers
        instead of propagating."""
        assert not issubclass(sqlite3.InterfaceError, sqlite3.DatabaseError), (
            "sqlite3.InterfaceError became a subclass of DatabaseError -- "
            "this test's premise (why the T-3706 widened catch still "
            "missed it) no longer holds; re-check whether the sqlite3.Error "
            "widening is still needed"
        )
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)

        calls = {"n": 0}

        def op(_conn: sqlite3.Connection) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.InterfaceError("bad parameter or other API misuse")
            return "recovered"

        result = graph_cache._run_with_stale_reconnect(conn, op, what="test op")
        assert result == "recovered"
        assert calls["n"] == 2, (
            "op should have been retried exactly once after the bare InterfaceError"
        )

    # frob:ticket T-3733
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # check_fingerprint_with_recovery_recovers_from_interface_error
    def test_check_fingerprint_with_recovery_recovers_from_interface_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3733: same widened-catch fix, for the fingerprint recovery
        loop specifically (`_check_fingerprint_with_recovery` /
        `_recover_fingerprint_connection`) -- the second escape point
        that still typed too narrowly (`DatabaseError`) to reach an
        `InterfaceError` raised by a stale/closed handle."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)

        calls = {"n": 0}
        real_check_fingerprint = graph_cache._check_fingerprint

        def flaky_check_fingerprint(c: sqlite3.Connection, p: Path) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.InterfaceError("bad parameter or other API misuse")
            real_check_fingerprint(c, p)

        monkeypatch.setattr(graph_cache, "_check_fingerprint", flaky_check_fingerprint)

        result = graph_cache._check_fingerprint_with_recovery(conn, path)
        assert isinstance(result, sqlite3.Connection)
        assert calls["n"] == 2, (
            "_check_fingerprint should have been retried exactly once "
            "after the bare InterfaceError"
        )

    # frob:ticket T-3733
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_\
    # is_stale_or_corrupt_connection_matches_interface_error_by_type
    def test_is_stale_or_corrupt_connection_matches_interface_error_by_type(
        self,
    ) -> None:
        """T-3733: `InterfaceError`'s message ("bad parameter or other API
        misuse") never appears in `_STALE_CONNECTION_ERROR_SHAPES`, so
        unlike every other shape `_is_stale_or_corrupt_connection` matches
        by substring, this one must be matched by TYPE -- confirm that
        directly, since the message-substring path alone would silently
        keep failing this shape even after the catch-clause widening."""
        exc = sqlite3.InterfaceError("bad parameter or other API misuse")
        assert graph_cache._is_stale_or_corrupt_connection(exc), (
            "InterfaceError must be classified as a stale/corrupt "
            "connection even though its message matches none of "
            "_STALE_CONNECTION_ERROR_SHAPES"
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


# frob:ticket T-3654
class TestLockBackoff:
    """T-3654 (cache round 5): `_lock_backoff_seconds` replaces the prior
    fixed `_LOCK_POLL_SECONDS` sleep between lock-retry attempts with
    exponential backoff, so darwin's slower fs contention (run
    33513484322) gets far more attempts within the same overall
    deadline instead of exhausting a small, evenly-spaced retry count."""

    # frob:tests src/frob/graph/cache.py::_lock_backoff_seconds
    def test_backoff_doubles_up_to_the_cap(self) -> None:
        delays = [
            graph_cache._lock_backoff_seconds(attempt, remaining=100.0)
            for attempt in range(8)
        ]
        assert delays[0] == graph_cache._LOCK_BACKOFF_BASE_SECONDS
        for earlier, later in zip(delays, delays[1:]):
            assert later >= earlier, "backoff must never shrink between attempts"
        assert delays[-1] == graph_cache._LOCK_BACKOFF_CAP_SECONDS, (
            "backoff must saturate at the former fixed poll interval, "
            "not grow unbounded"
        )

    # frob:tests src/frob/graph/cache.py::_lock_backoff_seconds
    def test_backoff_never_exceeds_remaining_budget(self) -> None:
        # a late, large attempt number would normally hit the cap, but a
        # near-exhausted deadline must win -- the final hard error still
        # has to fire promptly, not sleep past it
        delay = graph_cache._lock_backoff_seconds(10, remaining=0.01)
        assert delay <= 0.01

    # frob:tests src/frob/graph/cache.py::_lock_backoff_seconds
    def test_backoff_is_never_negative(self) -> None:
        delay = graph_cache._lock_backoff_seconds(0, remaining=0.0)
        assert delay >= 0.0


def _publish_marked_db(path: Path, marker: str) -> None:
    """Atomically `os.replace` a fresh schema-complete db carrying
    `meta.marker = marker` over `path` -- the exact publish shape a
    sibling's rebuild performs, used to simulate the replace that strands
    an already-open connection on the old inode (T-3669)."""
    tmp = graph_cache._build_schema_complete_db(path)
    writer = sqlite3.connect(str(tmp))
    try:
        writer.execute("INSERT INTO meta (key, value) VALUES ('marker', ?)", (marker,))
        writer.commit()
    finally:
        writer.close()
    os.replace(tmp, path)


# frob:ticket T-3669
class TestHandleIdentity:
    """T-3669 (cache round 6): a `sqlite3.Connection` opened before a
    sibling's `os.replace` stays bound to the OLD inode -- it reads
    pre-replace state indefinitely (the ~20-cycle `fingerprint None`
    rebuild thrash of run 33529632605) and its writes surface as `attempt
    to write a readonly database`, which rounds 1-5 all retried on that
    same doomed handle. The fix is lifecycle, not retry: detect the
    replace and REOPEN at the canonical path."""

    @staticmethod
    def _read_meta(path: Path, key: str) -> str | None:
        """`meta[key]` as an INDEPENDENT connection sees it on disk -- the
        only honest way to assert a write landed in the LIVE file rather
        than in a replaced-away inode (T-3669)."""
        reader = sqlite3.connect(str(path))
        try:
            row = reader.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
        finally:
            reader.close()
        return None if row is None else row[0]

    # frob:tests src/frob/graph/cache.py::_file_identity
    def test_identity_changes_after_os_replace(self, tmp_path: Path) -> None:
        """`_file_identity` must actually distinguish the pre- and
        post-replace files -- the whole detection rests on it."""
        path = tmp_path / "cache.db"
        graph_cache._create_schema_complete_db(path)
        before = graph_cache._file_identity(path)
        _publish_marked_db(path, "after")
        after = graph_cache._file_identity(path)
        assert before is not None and after is not None
        assert before != after, (
            "os.replace published a new file that _file_identity reports as "
            "identical -- a replaced-away handle could never be detected"
        )

    # frob:tests src/frob/graph/cache.py::_reopen_if_replaced
    def test_replaced_away_handle_is_reopened_before_the_next_read(
        self, tmp_path: Path
    ) -> None:
        """A connection whose backing file was replaced is closed and
        reopened at the canonical path, so its next read sees the WINNER's
        db -- not the stale inode it still had open."""
        path = tmp_path / "cache.db"
        graph_cache._create_schema_complete_db(path)
        conn = graph_cache._open(path)
        _publish_marked_db(path, "winner")

        # Sanity: the un-reopened handle is exactly the defect -- it still
        # answers from the replaced-away inode.
        assert (
            conn.execute("SELECT value FROM meta WHERE key = 'marker'").fetchone()
            is None
        )

        fresh = graph_cache._reopen_if_replaced(conn, path)
        try:
            row = fresh.execute(
                "SELECT value FROM meta WHERE key = 'marker'"
            ).fetchone()
        finally:
            fresh.close()
        assert row is not None and row[0] == "winner"

    # frob:tests src/frob/graph/cache.py::_reopen_if_replaced
    def test_live_handle_is_not_reopened(self, tmp_path: Path) -> None:
        """No replace, no reopen: a handle still bound to the file at
        `path` is returned untouched, so this check cannot reintroduce
        T-0232's "a second connection must not queue behind a held write"
        cost on the ordinary, non-racing path."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        try:
            assert graph_cache._reopen_if_replaced(conn, path) is conn
        finally:
            conn.close()

    # frob:tests src/frob/graph/cache.py::_is_readonly_handle_error
    def test_readonly_database_is_classified_as_a_handle_fault(self) -> None:
        """The terminal error of round 5 (`CacheLocked('attempt to write a
        readonly database')`) must be recognised as a handle fault, so it
        reopens instead of being retried on the connection that caused
        it."""
        exc = sqlite3.OperationalError("attempt to write a readonly database")
        assert graph_cache._is_readonly_handle_error(exc)
        assert not graph_cache._is_readonly_handle_error(
            sqlite3.OperationalError("database is locked")
        )

    # frob:tests src/frob/graph/cache.py::_with_lock_retry
    def test_lock_retry_lets_a_readonly_fault_escape_to_the_reopen_layer(
        self,
    ) -> None:
        """With `retry_readonly=False` the readonly shape escapes at once
        rather than burning the 30s budget on a doomed handle -- the
        measured reason T-3654's deadline backoff changed nothing."""
        calls: list[int] = []

        def _op() -> None:
            calls.append(1)
            raise sqlite3.OperationalError("attempt to write a readonly database")

        started = time.monotonic()
        with pytest.raises(sqlite3.OperationalError):
            graph_cache._with_lock_retry(_op, what="probe", retry_readonly=False)
        assert calls == [1], "the readonly fault was retried on the same handle"
        assert time.monotonic() - started < 5.0

    # frob:tests src/frob/graph/cache.py::_check_fingerprint_with_recovery
    def test_fingerprint_read_after_a_replace_lands_on_the_live_file(
        self, tmp_path: Path
    ) -> None:
        """The mutual-rebuild thrash in one assertion: after an external
        replace, the fingerprint check must reopen and write its
        fingerprint into the file that is actually at `path` -- writing it
        into the replaced-away inode is what let both processes keep
        seeing `fingerprint None` and rebuilding over each other."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        _publish_marked_db(path, "winner")

        conn = graph_cache._check_fingerprint_with_recovery(conn, path)
        try:
            assert self._read_meta(path, "marker") == "winner", (
                "the fingerprint check republished over the winner's db"
            )
            reader = sqlite3.connect(str(path))
            try:
                row = reader.execute(
                    "SELECT value FROM meta WHERE key = 'fingerprint'"
                ).fetchone()
            finally:
                reader.close()
        finally:
            conn.close()
        assert row is not None and row[0] == graph_cache._compute_fingerprint(), (
            "the fingerprint was written to a replaced-away inode, so the "
            "next reader still sees None and rebuilds again -- the thrash"
        )

    # frob:tests src/frob/graph/cache.py::store_file_data
    def test_store_file_data_after_a_replace_lands_on_the_live_file(
        self, tmp_path: Path
    ) -> None:
        """The app-path write shape (`ticket_run close` -> `build_graph` ->
        `store_file_data`, the second production surface seen in runs
        33521/33533): a write issued on a connection whose file was
        replaced must reach the LIVE db, not vanish into the old inode or
        die as `CacheLocked('attempt to write a readonly database')`."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        _publish_marked_db(path, "winner")

        graph_cache.store_file_data(
            conn,
            file_path="a.py",
            content_hash="deadbeef",
            symbols=(),
            edges=(),
            malformed=(),
        )
        conn.close()
        assert self._read_meta(path, "marker") == "winner"
        reader = sqlite3.connect(str(path))
        try:
            row = reader.execute(
                "SELECT content_hash FROM files WHERE path = 'a.py'"
            ).fetchone()
        finally:
            reader.close()
        assert row is not None and row[0] == "deadbeef", (
            "store_file_data wrote through a replaced-away handle -- the "
            "row never reached the db that is actually at the cache path"
        )
