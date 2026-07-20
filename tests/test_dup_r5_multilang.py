"""R5 real control-flow edges across grammars, not Python-only (T-0196).

Before this ticket, `_find_block`/`_statement_ids` only recognized
Python's own tree-sitter node labels ("block", "assignment"), so every
other `frob.lang` grammar silently fell to `_build_dataflow_graph` (the
co-occurrence proxy) even when `frob.lang.symbol_tree` had real structure
available. `_BLOCK_LABELS`/`_ASSIGNMENT_LABELS`/`_DECLARATOR_LABELS`
(src/frob/dup/_pipeline.py) widen that match to rust/typescript/tsx/c/cpp,
verified directly against each grammar's real tree-sitter parse tree (see
the constants' docstrings) -- these tests exercise `_real_dataflow_graph`
against `frob.lang.symbol_tree` output for a real small function per
grammar, confirming the real path fires (returns a graph, not `None`) and
correctly separates "def" from "use", not just that a `block`-like node
was found.

The Python case is a no-regression check (it already worked before this
ticket); the unrecognized-grammar case confirms `_find_block` still
honestly returns `None` (real fallback to the proxy) rather than guessing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import _core as dup_core
from frob.dup._pipeline import _find_block, _real_dataflow_graph
from frob.lang import symbol_tree
from frob.lang._models import TreeNode

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)


def _write(tmp_path: Path, name: str, source: str) -> Path:
    """Write `source` to `tmp_path/name` and return the path (test helper)."""
    path = tmp_path / name
    path.write_text(source)
    return path


class TestRealDataflowGraphPerGrammar:
    """`_real_dataflow_graph` fires (real path, not `None`) with correct
    def/use separation for every grammar `_BLOCK_LABELS` names."""

    def test_python_block_still_matches(self, tmp_path):
        # frob:tests src/frob/dup/_pipeline.py::_real_dataflow_graph kind="unit"
        path = _write(tmp_path, "m.py", "def add(a, b):\n    c = a + b\n    return c\n")
        tree = symbol_tree(path, (1, 3)).danger_ok
        block = _find_block(tree)
        assert block is not None and block.label == "block"
        graph = _real_dataflow_graph(tree)
        assert graph is not None
        adjacency, labels = graph
        assert "def" in labels and "use" in labels
        assert adjacency

    # frob:waive DUP001 reason="parallel test methods within \
    # test_dup_r5_multilang.py (4 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_rust_block_matches_and_labels_def_use(self, tmp_path):
        # frob:tests src/frob/dup/_pipeline.py::_real_dataflow_graph kind="unit"
        path = _write(
            tmp_path,
            "m.rs",
            "fn add(a: i32, b: i32) -> i32 {\n    let c = a + b;\n    return c;\n}\n",
        )
        tree = symbol_tree(path, (1, 4)).danger_ok
        block = _find_block(tree)
        assert block is not None and block.label == "block"
        graph = _real_dataflow_graph(tree)
        assert graph is not None
        adjacency, labels = graph
        assert "def" in labels and "use" in labels
        assert adjacency

    # frob:waive DUP001 reason="parallel test methods within \
    # test_dup_r5_multilang.py (4 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_typescript_statement_block_matches_and_labels_def_use(self, tmp_path):
        # frob:tests src/frob/dup/_pipeline.py::_real_dataflow_graph kind="unit"
        path = _write(
            tmp_path,
            "m.ts",
            "function add(a: number, b: number): number {\n"
            "    let c = a + b;\n"
            "    return c;\n"
            "}\n",
        )
        tree = symbol_tree(path, (1, 4)).danger_ok
        block = _find_block(tree)
        assert block is not None and block.label == "statement_block"
        graph = _real_dataflow_graph(tree)
        assert graph is not None
        adjacency, labels = graph
        assert "def" in labels and "use" in labels
        assert adjacency

    # frob:waive DUP001 reason="parallel test methods within \
    # test_dup_r5_multilang.py (4 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_c_compound_statement_matches_and_labels_def_use(self, tmp_path):
        # frob:tests src/frob/dup/_pipeline.py::_real_dataflow_graph kind="unit"
        path = _write(
            tmp_path,
            "m.c",
            "int add(int a, int b) {\n    int c = a + b;\n    return c;\n}\n",
        )
        tree = symbol_tree(path, (1, 4)).danger_ok
        block = _find_block(tree)
        assert block is not None and block.label == "compound_statement"
        graph = _real_dataflow_graph(tree)
        assert graph is not None
        adjacency, labels = graph
        assert "def" in labels and "use" in labels
        assert adjacency

    # frob:waive DUP001 reason="parallel test methods within \
    # test_dup_r5_multilang.py (4 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_cpp_compound_statement_matches_and_labels_def_use(self, tmp_path):
        # frob:tests src/frob/dup/_pipeline.py::_real_dataflow_graph kind="unit"
        path = _write(
            tmp_path,
            "m.cpp",
            "int add(int a, int b) {\n    int c = a + b;\n    return c;\n}\n",
        )
        tree = symbol_tree(path, (1, 4)).danger_ok
        block = _find_block(tree)
        assert block is not None and block.label == "compound_statement"
        graph = _real_dataflow_graph(tree)
        assert graph is not None
        adjacency, labels = graph
        assert "def" in labels and "use" in labels
        assert adjacency


class TestRealDataflowGraphHonestFallback:
    """`_find_block`/`_real_dataflow_graph` return `None` (real fallback to
    `_build_dataflow_graph`, never a guess) for a subtree whose grammar is
    not (yet) in `_BLOCK_LABELS`."""

    def test_unrecognized_grammar_label_returns_none(self):
        # frob:tests src/frob/dup/_pipeline.py::_real_dataflow_graph kind="unit"
        unknown_tree = TreeNode(
            label="function_item",
            children=(TreeNode(label="body_expr", children=()),),
        )
        assert _find_block(unknown_tree) is None
        assert _real_dataflow_graph(unknown_tree) is None
