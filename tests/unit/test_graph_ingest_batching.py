"""Tests for `frob.graph.build_graph`'s incremental-commit ingest (T-4282).

Kept in its own small file rather than `tests/test_graph.py`: that file's
own pre-existing, unrelated test classes carry heavy private-helper
fan-out into dozens of other modules, and scoping it into this narrow
ticket pulled in that whole unrelated closure (measured via `frob check
--ticket T-4282 --only scope`: adding it produced dozens of SCOPE002
"probable under-capture" findings across files this ticket never
touches). A fresh, minimal file has no such history to drag in.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from frob.graph import build_graph


def _write_source(root: Path, rel: str, content: str) -> Path:
    """Write `content` to `root/rel`, creating parent dirs; returns the path.

    Named `_write_source`, not the repo-wide-conventional `_write`
    (dozens of test files each define their own `_write` helper): frob's
    call-graph resolution matches a private helper call by bare short
    name (a known blind spot -- see "Shared graph wrong for its second
    consumer" in project lore), so a same-named helper here would get
    resolved as a dependency on every OTHER file's same-named `_write`
    too, producing a wall of unrelated SCOPE002 "probable under-capture"
    noise when this file is added to a ticket's scope (measured directly
    while writing this test)."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# frob:ticket T-4282
# frob:tests src/frob/graph/__init__.py::_ingest_source_files
# frob:tests src/frob/graph/__init__.py::_ingest_doc_files
def test_build_graph_commits_in_batches_not_one_final_transaction(
    tmp_path: Path, monkeypatch
) -> None:
    """Proves `build_graph` commits in batches: `conn.commit()` fires
    more often with a small `_INGEST_COMMIT_BATCH_SIZE` than with a
    batch size larger than the whole ingest (one commit at the very end
    plus whatever unrelated per-file commits `store_parsed_artifact`
    makes on its own), so sqlite's rollback-journal writer does not hold
    an EXCLUSIVE lock across the whole ingest once it spills its dirty
    page cache (see T-4282). Uses a differential comparison, not a fixed
    expected count, since the exact baseline includes those unrelated
    commits too."""
    import frob.graph as graph_module

    def _commit_count(root: Path, cache: Path, *, batch_size: int) -> int:
        monkeypatch.setattr(graph_module, "_INGEST_COMMIT_BATCH_SIZE", batch_size)
        commit_calls: list[int] = []

        class _CountingConnection(sqlite3.Connection):
            def commit(self) -> None:
                commit_calls.append(1)
                super().commit()

        real_sqlite_connect = sqlite3.connect

        def _connect_with_counting_factory(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            kwargs.setdefault("factory", _CountingConnection)
            return real_sqlite_connect(*args, **kwargs)

        # sqlite3.Connection is an immutable C type (no ad-hoc attribute
        # or method assignment on an instance or the class), so the
        # counter has to arrive via a `factory=` subclass on `sqlite3.
        # connect` itself -- `_cache`'s own module reference IS this
        # same `sqlite3` module, so patching it here reaches every
        # connection `build_graph` opens.
        with monkeypatch.context() as m:
            m.setattr(sqlite3, "connect", _connect_with_counting_factory)
            result = build_graph(root, cache)
        assert result.is_ok
        return len(commit_calls)

    for i in range(7):
        _write_source(tmp_path, f"src/m{i}.py", f"def f{i}() -> int:\n    return {i}\n")

    batched = _commit_count(tmp_path, tmp_path / ".frob" / "batched.db", batch_size=2)
    unbatched = _commit_count(
        tmp_path, tmp_path / ".frob" / "unbatched.db", batch_size=10_000_000
    )
    assert batched > unbatched, (
        f"a small ingest batch size ({batched} commits) must commit "
        f"strictly more often than a batch size larger than the whole "
        f"ingest ({unbatched} commits, the pre-T-4282 one-transaction "
        "shape) -- build_graph is not committing incrementally"
    )
