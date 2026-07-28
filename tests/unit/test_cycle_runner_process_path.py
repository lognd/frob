"""T-1022: `_process_path`'s skip/include boolean gates (skipped-dir,
exclude-glob, extension-language match) exercised directly so mutating any
of the three `and`/`or` conditions in its body is detected, not just its
per-file crash-guard (EXHAUST001/002 burn-down evidence for the same diff
hunk). Several tests monkeypatch `_add_file_edges` to record its exact
call args -- the only externally-observable trace of which branch of each
`and`/`or` gate actually fired, since a no-op file produces the same `None`
return whether or not edges were attempted.
"""

from __future__ import annotations

from pathlib import Path

import frob.app.cycle_runner as cycle_runner_mod
from frob.app.cycle_runner import _process_path
from frob.cycle.graph import DependencyGraph


def _recording_add_file_edges(monkeypatch, calls: list) -> None:
    """Replace `_add_file_edges` with a recorder so a test can assert
    exactly which (rel, language) pairs `_process_path` decided to scan."""

    def _fake(graph, path, rel, language, scan_root):  # noqa: ANN001
        calls.append((rel, language))
        return None

    monkeypatch.setattr(cycle_runner_mod, "_add_file_edges", _fake)


class TestProcessPathGating:
    def test_file_in_skipped_dir_is_not_added(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        f = venv_dir / "mod.py"
        f.write_text("x = 1\n")
        graph = DependencyGraph()

        result = _process_path(graph, f, tmp_path, None, ())

        assert result is None
        assert set(graph.nodes) == set()

    def test_nonmatching_nonempty_exclude_globs_does_not_short_circuit(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`exclude_globs and is_excluded(...)`: a non-empty (truthy)
        `exclude_globs` that does NOT match this file must still let the
        file through. An `and` -> `or` mutation would short-circuit on the
        truthy tuple alone and wrongly skip every file the moment ANY
        exclude glob is configured, regardless of match."""
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n")
        graph = DependencyGraph()
        calls: list = []
        _recording_add_file_edges(monkeypatch, calls)

        result = _process_path(graph, f, tmp_path, "python", ("nomatch-*.py",))

        assert result is None
        assert set(graph.nodes) == {"mod.py"}
        assert calls == [("mod.py", "python")]

    def test_file_matching_exclude_glob_is_not_added(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        f = tmp_path / "generated.py"
        f.write_text("x = 1\n")
        graph = DependencyGraph()

        result = _process_path(graph, f, tmp_path, None, ("generated.py",))

        assert result is None
        assert set(graph.nodes) == set()

    def test_python_file_with_matching_lang_is_added(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n")
        graph = DependencyGraph()
        calls: list = []
        _recording_add_file_edges(monkeypatch, calls)

        result = _process_path(graph, f, tmp_path, "python", ())

        assert result is None
        assert set(graph.nodes) == {"mod.py"}
        assert calls == [("mod.py", "python")]

    def test_python_file_wrong_requested_lang_is_skipped_after_node_add(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`want_python = ext in _PY_EXTS and lang in (None, "python")`: a
        `.py` file requested under `lang="cpp"` must not be scanned as
        either language. An `and` -> `or` mutation here would wrongly turn
        `want_python` true from the extension match alone, ignoring the
        requested language."""
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n")
        graph = DependencyGraph()
        calls: list = []
        _recording_add_file_edges(monkeypatch, calls)

        result = _process_path(graph, f, tmp_path, "cpp", ())

        assert result is None
        # the node is registered before the language gate runs, but no
        # import edges are added for a language mismatch
        assert set(graph.nodes) == {"mod.py"}
        assert calls == []

    def test_cpp_file_requested_as_cpp_is_scanned_as_cpp(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`want_cpp = ext in _CPP_EXTS and lang in (None, "cpp", "c")`:
        proves the positive branch of the same `and` gate `_add_file_edges`
        is actually called with `language="cpp"`, not skipped or
        mislabeled."""
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        f = tmp_path / "mod.cpp"
        f.write_text("// c++\n")
        graph = DependencyGraph()
        calls: list = []
        _recording_add_file_edges(monkeypatch, calls)

        result = _process_path(graph, f, tmp_path, "cpp", ())

        assert result is None
        assert set(graph.nodes) == {"mod.cpp"}
        assert calls == [("mod.cpp", "cpp")]

    def test_cpp_file_requested_as_python_is_not_scanned(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`if not (want_python or want_cpp): return None` -- a `.cpp` file
        under `lang="python"` satisfies neither gate (extension rules out
        `want_python`; requested lang rules out `want_cpp`), so
        `_add_file_edges` must never be called. An `or` -> `and` mutation
        on this line would flip which side of a false/false case reaches
        the return -- this and the plain-.py-file case below together
        pin down the direction."""
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        f = tmp_path / "mod.cpp"
        f.write_text("// c++\n")
        graph = DependencyGraph()
        calls: list = []
        _recording_add_file_edges(monkeypatch, calls)

        result = _process_path(graph, f, tmp_path, "python", ())

        assert result is None
        assert set(graph.nodes) == {"mod.cpp"}
        assert calls == []

    def test_plain_python_file_default_lang_is_scanned(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`if not (want_python or want_cpp): return None` -- with
        `want_python=True`/`want_cpp=False` (a `.py` file, `lang=None`),
        the `or` must still let the file through. An `or` -> `and`
        mutation would make this case wrongly return `None` before
        scanning, since `True and False` is `False`."""
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n")
        graph = DependencyGraph()
        calls: list = []
        _recording_add_file_edges(monkeypatch, calls)

        result = _process_path(graph, f, tmp_path, None, ())

        assert result is None
        assert set(graph.nodes) == {"mod.py"}
        assert calls == [("mod.py", "python")]

    def test_unrelated_extension_is_a_node_with_no_edges(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/cycle_runner.py::_process_path kind="unit"
        f = tmp_path / "notes.strata"
        f.write_text("x\n")
        graph = DependencyGraph()

        result = _process_path(graph, f, tmp_path, None, ())

        assert result is None
        assert set(graph.nodes) == {"notes.strata"}
