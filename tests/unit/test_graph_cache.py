"""Tests for `frob.graph.cache`'s persistent parse-artifact table (T-1464)."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from frob.graph import cache as graph_cache

# frob:ticket T-3781
# frob:ticket T-3820
#: T-3820 re-confirmed all 6 under winrun WITH the production
#: retry-on-PermissionError fix (`cache._replace_with_retry`) in place --
#: every one still fails on Windows, because each keeps a handle open on
#: the destination ACROSS the publish for the whole test: five hold a
#: single reader/`conn` open persistently (`test_connect_after_forced_
#: schema_rebuild`, `test_replaced_away_handle_is_reopened`,
#: `test_fingerprint_read_after_a_replace`, `test_store_file_data_after_a_
#: replace`, `test_sibling_reader_survives_concurrent_recreate`), and the
#: sixth (`test_two_processes_connecting_concurrently_...`) saturates the
#: path with a zero-gap sibling `connect()`/`close()` loop so no retry
#: window ever opens. The bounded retry helps the REALISTIC transient
#: production shape -- a gate worker that opens+closes the db around each
#: access, leaving gaps (proven separately by `TestReplaceWithRetry` on
#: Linux + a minimal winrun repro) -- but NONE of these 6 model that gap,
#: so they remain honestly skipped rather than masked. The production
#: limitation for the persistent-handle case is documented on `cache.py`
#: (search "T-3820 platform invariant") and tracked by ticket T-3820.
#: T-3781: 6 tests below model (single-process, or a real subprocess
#: sibling) another connection surviving an `os.replace` publish while it
#: still has `path` open -- the whole point of this module's rename-not-
#: unlink-in-place design (T-3607's docstring: "a rename does not
#: invalidate any process's already-open fd or active mmap"). That
#: guarantee is POSIX-specific. Confirmed via a minimal reproduction under
#: winrun (T-3781): even a single PLAIN sqlite3 connection with no active
#: transaction, opened by Python's bundled sqlite3 VFS, is enough to make
#: `os.replace` targeting that same path raise `PermissionError: [WinError
#: 5] Access is denied` on Windows -- CreateFile/MoveFileEx there refuse to
#: replace a file with ANY open handle unless that handle was opened with
#: FILE_SHARE_DELETE, which Python's bundled sqlite3 does not request.
#: There is no stdlib-`sqlite3`-level way to request that share flag, so a
#: caller with a stale connection (or a genuine cross-process sibling, as
#: `test_sibling_reader_survives_concurrent_recreate`/`test_two_processes_
#: connecting_concurrently_never_see_no_such_table_meta` construct with a
#: real subprocess) structurally CANNOT be survived by an `os.replace`-
#: based atomic publish on Windows -- not a gap in this module's retry/
#: recovery logic, a platform primitive with no equivalent here.
_WIN32_NO_REPLACE_OVER_OPEN_HANDLE = pytest.mark.skipif(
    sys.platform == "win32",
    reason=(
        "POSIX-only primitive: os.replace() must not invalidate another "
        "already-open handle to the destination path. Windows' "
        "CreateFile/MoveFileEx refuses to replace a file with any open "
        "handle lacking FILE_SHARE_DELETE, which Python's bundled sqlite3 "
        "does not request and cannot be made to via the stdlib API "
        "(confirmed via a minimal winrun reproduction, T-3781; re-confirmed "
        "under winrun WITH cache._replace_with_retry in place, T-3820 -- the "
        "bounded retry fixes the transient gap-between-accesses shape, not a "
        "handle held open across the whole publish, which these 6 all do)."
    ),
)


# frob:ticket T-1464
class TestParsedArtifacts:
    """`store_parsed_artifact`/`load_parsed_artifact` round-trip and miss."""

    # frob:tests src/frob/graph/cache.py::store_parsed_artifact
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

    # frob:tests src/frob/graph/cache.py::load_parsed_artifact
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


# frob:ticket T-4018
# frob:ticket T-4047
def _force_empty_rows_for_column(conn: sqlite3.Connection, column: str) -> None:
    """Make the `fetchone()` of any query selecting only `column` on `conn`
    return `()`, modeling the row_factory-interaction hypothesis for
    T-4018/T-4047's empty-row condition without racing for it. Scoped by
    the query's own column list so it does not also blank unrelated reads
    this module issues internally (e.g. `PRAGMA database_list`)."""

    def factory(cursor: sqlite3.Cursor, row: tuple[object, ...]) -> object:
        columns = [d[0] for d in cursor.description]
        if columns == [column]:
            return ()
        return row

    conn.row_factory = factory


# frob:ticket T-4018
# frob:ticket T-4419
class TestEmptyRowGuard:
    """Asserts the empty-row guard handles `fetchone()` returning `()`
    (present but zero columns) the same as `None`, using a `row_factory`
    to construct the `()` condition directly. See T-4018 for the design
    rationale."""

    # frob:ticket T-4018
    @staticmethod
    def _force_empty_rows(conn: sqlite3.Connection) -> None:
        """Make the `parsed_artifacts.payload` query's `fetchone()` return
        `()` on `conn` (T-4018) -- see `_force_empty_rows_for_column`."""
        _force_empty_rows_for_column(conn, "payload")

    # frob:ticket T-4018
    def test_empty_row_is_a_clean_miss_not_a_crash(self, tmp_path: Path) -> None:
        """`load_parsed_artifact` returns `None`, not `IndexError`, when
        `fetchone()` yields `()` for an otherwise-present row (T-4018)."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.store_parsed_artifact(
            conn, content_hash="deadbeef", fingerprint="frob==0.0.0", payload="x"
        )
        self._force_empty_rows(conn)
        loaded = graph_cache.load_parsed_artifact(
            conn, content_hash="deadbeef", fingerprint="frob==0.0.0"
        )
        assert loaded is None

    # frob:ticket T-4018
    def test_genuine_cached_payload_still_returns_unchanged(
        self, tmp_path: Path
    ) -> None:
        """The truthiness-guard fix does not disturb an ordinary cache hit
        -- only an empty `()` row is treated specially."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.store_parsed_artifact(
            conn,
            content_hash="realkey",
            fingerprint="frob==0.0.0",
            payload="real-payload",
        )
        loaded = graph_cache.load_parsed_artifact(
            conn, content_hash="realkey", fingerprint="frob==0.0.0"
        )
        assert loaded == "real-payload"

    # frob:ticket T-4018
    def test_empty_row_logs_a_warning_naming_table_and_keys(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An empty-but-present row is not silently swallowed as an
        ordinary miss -- it logs a WARNING naming the table and the
        lookup keys, so cache corruption or a concurrency fault stays
        diagnosable (T-4018)."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.store_parsed_artifact(
            conn, content_hash="deadbeef", fingerprint="frob==0.0.0", payload="x"
        )
        self._force_empty_rows(conn)
        with caplog.at_level("WARNING", logger="frob.graph.cache"):
            graph_cache.load_parsed_artifact(
                conn, content_hash="deadbeef", fingerprint="frob==0.0.0"
            )
        warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("parsed_artifacts" in msg and "deadbeef" in msg for msg in warnings)


# frob:ticket T-4047
class TestReadRootEmptyRowGuard:
    """`_read_root`/`get_root` were missed by T-4018's sweep (T-4047): they
    carried the identical `row is not None` mis-guard on the `meta.root`
    lookup. Same fixture technique as `TestEmptyRowGuard` -- a column-scoped
    `row_factory` override constructs the empty-row condition directly."""

    # frob:ticket T-4047
    @staticmethod
    def _force_empty_root_row(conn: sqlite3.Connection) -> None:
        """Make the `meta.value` root-lookup query's `fetchone()` return
        `()` on `conn` (T-4047) -- see `_force_empty_rows_for_column`."""
        _force_empty_rows_for_column(conn, "value")

    # frob:ticket T-4047
    def test_empty_root_row_is_a_clean_miss_not_a_crash(self, tmp_path: Path) -> None:
        """`get_root` returns `None`, not `IndexError`, when `fetchone()`
        yields `()` for an otherwise-present `meta.root` row (T-4047)."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.set_root(conn, "/some/repo")
        self._force_empty_root_row(conn)
        assert graph_cache.get_root(conn) is None

    # frob:ticket T-4047
    def test_genuine_root_still_returns_unchanged(self, tmp_path: Path) -> None:
        """The truthiness-guard fix does not disturb an ordinary root read."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.set_root(conn, "/some/repo")
        assert graph_cache.get_root(conn) == "/some/repo"

    # frob:ticket T-4047
    def test_empty_root_row_logs_a_warning_naming_table_and_key(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An empty-but-present `meta.root` row logs a WARNING naming the
        table and key rather than silently reading as a clean miss."""
        conn = graph_cache.connect(tmp_path / "cache.db")
        graph_cache.set_root(conn, "/some/repo")
        self._force_empty_root_row(conn)
        with caplog.at_level("WARNING", logger="frob.graph.cache"):
            graph_cache.get_root(conn)
        warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("meta" in msg and "root" in msg for msg in warnings)


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
# frob:ticket T-4419
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
    # tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_sibling_reader_survives_concurrent_recreate  # noqa: E501
    # frob:tests src/frob/graph/cache.py::connect_readonly
    # frob:tests src/frob/graph/cache.py::_with_lock_retry
    @_WIN32_NO_REPLACE_OVER_OPEN_HANDLE
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

    # frob:ticket T-4419
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_path_never_absent_during_recreate  # noqa: E501
    # frob:tests src/frob/graph/cache.py::_quarantine_main_db
    # frob:tests src/frob/graph/cache.py::_quarantine_sidecars
    def test_path_never_absent_during_recreate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Asserts `path` is present immediately before and after every
        call to the three primitives `_recreate` touches `path` through
        (`os.replace`, `os.link`, `Path.rename` for the sidecar
        quarantine), by patching each to record path existence around
        the call. See T-4454 for the design rationale."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache.store_parsed_artifact(
            conn, content_hash="h", fingerprint="f", payload="one"
        )

        observations: list[tuple[str, bool]] = []

        real_replace = os.replace
        real_link = os.link
        real_rename = Path.rename

        def _record(label: str) -> None:
            observations.append((label, path.exists()))

        def traced_replace(src: str | os.PathLike, dst: str | os.PathLike) -> None:
            _record(f"before os.replace->{dst}")
            real_replace(src, dst)
            _record(f"after os.replace->{dst}")

        def traced_link(src: str | os.PathLike, dst: str | os.PathLike) -> None:
            _record(f"before os.link->{dst}")
            real_link(src, dst)
            _record(f"after os.link->{dst}")

        def traced_rename(self: Path, target: str | os.PathLike) -> Path:
            _record(f"before rename {self}->{target}")
            result = real_rename(self, target)
            _record(f"after rename {self}->{target}")
            return result

        monkeypatch.setattr(os, "replace", traced_replace)
        monkeypatch.setattr(os, "link", traced_link)
        monkeypatch.setattr(Path, "rename", traced_rename)

        conn = graph_cache._recreate(graph_cache._open(path), path)
        graph_cache._close_conn(conn)

        assert observations, "expected _recreate to touch path via a traced primitive"
        absent = [label for label, existed in observations if not existed]
        assert not absent, (
            f"path was observed absent around: {absent} (full sequence: {observations})"
        )

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_quarantined_sidecars_are_renamed_not_unlinked  # noqa: E501
    # frob:tests src/frob/graph/cache.py::_quarantine_sidecars
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
    # tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_sweep_removes_only_old_quarantined_sidecars  # noqa: E501
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
# frob:ticket T-4419
class TestRecreateNeverExposesASchemaIncompleteDb:
    """Asserts a fresh replacement db built by `_recreate` (or the first
    `connect()` at a brand-new path) is never observable by a concurrent
    connection before its schema is fully applied. See T-3623 for the
    design rationale."""

    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_recreate_replacement_always_has_meta_table  # noqa: E501
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
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_first_ever_connect_never_exposes_a_tableless_file  # noqa: E501
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
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_two_processes_connecting_concurrently_never_see_no_such_table_meta  # noqa: E501
    # reason: two-process sqlite recreate/connect race sized to a wall-clock
    # window (3.0s); underlying bug fixed through 9 rounds (T-3623/T-3700),
    # residual failure is timing starvation under xdist CI load, not a
    # deterministic defect.
    # frob:tests src/frob/graph/cache.py::get_root
    # frob:tests src/frob/graph/cache.py::_check_fingerprint_with_recovery
    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    @_WIN32_NO_REPLACE_OVER_OPEN_HANDLE
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
    # frob:ticket T-4419
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_run_with_stale_reconnect_recovers_from_bare_database_error  # noqa: E501
    def test_run_with_stale_reconnect_recovers_from_bare_database_error(
        self, tmp_path: Path
    ) -> None:
        """Asserts `_run_with_stale_reconnect` catches a bare
        `sqlite3.DatabaseError` ("file is not a database", not a subclass
        of `OperationalError`) and recovers via its retry loop instead of
        propagating, by deterministically forcing the error shape rather
        than racing for it. See T-3706 for the design rationale."""
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
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_check_fingerprint_with_recovery_recovers_from_bare_database_error  # noqa: E501
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
    # frob:ticket T-4419
    # frob:tests \
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_run_with_stale_reconnect_recovers_from_interface_error  # noqa: E501
    def test_run_with_stale_reconnect_recovers_from_interface_error(
        self, tmp_path: Path
    ) -> None:
        """Asserts `_run_with_stale_reconnect` catches
        `sqlite3.InterfaceError('bad parameter or other API misuse')`
        (a sibling of `DatabaseError` under `sqlite3.Error`, not a
        subclass of it) and recovers via its retry loop instead of
        propagating, by deterministically forcing the error shape rather
        than racing for it. See T-3733 for the design rationale."""
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
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_check_fingerprint_with_recovery_recovers_from_interface_error  # noqa: E501
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
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_is_stale_or_corrupt_connection_matches_interface_error_by_type  # noqa: E501
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
    # tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_apply_schema_rebuild_replacement_always_has_files_table  # noqa: E501
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
    # tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection.test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection  # noqa: E501
    # frob:tests src/frob/graph/cache.py::_inprocess_write_lock
    @_WIN32_NO_REPLACE_OVER_OPEN_HANDLE
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
    # tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection.test_recreate_closed_connection_raises_a_clean_programming_error_not_interface_error  # noqa: E501
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
# frob:ticket T-4419
class TestLockBackoff:
    """Covers `_lock_backoff_seconds`'s exponential backoff between
    lock-retry attempts, replacing a fixed sleep interval. See T-3654 for
    the design rationale."""

    # frob:tests src/frob/graph/cache.py::_lock_backoff_seconds
    # frob:tests src/frob/graph/cache.py::_connect_with_backoff
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
# frob:ticket T-4419
class TestHandleIdentity:
    """Asserts a connection detects a sibling's `os.replace` and reopens
    at the canonical path, rather than staying bound to a stale/readonly
    inode. See T-3669 for the design rationale."""

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
    @_WIN32_NO_REPLACE_OVER_OPEN_HANDLE
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
    @_WIN32_NO_REPLACE_OVER_OPEN_HANDLE
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
    # frob:tests src/frob/graph/cache.py::_reopen_without_closing
    @_WIN32_NO_REPLACE_OVER_OPEN_HANDLE
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


