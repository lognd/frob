"""T-0712: `frob.perf._sketch_store.list_sketches` -- the read side of
`frob perf hot`'s query surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.perf._sketch_store import (
    SketchStoreConfig,
    _close_all,
    list_sketches,
    put_sketch,
)
from frob.stats._sketch import DEFAULT_ALPHA, add_value, new_sketch


@pytest.fixture(autouse=True)
def _teardown():
    yield
    _close_all()


def _sketch(value: float):
    return add_value(new_sketch(alpha=DEFAULT_ALPHA), value)


class TestListSketches:
    def test_empty_store_is_empty(self, tmp_path: Path) -> None:
        assert list_sketches(tmp_path) == []

    def test_lists_every_stored_row_with_its_label(self, tmp_path: Path) -> None:
        config = SketchStoreConfig()
        put_sketch(tmp_path, "k1", "loop", _sketch(5.0), config, label="pkg.mod.a")
        put_sketch(tmp_path, "k2", "function", _sketch(9.0), config, label="pkg.mod.b")

        rows = list_sketches(tmp_path)
        by_key = {row.section_key: row for row in rows}
        assert set(by_key) == {"k1", "k2"}
        assert by_key["k1"].label == "pkg.mod.a"
        assert by_key["k1"].kind == "loop"
        assert by_key["k2"].label == "pkg.mod.b"

    def test_pre_label_store_still_reads_via_column_migration(
        self, tmp_path: Path
    ) -> None:
        """A store created before T-0712's `label` column existed (the
        original `_SCHEMA`'s `CREATE TABLE IF NOT EXISTS`) still opens
        cleanly -- `_ensure_label_column`'s `ALTER TABLE` migration."""
        import sqlite3

        db_path = tmp_path / ".frob" / "hotgraph_sketches.db"
        db_path.parent.mkdir(parents=True)
        conn = sqlite3.connect(db_path)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sketches (
                section_key TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                last_used REAL NOT NULL,
                payload TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO sketches VALUES (?, ?, ?, ?)",
            ("legacy-key", "loop", 0.0, _sketch(1.0).model_dump_json()),
        )
        conn.commit()
        conn.close()

        rows = list_sketches(tmp_path)
        assert len(rows) == 1
        assert rows[0].section_key == "legacy-key"
        assert rows[0].label == ""
