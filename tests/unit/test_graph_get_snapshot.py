"""Tests for `frob.graph.get_snapshot` (T-4688): the shared
content-keyed load-or-build entry point introduced to replace 18
independently duplicated `load_graph`-then-`build_graph` call sites across
src/frob. Kept in its own file rather than tests/test_graph.py because that
file's lease was held by an in-progress sibling ticket at write time.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent directories as needed."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-4688
class TestGetSnapshot:
    """`get_snapshot`: the shared content-keyed load-or-build entry point
    T-4688 introduced to replace 18 independently duplicated
    `load_graph`-then-`build_graph` call sites across src/frob."""

    # frob:tests src/frob/graph/__init__.py::get_snapshot
    def test_second_call_on_unchanged_tree_does_not_rebuild(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two consecutive `get_snapshot` calls against an unchanged tree:
        the second must be a `load_graph` cache hit, never falling through
        to `build_graph` -- the exact cross-process-reuse contract
        T-4688 was filed to guarantee."""
        import frob.graph as graph_mod

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"

        first = graph_mod.get_snapshot(tmp_path, cache)
        assert first.is_ok

        build_calls = []
        real_build_graph = graph_mod.build_graph

        def _counting_build_graph(root: Path, cache_path: Path):  # noqa: ANN201
            build_calls.append((root, cache_path))
            return real_build_graph(root, cache_path)

        monkeypatch.setattr(graph_mod, "build_graph", _counting_build_graph)

        second = graph_mod.get_snapshot(tmp_path, cache)
        assert second.is_ok
        assert build_calls == []

    # frob:tests src/frob/graph/__init__.py::get_snapshot
    def test_changed_file_triggers_exactly_one_rebuild(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """One changed file between two `get_snapshot` calls: the second
        call rebuilds exactly once, not once per hypothetical duplicated
        call site."""
        import frob.graph as graph_mod

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        assert graph_mod.get_snapshot(tmp_path, cache).is_ok

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    return None\n")

        build_calls = []
        real_build_graph = graph_mod.build_graph

        def _counting_build_graph(root: Path, cache_path: Path):  # noqa: ANN201
            build_calls.append((root, cache_path))
            return real_build_graph(root, cache_path)

        monkeypatch.setattr(graph_mod, "build_graph", _counting_build_graph)

        result = graph_mod.get_snapshot(tmp_path, cache)
        assert result.is_ok
        assert len(build_calls) == 1

    # frob:tests src/frob/graph/__init__.py::get_snapshot
    def test_load_failure_falls_back_to_build(self, tmp_path: Path) -> None:
        """A never-built cache (no `.frob/cache.db` yet) is a `load_graph`
        miss that `get_snapshot` transparently covers via `build_graph`."""
        import frob.graph as graph_mod

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"

        result = graph_mod.get_snapshot(tmp_path, cache)
        assert result.is_ok
        assert "src/a.py::foo" in result.danger_ok.symbols
