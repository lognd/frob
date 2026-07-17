"""Unit tests for frob.lang's shared primitives and path-based helpers.

Covers the language-agnostic tree-sitter helpers in `frob.lang._common`,
the tree-based walkers in `frob.lang._extract`, and the path-based public
wrappers in `frob.lang.__init__` (docs/lang.md's Primitives / Extraction
API sections). Node-based helpers are exercised against a real tree-sitter
parse obtained via `raw_tree`, so the assertions reflect actual grammar
output rather than a hand-built stub.
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import (
    cpp_function_nodes,
    extract_imports,
    iter_identifiers,
    raw_tree,
    resolve_local_import,
    symbol_tree,
)
from frob.lang._common import (
    child_text,
    collapse_ws,
    export_tree,
    flatten_tree,
    iter_cpp_functions,
    leading_doc_comment,
    leaf_tokens,
    span_of,
    strip_comment_delims,
)
from frob.lang._extract import COMMENT_TYPES
from frob.lang._extract import extract_imports as extract_imports_tree
from frob.lang._extract import iter_identifiers as iter_identifiers_tree

_PY = (
    "import os\n"
    "from sys import argv\n"
    "\n"
    "# a leading comment\n"
    "def greet(name):\n"
    '    """Say hi."""\n'
    "    return name\n"
)

_CPP = (
    "int add(int a, int b) { return a + b; }\n"
    "struct Widget {\n"
    "    int render() { return 0; }\n"
    "};\n"
)


def _py_tree(tmp_path: Path):
    path = tmp_path / "sample.py"
    path.write_text(_PY)
    return raw_tree(path).danger_ok


def _cpp_tree(tmp_path: Path):
    path = tmp_path / "sample.cpp"
    path.write_text(_CPP)
    return raw_tree(path).danger_ok


def test_collapse_ws_flattens_whitespace():
    # frob:tests src/frob/lang/_common.py::collapse_ws kind="unit"
    assert collapse_ws("  a\n\t b   c ") == "a b c"


def test_strip_comment_delims_handles_each_style():
    # frob:tests src/frob/lang/_common.py::strip_comment_delims kind="unit"
    assert strip_comment_delims("// hi") == "hi"
    assert strip_comment_delims("/// hi") == "hi"
    assert strip_comment_delims("# hi") == "hi"
    # delimiters (and continuation `*`) are stripped; interior whitespace is
    # left for the caller's collapse_ws, so a two-line block joins with the
    # residual leading space preserved.
    assert strip_comment_delims("/** a\n * b */") == "a  b"


def test_leaf_tokens_are_formatting_insensitive(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::leaf_tokens kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    tokens = leaf_tokens(tree.root_node, COMMENT_TYPES["python"])
    assert "def" in tokens and "greet" in tokens
    # the leading comment is a comment-typed leaf and must be excluded
    assert "# a leading comment" not in tokens


def test_span_of_is_one_based_inclusive(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::span_of kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    start, end = span_of(fn)
    assert start == 5  # `def greet` is the 5th line
    assert end >= start


def test_child_text_decodes_and_tolerates_none(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::child_text kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    assert child_text(fn.child_by_field_name("name")) == "greet"
    assert child_text(None) == ""


def test_leading_doc_comment_gathers_block(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::leading_doc_comment kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    assert leading_doc_comment(fn, COMMENT_TYPES["python"]) == "a leading comment"


def test_export_tree_and_flatten_tree_round_trip(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::export_tree kind="unit"
    # frob:tests src/frob/lang/_common.py::flatten_tree kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    node = export_tree(fn, COMMENT_TYPES["python"])
    labels, parents = flatten_tree(node)
    assert labels[0] == "function_definition"
    assert parents[0] == -1
    assert len(labels) == len(parents) >= 2
    assert all(0 <= parents[i] < i for i in range(1, len(parents)))


def test_iter_cpp_functions_finds_free_and_member(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::iter_cpp_functions kind="unit"
    tree, _src, _lang = _cpp_tree(tmp_path)
    names = {name for _node, name in iter_cpp_functions(tree.root_node)}
    assert "add" in names
    assert "Widget::render" in names


def test_cpp_function_nodes_public_wrapper(tmp_path: Path):
    # frob:tests src/frob/lang/__init__.py::cpp_function_nodes kind="unit"
    tree, _src, _lang = _cpp_tree(tmp_path)
    names = {name for _node, name in cpp_function_nodes(tree)}
    assert "add" in names and "Widget::render" in names


def test_raw_tree_returns_tree_source_language(tmp_path: Path):
    # frob:tests src/frob/lang/__init__.py::raw_tree kind="unit"
    tree, source, language = _py_tree(tmp_path)
    assert language == "python"
    assert source.startswith(b"import os")
    assert tree.root_node.type == "module"


def test_symbol_tree_covers_span(tmp_path: Path):
    # frob:tests src/frob/lang/__init__.py::symbol_tree kind="unit"
    path = tmp_path / "s.py"
    path.write_text(_PY)
    node = symbol_tree(path, (5, 7)).danger_ok
    assert node.label == "function_definition"


def test_extract_imports_tree_and_path(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_imports kind="unit"
    # frob:tests src/frob/lang/__init__.py::extract_imports kind="unit"
    tree, _src, lang = _py_tree(tmp_path)
    tree_specs = extract_imports_tree(tree, lang)
    assert any("os" in s for s in tree_specs)
    path = tmp_path / "sample.py"
    path_specs = extract_imports(path).danger_ok
    assert any("os" in s for s in path_specs)


def test_iter_identifiers_tree_and_path(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::iter_identifiers kind="unit"
    # frob:tests src/frob/lang/__init__.py::iter_identifiers kind="unit"
    tree, _src, lang = _py_tree(tmp_path)
    tree_ids = {name for name, _line in iter_identifiers_tree(tree, lang)}
    assert "greet" in tree_ids
    path = tmp_path / "sample.py"
    path_ids = {name for name, _line in iter_identifiers(path).danger_ok}
    assert "greet" in path_ids


def test_resolve_local_import_maps_to_repo_relative(tmp_path: Path):
    # frob:tests src/frob/lang/__init__.py::resolve_local_import kind="unit"
    root = tmp_path
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("x = 1\n")
    resolved = resolve_local_import("pkg.mod", "python", file_dir=root, root=root)
    assert resolved == "pkg/mod.py"
    assert resolve_local_import("os", "python", file_dir=root, root=root) is None
