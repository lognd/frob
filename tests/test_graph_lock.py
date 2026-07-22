"""Tests for frob.graph.lock -- acknowledgement and drift (docs/modules/graph.md)."""

from __future__ import annotations

from pathlib import Path

from frob.graph import build_graph
from frob.graph.lock import LockError, acknowledge, drift, load_lock, write_lock


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


_WIDGET_PY = '''class Widget:
    """A widget."""

    def render(self, value: int) -> str:
        """Render the widget."""
        # frob:doc docs/x.md#widget
        return str(value)
'''


class TestAckDrift:
    def _snapshot(self, tmp_path: Path):
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        cache = tmp_path / ".frob" / "cache.db"
        return build_graph(tmp_path, cache).danger_ok

    def test_ack_then_sig_edit_yields_stale(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        # frob:tests src/frob/graph/lock.py::drift
        # T-0556: a no-explicit-facet ack now always also locks `body`
        # (docs/audits/gates-accounting.md B2), so this yields 2 entries,
        # not 1 -- `sig` and `body`, both for the same ref.
        snap = self._snapshot(tmp_path)
        ref = "src/a.py::Widget.render"
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, [ref]).danger_ok
        assert len(acked.entries) == 2
        assert {e.facet for e in acked.entries} == {"sig", "body"}

        _write(
            tmp_path,
            "src/a.py",
            _WIDGET_PY.replace(
                "def render(self, value: int) -> str:",
                "def render(self, value: int, extra: bool = False) -> str:",
            ),
        )
        cache = tmp_path / ".frob" / "cache.db"
        new_snap = build_graph(tmp_path, cache).danger_ok
        report = drift(acked, new_snap)
        assert len(report.stale) == 1
        stale = report.stale[0]
        assert stale.entry.ref == ref
        assert any(o.startswith("src/a.py") for o in stale.dependents)
        assert report.dangling == ()

    def test_ack_then_body_only_rewrite_yields_stale(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        # frob:tests src/frob/graph/lock.py::drift
        # T-0556 (docs/audits/gates-accounting.md B2): the audit's own repro
        # -- ack a `frob:doc` at the default (no explicit) facet, then
        # rewrite ONLY the function body, leaving its signature untouched.
        # Before this fix, a no-facet ack locked only `sig`, so this body
        # rewrite produced zero DRIFT001 signal -- the doc could lie about
        # behavior forever. `_facets_for_ref` now always includes `body`.
        snap = self._snapshot(tmp_path)
        ref = "src/a.py::Widget.render"
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, [ref]).danger_ok

        _write(
            tmp_path,
            "src/a.py",
            _WIDGET_PY.replace(
                "return str(value)",
                'return "value=" + str(value)',
            ),
        )
        cache = tmp_path / ".frob" / "cache.db"
        new_snap = build_graph(tmp_path, cache).danger_ok
        report = drift(acked, new_snap)
        assert len(report.stale) == 1
        assert report.stale[0].entry.facet == "body"

    def test_rename_yields_dangling_candidate_via_body_digest(
        self, tmp_path: Path
    ) -> None:
        # A markdown `frob:describes` anchor holds its target as a literal
        # string -- unlike a comment-bound edge (whose `src` is recomputed
        # from the *current* enclosing symbol on every parse), a rename does
        # NOT move this target along with the code. That is what "dangling"
        # actually means here.
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        _write(
            tmp_path,
            "docs/x.md",
            "# Widget\n\n<!-- frob:describes src/a.py::Widget.render -->\n",
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        ref = "src/a.py::Widget.render"
        record = snap.symbols[ref]

        from frob.graph._models import LockEntry, LockFile

        lock = LockFile(
            entries=(LockEntry(ref=ref, facet="body", digest=record.digests.body),)
        )

        _write(
            tmp_path,
            "src/a.py",
            _WIDGET_PY.replace("def render(", "def draw("),
        )
        new_snap = build_graph(tmp_path, cache).danger_ok
        report = drift(lock, new_snap)
        assert len(report.dangling) == 1
        dangling = report.dangling[0]
        assert dangling.edge.kind.value == "describes"
        assert "src/a.py::Widget.draw" in dangling.candidates

    def test_bare_describes_target_to_nonexistent_symbol_is_dangling(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/lock.py::drift
        # G3 (T-0402): `markdown_anchors` accepts a BARE (no `::`) symref in
        # `<!-- frob:describes ... -->`, so a doc anchor can point at a
        # symbol that never existed. `_vanished_endpoint`'s old
        # `"::" in edge.target` guard skipped bare targets entirely -- this
        # doc silently "described" nothing and `drift` reported zero
        # dangling. Reverting the `EdgeKind.DESCRIBES`-via-`resolve()`
        # branch makes `report.dangling` empty again.
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        _write(
            tmp_path,
            "docs/x.md",
            "# X\n\n<!-- frob:describes does_not_exist -->\n",
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        report = drift(load_lock(tmp_path / "frob.lock").danger_ok, snap)
        assert len(report.dangling) == 1
        assert report.dangling[0].edge.target == "does_not_exist"

    def test_acknowledge_records_every_describes_facet(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        # G11 (T-0402): two DESCRIBES anchors on the same symbol under
        # different facets (`sig` and `doc`) used to collapse to only the
        # FIRST facet found (`_facet_for_ref`, singular) -- the second
        # facet's contract could drift with no `DRIFT001` signal because it
        # was never acked at all. Reverting to the singular-facet lookup
        # makes `acked.entries` length 1 instead of 3.
        # T-0556: `body` is now always also included (B2), so the expected
        # set is {"sig", "doc", "body"}, not just the two explicit facets.
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        _write(
            tmp_path,
            "docs/x.md",
            "# X\n\n"
            "<!-- frob:describes src/a.py::Widget.render sig -->\n"
            "<!-- frob:describes src/a.py::Widget.render doc -->\n",
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        ref = "src/a.py::Widget.render"
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, [ref]).danger_ok
        facets = {e.facet for e in acked.entries}
        assert facets == {"sig", "doc", "body"}

    def test_acknowledge_skips_meaningless_body_facet_on_class(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        # G5 (T-0402): `digest.py`'s `body` facet is a constant empty-tuple
        # hash for class/const/type symbols (they have no body_tokens), so
        # acking `body` on a class can never observe drift. Reverting the
        # `_BODY_FACET_MEANINGLESS_KINDS` skip makes this record a `body`
        # entry for the class ref.
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        _write(
            tmp_path,
            "docs/x.md",
            "# X\n\n<!-- frob:describes src/a.py::Widget body -->\n",
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        ref = "src/a.py::Widget"
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, [ref]).danger_ok
        assert acked.entries == ()

    def test_acknowledge_unknown_ref_is_err(self, tmp_path: Path) -> None:
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        result = acknowledge(lock, snap, ["src/a.py::NoSuchSymbol"])
        assert result.is_err
        assert result.danger_err == LockError.UnknownRef

    def test_acknowledge_endpoint_that_does_not_resolve_is_err(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        # A doc anchor is an edge endpoint (the `frob:doc` edge's target)
        # but is not itself a symbol ref -- `resolve` must fail on it even
        # though `_edge_endpoints` includes it, exercising the
        # record_result.is_err branch distinct from the "not an endpoint
        # at all" branch above.
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        result = acknowledge(lock, snap, ["docs/x.md#widget"])
        assert result.is_err
        assert result.danger_err == LockError.UnknownRef

    def test_write_lock_deterministic(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::write_lock
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, ["src/a.py::Widget.render"]).danger_ok
        path = tmp_path / "frob.lock"
        write_lock(acked, path)
        first = path.read_bytes()
        write_lock(acked, path)
        second = path.read_bytes()
        assert first == second
        assert first.endswith(b"\n")

    def test_write_lock_is_atomic(self, tmp_path: Path, monkeypatch) -> None:
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, ["src/a.py::Widget.render"]).danger_ok
        path = tmp_path / "frob.lock"

        calls: list[tuple[str, str]] = []
        real_replace = __import__("os").replace

        def spy_replace(src: str, dst: str) -> None:
            calls.append((src, dst))
            real_replace(src, dst)

        monkeypatch.setattr("frob.graph.lock.os.replace", spy_replace)
        result = write_lock(acked, path)
        assert result.is_ok
        assert len(calls) == 1
        assert Path(calls[0][1]) == path

    def test_write_lock_oserror_on_replace_is_write_failed(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/graph/lock.py::write_lock
        # Drives the OSError except-branch: `os.replace` failing (e.g. a
        # cross-device rename or permission error) must surface as
        # LockError.WriteFailed, not propagate the raw OSError.
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, ["src/a.py::Widget.render"]).danger_ok
        path = tmp_path / "frob.lock"

        def fail_replace(src: str, dst: str) -> None:
            raise OSError("simulated replace failure")

        monkeypatch.setattr("frob.graph.lock.os.replace", fail_replace)
        result = write_lock(acked, path)
        assert result.is_err
        assert result.danger_err == LockError.WriteFailed


class TestLoadLock:
    def test_missing_file_is_empty_lock(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::load_lock
        result = load_lock(tmp_path / "frob.lock")
        assert result.is_ok
        assert result.danger_ok.entries == ()

    def test_malformed_json_is_err(self, tmp_path: Path) -> None:
        path = tmp_path / "frob.lock"
        path.write_text("{not json")
        result = load_lock(path)
        assert result.is_err
        assert result.danger_err == LockError.Malformed
