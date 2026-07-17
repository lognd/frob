"""Tests for frob.graph -- obligation graph registry (docs/graph.md)."""

from __future__ import annotations

from pathlib import Path

from frob.graph import (
    GraphError,
    build_graph,
    edges_from,
    edges_to,
    load_graph,
    resolve,
)
from frob.graph.digest import compute_digests
from frob.graph.dsl import markdown_anchors, parse_directives
from frob.lang import parse_file


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


_BASE_PY = '''"""Module docstring."""


class Widget:
    """A widget."""

    def render(self, value: int) -> str:
        """Render the widget."""
        # frob:doc docs/x.md#widget
        data = value + 1
        return str(data)
'''


class TestDigests:
    def _parse(self, tmp_path: Path, text: str, name: str = "sample.py"):
        path = _write(tmp_path, name, text)
        return parse_file(path).danger_ok

    def _method(self, pf):
        return next(s for s in pf.symbols if s.qualname == "Widget.render")

    def test_reformat_identical_digests(self, tmp_path: Path) -> None:
        orig = self._parse(tmp_path, _BASE_PY, "a.py")
        reformatted = _BASE_PY.replace("    def render", "    def   render") + "\n\n"
        rf = self._parse(tmp_path, reformatted, "b.py")
        d1 = compute_digests(self._method(orig))
        d2 = compute_digests(self._method(rf))
        assert d1.sig == d2.sig
        assert d1.body == d2.body

    def test_param_rename_moves_sig_only(self, tmp_path: Path) -> None:
        orig = self._parse(tmp_path, _BASE_PY, "a.py")
        renamed = self._parse(
            tmp_path,
            _BASE_PY.replace(
                "def render(self, value: int)", "def render(self, amount: int)"
            ),
            "b.py",
        )
        d1 = compute_digests(self._method(orig))
        d2 = compute_digests(self._method(renamed))
        assert d1.sig != d2.sig
        assert d1.body == d2.body
        assert d1.doc == d2.doc

    def test_body_edit_changes_body_only(self, tmp_path: Path) -> None:
        orig = self._parse(tmp_path, _BASE_PY, "a.py")
        edited = self._parse(
            tmp_path, _BASE_PY.replace("data = value + 1", "data = value + 2"), "b.py"
        )
        d1 = compute_digests(self._method(orig))
        d2 = compute_digests(self._method(edited))
        assert d1.sig == d2.sig
        assert d1.body != d2.body
        assert d1.doc == d2.doc

    def test_docstring_edit_changes_doc_only(self, tmp_path: Path) -> None:
        orig = self._parse(tmp_path, _BASE_PY, "a.py")
        edited = self._parse(
            tmp_path,
            _BASE_PY.replace('"""Render the widget."""', '"""Render it."""'),
            "b.py",
        )
        d1 = compute_digests(self._method(orig))
        d2 = compute_digests(self._method(edited))
        assert d1.sig == d2.sig
        assert d1.body == d2.body
        assert d1.doc != d2.doc


