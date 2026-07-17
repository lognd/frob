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
        snap = self._snapshot(tmp_path)
        ref = "src/a.py::Widget.render"
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, [ref]).danger_ok
        assert len(acked.entries) == 1
        assert acked.entries[0].facet == "sig"

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

    def test_acknowledge_unknown_ref_is_err(self, tmp_path: Path) -> None:
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        result = acknowledge(lock, snap, ["src/a.py::NoSuchSymbol"])
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