# frob:ticket T-3820
class TestReplaceWithRetry:
    """`_replace_with_retry` is the shared atomic-publish primitive: it must
    retry a TRANSIENT `os.replace` failure (Windows [WinError 5] while a
    concurrent reader momentarily holds the destination open) and land the
    publish once a window opens, yet re-raise cleanly when the fault never
    clears (a reader holding the handle open for the whole rebuild).

    Cross-platform by construction -- the real Windows failure is simulated
    by monkeypatching `os.replace`, so this pins the retry contract on every
    platform (the genuine Windows behavior itself is confirmed via winrun,
    T-3820/T-3781; the 6 skipped tests above cover the unsupported
    persistent-handle case)."""

    @staticmethod
    def _marked_db(path: Path, marker: str) -> None:
        """Write a sqlite db at `path` carrying `meta.marker = marker` -- a
        distinguishable payload to prove which file won a publish, without
        raw `read_bytes`/`write_bytes` (which the testsuite node's effect
        gate tracks as an undeclared fs capability)."""
        conn = sqlite3.connect(str(path))
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT, value TEXT)")
            conn.execute(
                "INSERT INTO meta (key, value) VALUES ('marker', ?)", (marker,)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _marker(path: Path) -> str | None:
        """`meta.marker` at `path` via an INDEPENDENT sqlite connection."""
        reader = sqlite3.connect(str(path))
        try:
            row = reader.execute(
                "SELECT value FROM meta WHERE key = 'marker'"
            ).fetchone()
        finally:
            reader.close()
        return None if row is None else row[0]

    def test_transient_permission_error_is_retried_then_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two consecutive `PermissionError`s (the transient competing-handle
        shape) are absorbed by backoff; the third attempt publishes."""
        src = tmp_path / "src.db"
        self._marked_db(src, "winner")
        dst = tmp_path / "dst.db"
        self._marked_db(dst, "old")

        real_replace = os.replace
        calls = {"n": 0}

        def flaky_replace(a: Path, b: Path) -> None:
            calls["n"] += 1
            if calls["n"] < 3:
                raise PermissionError(5, "Access is denied")
            real_replace(a, b)

        monkeypatch.setattr(graph_cache.os, "replace", flaky_replace)
        graph_cache._replace_with_retry(src, dst, what="probe")

        assert calls["n"] == 3, "the transient faults were not retried to success"
        assert self._marker(dst) == "winner", "the publish did not land"
        assert not src.exists(), "the temp file was not consumed by the rename"

    def test_persistent_permission_error_is_reraised_after_the_deadline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A never-clearing `PermissionError` (a reader holding the handle
        open across the whole rebuild) is re-raised once the bounded budget
        is spent -- the fault is surfaced, never swallowed."""
        src = tmp_path / "src.db"
        self._marked_db(src, "winner")
        dst = tmp_path / "dst.db"

        def always_denied(a: Path, b: Path) -> None:
            raise PermissionError(5, "Access is denied")

        monkeypatch.setattr(graph_cache.os, "replace", always_denied)
        monkeypatch.setattr(graph_cache, "_REPLACE_RETRY_TOTAL_TIMEOUT_SECONDS", 0.2)

        started = time.monotonic()
        with pytest.raises(PermissionError):
            graph_cache._replace_with_retry(src, dst, what="probe")
        elapsed = time.monotonic() - started
        assert elapsed < 5.0, "the bounded retry did not honor its deadline"

    def test_posix_happy_path_replaces_on_the_first_attempt(
        self, tmp_path: Path
    ) -> None:
        """With no fault, exactly one `os.replace` runs -- POSIX behavior is
        unchanged, the retry loop adds no overhead on the common path."""
        src = tmp_path / "src.db"
        self._marked_db(src, "winner")
        dst = tmp_path / "dst.db"
        self._marked_db(dst, "old")

        graph_cache._replace_with_retry(src, dst, what="probe")
        assert self._marker(dst) == "winner"
        assert not src.exists()


# frob:ticket T-4159
class TestCorruptCacheSelfHeals:
    """T-4159: a `cache.db` whose bytes fail sqlite's own `PRAGMA
    integrity_check` must be detected and rebuilt from empty, never
    silently served or endlessly retried against -- the exact live
    symptom measured in this checkout (`store_file_data` retrying 3
    times against a genuinely corrupt db, then giving up with a
    misleading "cache lock never released" message)."""

    @staticmethod
    def _corrupt_in_place(path: Path) -> None:
        """Flip a block of bytes well past sqlite's header (offset 100)
        so `PRAGMA integrity_check` reports real page-structure damage,
        not merely an empty/truncated file -- the same "torn write to a
        live page" shape production hits, not a synthetic string match."""
        with open(path, "r+b") as fh:
            fh.seek(100)
            fh.write(b"\xff" * 200)

    # frob:tests src/frob/graph/cache.py::_cache_integrity_ok
    def test_integrity_check_reports_corrupt(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals.test_integrity_check_reports_corrupt  # noqa: E501
        """MUST-FIRE half 1: a deliberately corrupted db fails the check.
        Positive control (MUST-STAY-QUIET): an untouched db still passes."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        conn.close()
        assert graph_cache._cache_integrity_ok(path) is True

        self._corrupt_in_place(path)
        assert graph_cache._cache_integrity_ok(path) is False

    # frob:tests src/frob/graph/cache.py::_rebuild_because_corrupt
    def test_corrupt_cache_self_heals(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals.test_corrupt_cache_self_heals  # noqa: E501
        """MUST-FIRE fixture (THIRD FIXTURE): `_rebuild_because_corrupt`
        replaces a corrupt db with a fresh, empty, schema-complete one
        rather than raising or handing back the bad bytes."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache.store_file_data(
            conn,
            file_path="src/a.py",
            content_hash="deadbeef",
            mtime_ns=1,
            size=1,
            symbols=(),
            edges=(),
            malformed=(),
        )
        conn.commit()
        conn.close()
        self._corrupt_in_place(path)
        assert graph_cache._cache_integrity_ok(path) is False

        fresh = graph_cache._rebuild_because_corrupt(path, what="test probe")
        try:
            assert graph_cache._cache_integrity_ok(path) is True
            # Data loss is expected and correct: a corrupt db cannot be
            # trusted to still hold what it appeared to hold.
            assert graph_cache.get_file_meta(fresh, "src/a.py") is None
        finally:
            fresh.close()

    # frob:tests src/frob/graph/cache.py::_rebuild_if_genuinely_corrupt
    # frob:tests src/frob/graph/cache.py::_is_genuine_corruption_shape
    def test_run_with_stale_reconnect_rebuilds_and_completes_on_corruption(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals.test_run_with_stale_reconnect_rebuilds_and_completes_on_corruption  # noqa: E501
        """MUST-FIRE fixture, end to end: an ALREADY-OPEN connection
        (mirroring production, where `connect()` succeeded before the db
        went bad mid-session) that hits "database disk image is
        malformed" mid-operation must have the operation complete
        against a rebuilt cache, not raise the stale error forever."""
        path = tmp_path / "cache.db"
        setup = graph_cache.connect(path)
        graph_cache.store_file_data(
            setup,
            file_path="src/a.py",
            content_hash="deadbeef",
            mtime_ns=1,
            size=1,
            symbols=(),
            edges=(),
            malformed=(),
        )
        setup.commit()
        setup.close()
        self._corrupt_in_place(path)

        # `_open` only sets pragmas -- it does not touch a page, so it
        # succeeds even against a corrupt file, exactly like a
        # connection that was opened before the corruption occurred.
        stale = graph_cache._open(path)

        # Must not raise, and must not merely retry forever against the
        # same bad bytes.
        result = graph_cache.get_file_meta(stale, "src/a.py")
        assert result is None, (
            "the corrupt cache was rebuilt (empty), so the prior entry "
            "is correctly gone rather than served from bad bytes"
        )
        assert graph_cache._cache_integrity_ok(path) is True, (
            "the on-disk cache was not actually rebuilt clean"
        )

    # frob:tests src/frob/graph/cache.py::_rebuild_if_genuinely_corrupt
    def test_win32_rebuild_closes_the_callers_stale_connection_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals.test_win32_rebuild_closes_the_callers_stale_connection_first  # noqa: E501
        """T-4402 (Linux-runnable): a Windows regression (CI run
        34546329688) had this exact rebuild fail with `PermissionError:
        [WinError 5] Access is denied` from `os.replace(tmp_path, path)`
        inside `_recreate`, because the CALLER's own stale connection
        (`stale` below -- the second open handle: one connection opened
        by this test, held across the corruption, plus the internal
        `throwaway` connection `_rebuild_because_corrupt` itself opens
        and closes) was still open on `path` when the replace ran --
        Windows refuses to replace a path with ANY open handle, unlike
        POSIX rename, which never cares who else has the destination
        open. This cannot reproduce the `PermissionError` itself on
        Linux, so `sys.platform` is forced to `"win32"` here (the only
        way this fix's behavior differs by platform) to run the actual
        win32 code path natively.

        `stale.execute(...)` after the rebuild must raise sqlite3's own
        `ProgrammingError` for a closed connection -- proving the handle
        that would have blocked Windows's `os.replace` is actually
        closed by `_rebuild_if_genuinely_corrupt` BEFORE the replace
        runs, not merely left dangling until some later, coincidental
        close. The rebuild itself must still complete and report a
        clean, empty cache regardless of platform."""
        monkeypatch.setattr(graph_cache.sys, "platform", "win32")
        path = tmp_path / "cache.db"
        setup = graph_cache.connect(path)
        graph_cache.store_file_data(
            setup,
            file_path="src/a.py",
            content_hash="deadbeef",
            mtime_ns=1,
            size=1,
            symbols=(),
            edges=(),
            malformed=(),
        )
        setup.commit()
        setup.close()
        self._corrupt_in_place(path)

        stale = graph_cache._open(path)
        result = graph_cache.get_file_meta(stale, "src/a.py")
        assert result is None, (
            "the corrupt cache was rebuilt (empty), so the prior entry "
            "is correctly gone rather than served from bad bytes"
        )
        assert graph_cache._cache_integrity_ok(path) is True

        with pytest.raises(sqlite3.ProgrammingError):
            stale.execute("SELECT 1")

    def test_healthy_cache_never_triggers_a_rebuild(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals.test_healthy_cache_never_triggers_a_rebuild  # noqa: E501
        """MUST-STAY-QUIET: an ordinary, healthy cache never calls the new
        rebuild path -- this fix must not degrade the common case."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        graph_cache.store_file_data(
            conn,
            file_path="src/a.py",
            content_hash="deadbeef",
            mtime_ns=1,
            size=1,
            symbols=(),
            edges=(),
            malformed=(),
        )
        conn.commit()

        calls: list[Path] = []
        monkeypatch.setattr(
            graph_cache,
            "_rebuild_because_corrupt",
            lambda p, **kw: (
                calls.append(p) or graph_cache._recreate(sqlite3.connect(str(p)), p)
            ),
        )

        assert graph_cache.get_file_meta(conn, "src/a.py") == ("deadbeef", 1, 1)
        assert calls == [], "a healthy cache must never be rebuilt"


# frob:ticket T-4412
class TestLockedDbNeverRebuilds:
    """T-4412: `database is locked` (T-3644: or its TRUNCATE-mode
    `readonly database` sibling) must never be classified as an
    unreadable/corrupt db and rebuilt -- it is a live, healthy cache a
    sibling process merely has open right now. `connect()` must instead
    resolve it via `_with_lock_retry`'s existing bounded busy-wait, either
    succeeding once the lock clears or raising `CacheLocked` (naming the
    holder) once the retry budget is exhausted."""

    # frob:tests src/frob/graph/cache.py::connect
    # frob:tests src/frob/graph/cache.py::_read_schema_version
    def test_locked_db_is_never_classified_as_unreadable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds.test_locked_db_is_never_classified_as_unreadable  # noqa: E501
        """Positive control (real second connection holding an exclusive
        lock, not a synthetic monkeypatch of the error): `connect()` must
        wait out the lock and succeed, never rebuild. Rebuild is detected
        by asserting the file's inode is unchanged (a rebuild replaces
        the inode via `os.replace`, T-3607) and that no `cache.db.stale-*`
        quarantine sidecar appears -- NOT by a byte-identity check, since
        the blocker's own committed `INSERT` legitimately changes the
        file's bytes and that is expected, correct behavior."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        conn.commit()
        conn.close()
        original_inode = path.stat().st_ino

        blocker = sqlite3.connect(str(path), timeout=0.1, check_same_thread=False)
        blocker.execute("BEGIN EXCLUSIVE")
        blocker.execute("INSERT INTO meta (key, value) VALUES ('x', '1')")

        monkeypatch.setattr(graph_cache, "_LOCK_POLL_SECONDS", 0.05)
        monkeypatch.setattr(graph_cache, "_LOCK_TOTAL_TIMEOUT_SECONDS", 2.0)

        rebuild_calls: list[Path] = []
        monkeypatch.setattr(
            graph_cache,
            "_recreate",
            lambda c, p: rebuild_calls.append(p) or c,
        )

        def _release_after_delay() -> None:
            time.sleep(0.2)
            blocker.commit()
            blocker.close()

        releaser = threading.Thread(target=_release_after_delay)
        releaser.start()
        try:
            reopened = graph_cache.connect(path)
            reopened.close()
        finally:
            releaser.join()

        assert rebuild_calls == []
        assert path.stat().st_ino == original_inode
        assert not list(tmp_path.glob("cache.db.stale-*"))

    def test_lock_exhaustion_raises_cache_locked_naming_the_holder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds.test_lock_exhaustion_raises_cache_locked_naming_the_holder  # noqa: E501
        """A lock that never clears within the retry budget must surface
        as `CacheLocked` naming the lock, never a rebuild."""
        path = tmp_path / "cache.db"
        conn = graph_cache.connect(path)
        conn.commit()
        conn.close()

        blocker = sqlite3.connect(str(path), timeout=0.1, check_same_thread=False)
        blocker.execute("BEGIN EXCLUSIVE")
        blocker.execute("INSERT INTO meta (key, value) VALUES ('x', '1')")

        monkeypatch.setattr(graph_cache, "_LOCK_POLL_SECONDS", 0.01)
        monkeypatch.setattr(graph_cache, "_LOCK_TOTAL_TIMEOUT_SECONDS", 0.05)

        rebuild_calls: list[Path] = []
        monkeypatch.setattr(
            graph_cache,
            "_recreate",
            lambda c, p: rebuild_calls.append(p) or c,
        )

        try:
            with pytest.raises(graph_cache.CacheLocked) as excinfo:
                graph_cache.connect(path)
            assert "locked" in str(excinfo.value).lower()
        finally:
            blocker.commit()
            blocker.close()

        assert rebuild_calls == []

    # frob:tests src/frob/graph/cache.py::_read_schema_version
    def test_genuinely_malformed_db_still_rebuilds(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds.test_genuinely_malformed_db_still_rebuilds  # noqa: E501
        """Positive control: a truly non-sqlite file (never a lock error)
        must still self-heal via `connect()`'s pre-existing T-0141
        recreate path -- this fix narrows the lock case only, it must not
        blunt real corruption recovery."""
        path = tmp_path / "cache.db"
        path.write_bytes(b"not a sqlite file at all")

        conn = graph_cache.connect(path)
        try:
            cur = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'")
            assert cur.fetchone() is not None
        finally:
            conn.close()


# frob:ticket T-4411
class TestSeedDisposableWorktreeCache:
    """T-4411: `seed_disposable_worktree_cache` copies a primary
    checkout's `.frob/cache.db` into a disposable land squash worktree so
    `load_graph` there finds a warm cache instead of rebuilding the whole
    graph uncached."""

    # frob:tests src/frob/graph/cache.py::seed_disposable_worktree_cache
    def test_seeds_from_an_existing_primary_cache(self, tmp_path: Path) -> None:
        """Given a primary checkout with a built cache.db and a fresh
        worktree with none, when seeding runs, then the worktree's
        cache.db is present and `load_graph` reads it as a hit, not
        'no cache at ...'."""
        primary = tmp_path / "primary"
        worktree = tmp_path / "worktree"
        (primary / ".frob").mkdir(parents=True)
        conn = graph_cache.connect(primary / ".frob" / "cache.db")
        conn.close()

        seeded = graph_cache.seed_disposable_worktree_cache(primary, worktree)

        assert seeded is True
        worktree_cache = worktree / ".frob" / "cache.db"
        assert worktree_cache.exists()
        # a copied schema-complete db opens cleanly, i.e. reads as a real
        # cache hit rather than the "no cache at ..." cold-start warning
        conn = sqlite3.connect(str(worktree_cache))
        conn.execute("SELECT 1")
        conn.close()

    # frob:tests src/frob/graph/cache.py::seed_disposable_worktree_cache
    def test_no_primary_cache_is_a_quiet_no_op(self, tmp_path: Path) -> None:
        """Given a primary checkout that has never built a cache, when
        seeding runs, then it declines rather than seeding an empty file
        (a missing worktree cache still reads as a normal, honest cold
        start)."""
        primary = tmp_path / "primary"
        worktree = tmp_path / "worktree"
        primary.mkdir()

        seeded = graph_cache.seed_disposable_worktree_cache(primary, worktree)

        assert seeded is False
        assert not (worktree / ".frob" / "cache.db").exists()

    # frob:tests src/frob/graph/cache.py::seed_disposable_worktree_cache
    def test_primary_journal_present_skips_seeding(self, tmp_path: Path) -> None:
        """Given a primary cache with a NON-EMPTY `cache.db-journal`
        sidecar (T-3644: this module's rollback-journal mode means a
        writer is mid-transaction right now), when seeding runs, then it
        declines rather than copying a torn pre-transaction snapshot --
        the next `load_graph` in the worktree just cold-starts for that
        one file via normal drift detection."""
        primary = tmp_path / "primary"
        worktree = tmp_path / "worktree"
        (primary / ".frob").mkdir(parents=True)
        conn = graph_cache.connect(primary / ".frob" / "cache.db")
        conn.close()
        (primary / ".frob" / "cache.db-journal").write_bytes(b"\x00" * 16)

        seeded = graph_cache.seed_disposable_worktree_cache(primary, worktree)

        assert seeded is False
        assert not (worktree / ".frob" / "cache.db").exists()

    # frob:tests src/frob/graph/cache.py::seed_disposable_worktree_cache
    def test_empty_primary_journal_does_not_block_seeding(self, tmp_path: Path) -> None:
        """Given a primary cache with the ZERO-length `cache.db-journal`
        that this module's TRUNCATE journal mode routinely leaves behind
        after an ordinary commit (not a live-write signal), when seeding
        runs, then it still seeds -- mere existence of the journal must
        never be mistaken for a mid-transaction write."""
        primary = tmp_path / "primary"
        worktree = tmp_path / "worktree"
        (primary / ".frob").mkdir(parents=True)
        conn = graph_cache.connect(primary / ".frob" / "cache.db")
        conn.close()
        assert (primary / ".frob" / "cache.db-journal").exists()

        seeded = graph_cache.seed_disposable_worktree_cache(primary, worktree)

        assert seeded is True
        assert (worktree / ".frob" / "cache.db").exists()

    # frob:ticket T-4411
    # frob:tests src/frob/graph/cache.py::seed_disposable_worktree_cache
    def test_seeded_worktree_cache_only_reparses_the_touched_file(
        self, tmp_path: Path
    ) -> None:
        """T-4411 acceptance criterion 2: a cache seeded from the primary
        checkout is stale for whatever the disposable worktree's squash
        touched, but normal drift detection still recomputes only THOSE
        entries on the next `build_graph` -- seeding must not force (or
        accidentally trigger) a full uncached rebuild of the whole graph."""
        from frob.graph import build_graph

        primary = tmp_path / "primary"
        worktree = tmp_path / "worktree"
        for root in (primary, worktree):
            (root / "src").mkdir(parents=True)
            (root / "src" / "a.py").write_text("def foo() -> None:\n    pass\n")
            (root / "src" / "b.py").write_text("def bar() -> None:\n    pass\n")

        primary_cache = primary / ".frob" / "cache.db"
        build_graph(primary, primary_cache).danger_ok

        seeded = graph_cache.seed_disposable_worktree_cache(primary, worktree)
        assert seeded is True

        # the squash touched only a.py -- b.py's seeded row is still fresh
        (worktree / "src" / "a.py").write_text("def foo() -> None:\n    return None\n")

        worktree_cache = worktree / ".frob" / "cache.db"
        result = build_graph(worktree, worktree_cache)
        assert result.is_ok
        assert result.danger_ok.stats.parsed == 1
        assert result.danger_ok.stats.cache_hits == 1
