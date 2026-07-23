"""Regression tests for pre-migration `cache.db` schema drift (T-0799).

A `.frob/cache.db` written under an older `_SCHEMA_VERSION` (missing a
table a later ticket added, or missing a column an existing table gained)
must never crash `load_graph` with a raw `sqlite3.OperationalError` -- it
must be treated as `CacheCorrupt` so the normal load-then-build fallback
(every real caller does `load_graph`, then `build_graph` on `Err`) rebuilds
the cache cleanly. Two such crashes ("no such table: symbols", "no such
column: mtime_ns") escaped mid-land on 2026-07-23 before this fix.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from frob.graph import GraphError, build_graph, load_graph


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs; returns the path."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestSchemaDriftRebuild:
    """T-0799: schema-drifted cache.db files must rebuild, never crash."""

    def test_missing_symbols_table_rebuilds_clean(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/graph/test_cache.py::TestSchemaDriftRebuild.test_missing_symbols_table_rebuilds_clean  # noqa: E501
        """An old cache.db with no `symbols` table at all (a table added by
        a later schema version) must not raise `sqlite3.OperationalError`
        out of `load_graph` -- it is `CacheCorrupt`, and a follow-up
        `build_graph` call rebuilds a working cache from scratch."""
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        cache.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(cache))
        conn.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE files (
                path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('root', ?)", (str(tmp_path),)
        )
        conn.execute(
            "INSERT INTO files (path, content_hash) VALUES (?, ?)",
            ("src/a.py", "deadbeef"),
        )
        conn.commit()
        conn.close()

        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

        rebuilt = build_graph(tmp_path, cache)
        assert rebuilt.is_ok
        assert "src/a.py::foo" in rebuilt.danger_ok.symbols

        reload_result = load_graph(cache)
        assert reload_result.is_ok
        assert "src/a.py::foo" in reload_result.danger_ok.symbols

    def test_missing_mtime_ns_column_rebuilds_clean(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/graph/test_cache.py::TestSchemaDriftRebuild.test_missing_mtime_ns_column_rebuilds_clean  # noqa: E501
        """A pre-T-0245 cache.db whose `files` table has no `mtime_ns`/
        `size` columns must not raise `sqlite3.OperationalError` out of
        `load_graph`'s stat-based staleness probe -- it is `CacheCorrupt`,
        and a follow-up `build_graph` call rebuilds cleanly onto the
        current schema."""
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        cache.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(cache))
        conn.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE files (
                path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL
            );
            CREATE TABLE symbols (
                symref TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                qualname TEXT NOT NULL,
                kind TEXT NOT NULL,
                public INTEGER NOT NULL,
                span_start INTEGER NOT NULL,
                span_end INTEGER NOT NULL,
                digest_sig TEXT NOT NULL,
                digest_body TEXT NOT NULL,
                digest_doc TEXT NOT NULL
            );
            CREATE TABLE edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file TEXT NOT NULL,
                src TEXT NOT NULL,
                kind TEXT NOT NULL,
                target TEXT NOT NULL,
                origin TEXT NOT NULL,
                attrs TEXT NOT NULL
            );
            CREATE TABLE malformed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file TEXT NOT NULL,
                line INTEGER NOT NULL,
                reason TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('root', ?)", (str(tmp_path),)
        )
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', '2')",
        )
        conn.execute(
            "INSERT INTO files (path, content_hash) VALUES (?, ?)",
            ("src/a.py", "deadbeef"),
        )
        conn.commit()
        conn.close()

        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

        rebuilt = build_graph(tmp_path, cache)
        assert rebuilt.is_ok
        assert "src/a.py::foo" in rebuilt.danger_ok.symbols

        reload_result = load_graph(cache)
        assert reload_result.is_ok
        assert "src/a.py::foo" in reload_result.danger_ok.symbols
