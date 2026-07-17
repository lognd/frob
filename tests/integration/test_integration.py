"""
Integration tests: multiple frob modules working together.

These test the realistic agentic workflow sequences described in
docs/agentic-workflow.md.
"""

import pytest

from frob.cycle.graph import DependencyGraph, find_cycles
from frob.map import map_project
from frob.outline import outline_file
from frob.xref import xref

# ---------------------------------------------------------------------------
# Fixture: a small multi-file Python project with a real cycle
# ---------------------------------------------------------------------------


@pytest.fixture
def mini_project(tmp_path):
    """
    Structure:
      core.py     defines CoreClass, imports from utils.py
      utils.py    defines helper(), imports from core.py  <- cycle!
      main.py     imports from core.py, uses CoreClass
    """
    (tmp_path / "core.py").write_text(
        "from utils import helper\n\n"
        "class CoreClass:\n"
        "    def run(self) -> str:\n"
        "        return helper(42)\n"
    )
    (tmp_path / "utils.py").write_text(
        "from core import CoreClass\n\ndef helper(x: int) -> str:\n    return str(x)\n"
    )
    (tmp_path / "main.py").write_text(
        "from core import CoreClass\n\n"
        "if __name__ == '__main__':\n"
        "    CoreClass().run()\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# map + outline: structural understanding pipeline
# ---------------------------------------------------------------------------


def test_map_then_outline_consistency(mini_project):
    """Symbols in map output should match outline output for each file."""
    proj_map = map_project(mini_project)
    for node in proj_map.files:
        path = mini_project / node.path
        ol_result = outline_file(path)
        assert ol_result.is_ok, f"outline failed for {node.path}"
        ol = ol_result.danger_ok
        outline_symbols = {f.name for f in ol.functions} | {c.name for c in ol.classes}
        for sym in node.symbols:
            assert sym in outline_symbols, (
                f"{sym} in map but not in outline for {node.path}"
            )


def test_map_total_lines_matches_file_sum(mini_project):
    proj_map = map_project(mini_project)
    for node in proj_map.files:
        path = mini_project / node.path
        actual_lines = path.read_bytes().count(b"\n") + 1
        assert node.lines == actual_lines


# ---------------------------------------------------------------------------
# outline + xref: find a symbol then confirm xref agrees on location
# ---------------------------------------------------------------------------


def test_outline_line_matches_xref_definition(mini_project):
    """outline and xref should agree on the line number of a definition."""
    core = mini_project / "core.py"
    ol = outline_file(core).danger_ok
    cls = next(c for c in ol.classes if c.name == "CoreClass")

    xr = xref("CoreClass", mini_project).danger_ok
    assert xr.definition is not None
    assert xr.definition.line == cls.line


# ---------------------------------------------------------------------------
# xref: blast radius before a change
# ---------------------------------------------------------------------------


def test_xref_finds_all_callers(mini_project):
    """xref('CoreClass') should find usages in both main.py and utils.py."""
    xr = xref("CoreClass", mini_project).danger_ok
    usage_files = {u.file for u in xr.usages}
    assert any("main.py" in f for f in usage_files)
    # utils imports CoreClass too
    assert any("utils.py" in f for f in usage_files)


# ---------------------------------------------------------------------------
# cycle detection on a real import graph
# ---------------------------------------------------------------------------


def test_cycle_detected_in_mini_project(mini_project):
    from frob.ast import python as _py
    from frob.ast.common import ModuleTag

    graph = DependencyGraph()
    for path in mini_project.glob("*.py"):
        rel = path.name
        graph.add_node(rel)
        try:
            for imp in _py.get_imports(ModuleTag(rel), mini_project):
                graph.add_edge(rel, imp)
        except Exception:
            pass

    cycles = find_cycles(graph)
    assert len(cycles) >= 1
    cycle_nodes = set()
    for c in cycles:
        cycle_nodes.update(c)
    assert "core.py" in cycle_nodes or "utils.py" in cycle_nodes
