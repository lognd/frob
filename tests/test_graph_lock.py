"""Tests for frob.graph.lock -- acknowledgement and drift (docs/modules/graph.md)."""

# frob:waive OPAQUE001 reason="T-1038: every setattr(...) in this file is \
# monkeypatch-style test isolation (pytest fixtures reassigning a module/object \
# attribute by a name the test itself constructs) -- deliberate test infrastructure, \
# not an evasion risk over untrusted input"

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from frob.graph import GraphError, build_graph
from frob.graph import cache as graph_cache
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


# frob:ticket T-1423
class TestCacheLockRetry:
    """`_with_lock_retry` (T-1423) must retry a contended cache write/read
    instead of letting `sqlite3.OperationalError("database is locked")`
    escape, and must convert an exhausted retry budget into `CacheLocked`
    rather than the bare sqlite exception."""

    # frob:tests src/frob/graph/cache.py::_with_lock_retry
    def test_retries_then_succeeds_past_a_transient_lock(
        self, monkeypatch
    ) -> None:
        calls = {"n": 0}

        def _flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise sqlite3.OperationalError("database is locked")
            return "ok"

        monkeypatch.setattr(graph_cache, "_LOCK_POLL_SECONDS", 0.01)
        result = graph_cache._with_lock_retry(_flaky, what="test-op")
        assert result == "ok"
        assert calls["n"] == 3

    # frob:tests src/frob/graph/cache.py::_with_lock_retry
    def test_raises_cache_locked_once_budget_exhausted(self, monkeypatch) -> None:
        def _always_locked() -> None:
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(graph_cache, "_LOCK_POLL_SECONDS", 0.01)
        monkeypatch.setattr(graph_cache, "_LOCK_TOTAL_TIMEOUT_SECONDS", 0.03)
        try:
            graph_cache._with_lock_retry(_always_locked, what="test-op")
        except graph_cache.CacheLocked:
            pass
        else:
            raise AssertionError("expected CacheLocked to be raised")

    # frob:tests src/frob/graph/cache.py::_with_lock_retry
    def test_non_locked_operational_error_is_not_retried(self) -> None:
        def _other_error() -> None:
            raise sqlite3.OperationalError("disk I/O error")

        try:
            graph_cache._with_lock_retry(_other_error, what="test-op")
        except sqlite3.OperationalError as exc:
            assert not isinstance(exc, graph_cache.CacheLocked)
        else:
            raise AssertionError("expected the original OperationalError to propagate")

    # frob:tests src/frob/graph/cache.py::store_file_data
    def test_store_file_data_retries_past_a_held_exclusive_lock(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Two real sqlite connections on the same file, one holding an
        exclusive write lock while the other retries -- the honest
        reproduction the ticket asks for, not just a monkeypatched op."""
        cache = tmp_path / "cache.db"
        conn = graph_cache.connect(cache)
        blocker = sqlite3.connect(str(cache), timeout=0.1, check_same_thread=False)
        blocker.execute("BEGIN IMMEDIATE")
        blocker.execute("INSERT INTO meta (key, value) VALUES ('x', '1')")

        monkeypatch.setattr(graph_cache, "_LOCK_POLL_SECONDS", 0.05)
        monkeypatch.setattr(graph_cache, "_LOCK_TOTAL_TIMEOUT_SECONDS", 2.0)

        def _release_after_delay() -> None:
            time.sleep(0.2)
            blocker.commit()
            blocker.close()

        releaser = threading.Thread(target=_release_after_delay)
        releaser.start()
        try:
            graph_cache.store_file_data(
                conn,
                file_path="a.py",
                content_hash="deadbeef",
                symbols=(),
                edges=(),
                malformed=(),
            )
            conn.commit()
        finally:
            releaser.join()
            conn.close()

    # frob:tests src/frob/graph/build_graph
    def test_build_graph_reports_err_instead_of_crashing_on_cache_locked(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        root = tmp_path / "repo"
        root.mkdir()
        cache = tmp_path / "cache.db"

        def _always_locked(path):  # noqa: ANN001, ARG001
            raise graph_cache.CacheLocked("database is locked")

        monkeypatch.setattr(graph_cache, "connect", _always_locked)
        result = build_graph(root, cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheLocked
