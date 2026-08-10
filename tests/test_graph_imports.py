"""Tests for frob.graph.imports -- file-level resolved-import edge
substrate (docs/modules/graph.md#import-graph, T-1985)."""

from __future__ import annotations

from pathlib import Path

from frob.graph.imports import ImportGraph, UnresolvedImport, build_import_graph


# frob:ticket T-1985
def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-1985
class TestBuildImportGraph:
    def test_resolves_a_real_intra_repo_import_edge(self) -> None:
        # frob:ticket T-1985
        # frob:tests src/frob/graph/imports.py::build_import_graph
        # Real files in THIS repo: frob.graph.__init__ imports from
        # frob.graph.affects. Before this ticket's substrate existed, no
        # facility in frob.graph/frob.lang could answer this at all.
        root = Path(__file__).resolve().parents[1]
        graph = build_import_graph(
            root,
            ["src/frob/graph/__init__.py", "src/frob/graph/affects.py"],
        )
        assert isinstance(graph, ImportGraph)
        assert "src/frob/graph/affects.py" in graph.edges["src/frob/graph/__init__.py"]

    def test_dynamic_import_reports_unresolved_not_dropped(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-1985
        # frob:tests src/frob/graph/imports.py::build_import_graph
        _write(
            tmp_path,
            "pkg/dyn.py",
            "import importlib\n\nmod = importlib.import_module('pkg.other')\n",
        )
        graph = build_import_graph(tmp_path, ["pkg/dyn.py"])
        assert graph.edges == {}
        assert len(graph.unresolved) == 1
        rec = graph.unresolved[0]
        assert rec.importer == "pkg/dyn.py"
        assert rec.reason == "dynamic-import"

    def test_non_python_file_reports_unsupported_language_unresolved(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-1985
        # frob:tests src/frob/graph/imports.py::build_import_graph
        _write(tmp_path, "pkg/lib.rs", "use crate::other;\n")
        graph = build_import_graph(tmp_path, ["pkg/lib.rs"])
        assert graph.edges == {}
        assert graph.unresolved == (
            UnresolvedImport(
                importer="pkg/lib.rs", module="", reason="unsupported-language"
            ),
        )

    def test_stdlib_import_counts_as_external_not_unresolved(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-1985
        # frob:tests src/frob/graph/imports.py::build_import_graph
        _write(tmp_path, "pkg/a.py", "import os\nimport sys\n")
        graph = build_import_graph(tmp_path, ["pkg/a.py"])
        assert graph.edges == {}
        assert graph.unresolved == ()
        assert graph.external_count == 2

    def test_relative_import_resolves_within_package(self, tmp_path: Path) -> None:
        # frob:ticket T-1985
        # frob:tests src/frob/graph/imports.py::build_import_graph
        _write(tmp_path, "pkg/__init__.py", "")
        _write(tmp_path, "pkg/a.py", "from . import b\n")
        _write(tmp_path, "pkg/b.py", "")
        graph = build_import_graph(
            tmp_path, ["pkg/__init__.py", "pkg/a.py", "pkg/b.py"]
        )
        assert graph.edges["pkg/a.py"] == ("pkg/b.py",)

    def test_star_import_resolves_the_module_not_its_names(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-1985
        # frob:tests src/frob/graph/imports.py::build_import_graph
        _write(tmp_path, "pkg/a.py", "from pkg.b import *\n")
        _write(tmp_path, "pkg/b.py", "THING = 1\n")
        graph = build_import_graph(tmp_path, ["pkg/a.py", "pkg/b.py"])
        assert graph.edges["pkg/a.py"] == ("pkg/b.py",)

    def test_relative_import_inside_init_py_resolves_within_its_own_package(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-1665
        # frob:tests src/frob/graph/imports.py::build_import_graph
        # T-1665 bug fix: `_module_name_of` already collapses an
        # `__init__.py` importer to its OWN package's dotted name (it
        # strips the trailing `.__init__`) -- `_relative_module_name`
        # used to unconditionally drop one MORE component regardless,
        # over-walking a `level=1` relative import inside a package's own
        # `__init__.py` to the PARENT package instead of the importer's
        # real one. Measured in this repo: `frob._cli_parsers.__init__`'s
        # `from ._design import ...` resolved to `frob._design` (does not
        # exist) instead of `frob._cli_parsers._design` (the real file),
        # silently losing 3 real import edges and turning 3 genuinely
        # 2+-referenced CLI parser modules into false REF002s.
        _write(tmp_path, "pkg/__init__.py", "from ._sub import thing\n")
        _write(tmp_path, "pkg/_sub.py", "thing = 1\n")
        graph = build_import_graph(
            tmp_path, ["pkg/__init__.py", "pkg/_sub.py"]
        )
        assert graph.edges["pkg/__init__.py"] == ("pkg/_sub.py",)

    def test_unreadable_file_is_reported_unresolved_not_silently_skipped(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-1985
        # frob:tests src/frob/graph/imports.py::build_import_graph
        graph = build_import_graph(tmp_path, ["pkg/missing.py"])
        assert graph.edges == {}
        assert graph.unresolved == (
            UnresolvedImport(
                importer="pkg/missing.py", module="", reason="parse-error"
            ),
        )