class TestDsl:
    def test_hash_comment_directive(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:ticket T-0042
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "T-0042"
        assert edges[0].src.endswith("::foo")

    def test_slash_slash_directive(self, tmp_path: Path) -> None:
        src = """function foo(): void {
    // frob:invariant INV-007
}
"""
        pf = parse_file(_write(tmp_path, "a.ts", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "INV-007"

    def test_block_comment_directive(self, tmp_path: Path) -> None:
        src = """int foo(void) {
    /* frob:waive RULE-1 reason="known issue" */
    return 0;
}
"""
        pf = parse_file(_write(tmp_path, "a.c", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "RULE-1"
        assert edges[0].attrs["reason"] == "known issue"

    def test_binds_to_enclosing_symbol(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:ticket T-0001
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].src == f"{pf.path}::foo"

    def test_binds_to_following_symbol(self, tmp_path: Path) -> None:
        src = """# frob:ticket T-0002
def foo() -> None:
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].src == f"{pf.path}::foo"

    def test_bare_file_when_no_binding(self, tmp_path: Path) -> None:
        src = "# frob:ticket T-0003\n\n\n\n\ndef far_away() -> None:\n    pass\n"
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].src == pf.path

    def test_tests_verb_attrs(self, tmp_path: Path) -> None:
        src = """def test_it() -> None:
    # frob:tests src/foo.py::Widget.render kind="e2e"
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert edges[0].attrs["kind"] == "e2e"

    def test_tests_verb_default_kind(self, tmp_path: Path) -> None:
        src = """def test_it() -> None:
    # frob:tests src/foo.py::Widget.render
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, _ = parse_directives(pf)
        assert edges[0].attrs["kind"] == "unit"

    def test_unknown_verb_is_malformed(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:bogus target
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert malformed[0].file == pf.path

    def test_missing_target_is_malformed(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:ticket
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        _edges, malformed = parse_directives(pf)
        assert len(malformed) == 1

    def test_waive_without_reason_is_malformed(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:waive RULE-1
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        _edges, malformed = parse_directives(pf)
        assert len(malformed) == 1

    def test_bad_attr_syntax_is_malformed(self, tmp_path: Path) -> None:
        src = """def foo() -> None:
    # frob:ticket T-1 not-an-attr
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        _edges, malformed = parse_directives(pf)
        assert len(malformed) == 1


class TestMarkdownAnchors:
    def test_describes_edge_with_heading_slug_and_facet(self) -> None:
        text = """# Top Heading

## Lock File

<!-- frob:describes src/frob/graph/lock.py::LockFile body -->
Some text.
"""
        edges = markdown_anchors("docs/graph.md", text)
        assert len(edges) == 1
        edge = edges[0]
        assert edge.src == "docs/graph.md#lock-file"
        assert edge.target == "src/frob/graph/lock.py::LockFile"
        assert edge.attrs["facet"] == "body"

    def test_default_facet_is_sig(self) -> None:
        text = "<!-- frob:describes src/foo.py::bar -->\n"
        edges = markdown_anchors("docs/foo.md", text)
        assert edges[0].attrs["facet"] == "sig"
        assert edges[0].src == "docs/foo.md#top"


class TestBuildIncremental:
    def _tree(self, tmp_path: Path) -> Path:
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(tmp_path, "src/b.py", "def bar() -> None:\n    pass\n")
        return tmp_path

    def test_second_build_is_all_cache_hits(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::build_graph
        root = self._tree(tmp_path)
        cache = root / ".frob" / "cache.db"
        first = build_graph(root, cache).danger_ok
        assert first.stats.parsed == 2
        second = build_graph(root, cache).danger_ok
        assert second.stats.parsed == 0
        assert second.stats.cache_hits == 2

    def test_touching_one_file_reparses_only_it(self, tmp_path: Path) -> None:
        root = self._tree(tmp_path)
        cache = root / ".frob" / "cache.db"
        build_graph(root, cache).danger_ok
        _write(root, "src/a.py", "def foo() -> None:\n    return None\n")
        third = build_graph(root, cache).danger_ok
        assert third.stats.parsed == 1
        assert third.stats.cache_hits == 1


class TestExclude:
    """`[graph] exclude` in frob.toml is additive to the built-in dir excludes."""

    def test_glob_excludes_matching_files(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(tmp_path, "tests/fixtures/bad.py", "def broken(:\n")
        _write(
            tmp_path,
            "frob.toml",
            '[graph]\nexclude = ["tests/fixtures/**"]\n',
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        paths = {rec.id.path for rec in snap.symbols.values()}
        assert "src/a.py" in paths
        assert not any(p.startswith("tests/fixtures/") for p in paths)

    def test_no_config_excludes_nothing_extra(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(tmp_path, "tests/fixtures/b.py", "def bar() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        paths = {rec.id.path for rec in snap.symbols.values()}
        assert "src/a.py" in paths
        assert "tests/fixtures/b.py" in paths


class TestResolve:
    def _snapshot(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/a.py",
            "class Widget:\n    def render(self) -> None:\n        pass\n",
        )
        _write(tmp_path, "src/b.py", "def render() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        return build_graph(tmp_path, cache).danger_ok

    def test_exact_match(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::resolve
        snap = self._snapshot(tmp_path)
        result = resolve(snap, "src/a.py::Widget.render")
        assert result.is_ok
        assert result.danger_ok.id.qualname == "Widget.render"

    def test_suffix_unique_match(self, tmp_path: Path) -> None:
        snap = self._snapshot(tmp_path)
        result = resolve(snap, "Widget.render")
        assert result.is_ok

    def test_ambiguous(self, tmp_path: Path) -> None:
        snap = self._snapshot(tmp_path)
        result = resolve(snap, "render")
        assert result.is_err
        assert result.danger_err == GraphError.AmbiguousSymbol

    def test_unknown(self, tmp_path: Path) -> None:
        snap = self._snapshot(tmp_path)
        result = resolve(snap, "nonexistent")
        assert result.is_err
        assert result.danger_err == GraphError.UnknownSymbol


class TestEdgesFromTo:
    def test_edges_from_and_to(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::edges_from
        # frob:tests src/frob/graph/__init__.py::edges_to
        _write(
            tmp_path,
            "src/a.py",
            "def foo() -> None:\n    # frob:uses-contract src/a.py::bar\n    pass\n\n\ndef bar() -> None:\n    pass\n",
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        src_ref = "src/a.py::foo"
        target_ref = "src/a.py::bar"
        assert len(edges_from(snap, src_ref)) == 1
        assert len(edges_to(snap, target_ref)) == 1


class TestLoadGraph:
    def test_cache_stale_after_edit(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::load_graph
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    return None\n")
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheStale

    def test_cache_corrupt_on_garbage(self, tmp_path: Path) -> None:
        cache = tmp_path / ".frob" / "cache.db"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"not a sqlite database at all, definitely garbage bytes")
        result = load_graph(cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

    def test_cache_corrupt_when_missing(self, tmp_path: Path) -> None:
        result = load_graph(tmp_path / ".frob" / "cache.db")
        assert result.is_err
        assert result.danger_err == GraphError.CacheCorrupt

    # frob:invariant INV-003
    def test_deleted_cache_is_rebuildable_from_source(self, tmp_path: Path) -> None:
        """Deleting `.frob/cache.db` entirely is equivalent to a fresh build."""
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = tmp_path / ".frob" / "cache.db"
        build_graph(tmp_path, cache).danger_ok
        cache.unlink()
        rebuilt = build_graph(tmp_path, cache)
        assert rebuilt.is_ok
        assert "src/a.py::foo" in rebuilt.danger_ok.symbols


class TestCorruptCacheRecovery:
    # frob:tests src/frob/graph/cache.py::connect
    def test_garbage_cache_file_is_recreated(self, tmp_path):
        """T-0019 / INV-003: a cache.db that is not sqlite at all must not
        crash build_graph -- the derived cache is deleted and rebuilt."""
        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "m.py").write_text("def f():\n    return 1\n")
        cache = root / ".frob" / "cache.db"
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b"this is not a sqlite database at all")

        result = build_graph(root, cache)
        assert result.is_ok, result.err
        assert any("m.py" in ref for ref in result.danger_ok.symbols)


class TestDuplicateSymrefs:
    # frob:tests src/frob/graph/__init__.py::build_graph
    def test_overload_and_property_setter_do_not_crash(self, tmp_path):
        """T-0024: @overload chains and property/setter pairs legally repeat
        a qualname in one file; last definition wins, never a crash."""
        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "m.py").write_text(
            "from typing import overload\n\n"
            "@overload\n"
            "def f(x: int) -> int: ...\n"
            "@overload\n"
            "def f(x: str) -> str: ...\n"
            "def f(x):\n"
            "    return x\n\n"
            "class C:\n"
            "    @property\n"
            "    def v(self):\n"
            "        return self._v\n"
            "    @v.setter\n"
            "    def v(self, value):\n"
            "        self._v = value\n",
            encoding="utf-8",
        )
        result = build_graph(root, root / ".frob" / "cache.db")
        assert result.is_ok, result.err
        snap = result.danger_ok
        assert "src/m.py::f" in snap.symbols
        assert "src/m.py::C.v" in snap.symbols


class TestConcurrentCache:
    # frob:ticket T-0029
    def test_concurrent_connections_do_not_raise_disk_io(self, tmp_path):
        # frob:ticket T-0029
        # frob:tests src/frob/graph/cache.py::connect
        """T-0029: two connections writing the same cache.db must serialize on
        WAL + the busy timeout, not raise `sqlite3.OperationalError: disk I/O
        error` (the hard crash a second `frob graph build` process hit).

        This pins the connection-lock fix specifically. Full race-free
        concurrent build_graph on one cache (overlapping schema rebuilds and
        per-file commits) is broader work tracked in T-0029's body -- it wants
        a build lockfile, not just a busy timeout."""
        from concurrent.futures import ThreadPoolExecutor

        from frob.graph import cache as _cache

        cache_path = tmp_path / ".frob" / "cache.db"
        _cache.connect(cache_path).close()  # initialize schema once

        def writer(n: int) -> bool:
            conn = _cache.connect(cache_path)
            try:
                for i in range(20):
                    _cache.set_root(conn, f"root-{n}-{i}")
                    conn.commit()
                return True
            finally:
                conn.close()

        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(writer, n) for n in range(4)]
            assert all(f.result() for f in futures)
