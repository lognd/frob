"""T-2156: `build_reference_graph`'s short-name resolution is DELIBERATELY
over-inclusive (safe for its original consumer, T-0422's dead-symbol
gate) -- it wires an edge between ANY two same-named private symbols
across the whole tree, discarding the candidate's own file path. Reused
by `frob.verify._attribution` for causal reachability, that same
over-matching manufactures false attributions: a common private helper
name (`_run`, `_commit_all` -- 17/18 test files in this repo define one
independently) creates a fabricated edge between two files with no real
reference between them at all.

`build_reference_graph_module_scoped` is the fix: same extraction/
indexing, but a cross-file candidate only resolves when the caller's file
actually imports the candidate's file. This file tests ONLY the new
function; `build_reference_graph` itself is untouched and unaffected --
see `tests/test_graph.py`'s own suite for its (unaffected) coverage.
"""

from __future__ import annotations

from pathlib import Path


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestBuildReferenceGraphModuleScoped:
    # frob:tests tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped.test_does_not_cross_wire_same_named_helpers_in_unrelated_files kind="unit"  # noqa: E501
    def test_does_not_cross_wire_same_named_helpers_in_unrelated_files(
        self, tmp_path: Path
    ) -> None:
        """FAILS FIRST against current main's `build_reference_graph`
        (which DOES wire this edge -- that is the whole T-2156 incident):
        two files, each with its own private `_run` helper and no import
        relationship between them, must never resolve a caller in one to
        the OTHER file's `_run`."""
        from frob.graph.callgraph import (
            build_reference_graph,
            build_reference_graph_module_scoped,
        )

        _write(
            tmp_path,
            "tests/a.py",
            "def _run() -> None:\n    pass\n\n\ndef caller_in_a() -> None:\n    _run()\n",
        )
        _write(
            tmp_path,
            "tests/b.py",
            "def _run() -> None:\n    pass\n",
        )
        paths = ("tests/a.py", "tests/b.py")

        # Demonstrates the bug still exists in the UNTOUCHED function --
        # this is not a regression test, it is confirming the premise.
        blanket = build_reference_graph(tmp_path, paths)
        assert blanket.calls["tests/a.py::caller_in_a"] == (
            "tests/a.py::_run",
            "tests/b.py::_run",
        ), "build_reference_graph's own over-matching must be unaffected by this fix"

        scoped = build_reference_graph_module_scoped(tmp_path, paths)
        assert scoped.calls["tests/a.py::caller_in_a"] == ("tests/a.py::_run",), (
            "the module-scoped graph must resolve ONLY the same-file _run, "
            f"got {scoped.calls.get('tests/a.py::caller_in_a')!r}"
        )

    # frob:tests tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped.test_resolves_a_genuine_cross_file_import kind="unit"  # noqa: E501
    def test_resolves_a_genuine_cross_file_import(self, tmp_path: Path) -> None:
        """Safety property: a REAL cross-file reference (the caller's file
        actually imports the callee's module) must still resolve -- this
        is not a same-file-only restriction, it is an import-scoped one."""
        from frob.graph.callgraph import build_reference_graph_module_scoped

        _write(
            tmp_path,
            "pkg/_helper.py",
            "def _shared() -> None:\n    pass\n",
        )
        _write(
            tmp_path,
            "pkg/caller.py",
            "from pkg._helper import _shared\n\n\ndef entry() -> None:\n    _shared()\n",
        )
        paths = ("pkg/_helper.py", "pkg/caller.py")

        scoped = build_reference_graph_module_scoped(tmp_path, paths)
        assert scoped.calls["pkg/caller.py::entry"] == ("pkg/_helper.py::_shared",)

    # frob:tests tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped.test_same_file_candidate_always_resolves kind="unit"  # noqa: E501
    def test_same_file_candidate_always_resolves(self, tmp_path: Path) -> None:
        """The overwhelmingly common case -- an ordinary local call within
        one file -- must be completely unaffected."""
        from frob.graph.callgraph import build_reference_graph_module_scoped

        _write(
            tmp_path,
            "pkg/a.py",
            "def _helper() -> None:\n    pass\n\n\ndef entry() -> None:\n    _helper()\n",
        )
        scoped = build_reference_graph_module_scoped(tmp_path, ("pkg/a.py",))
        assert scoped.calls["pkg/a.py::entry"] == ("pkg/a.py::_helper",)
