"""Unit tests for frob.lang's shared primitives and path-based helpers.

Covers the language-agnostic tree-sitter helpers in `frob.lang._common`,
the tree-based walkers in `frob.lang._extract`, and the path-based public
wrappers in `frob.lang.__init__` (docs/modules/lang.md's Primitives / Extraction
API sections). Node-based helpers are exercised against a real tree-sitter
parse obtained via `raw_tree`, so the assertions reflect actual grammar
output rather than a hand-built stub.
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import (
    child_by_field,
    cpp_function_nodes,
    extract_imports,
    iter_identifiers,
    language_for_extension,
    node_text,
    raw_tree,
    resolve_local_import,
    supported_extensions,
    symbol_tree,
    tree_sitter_extensions,
)
from frob.lang._common import (
    _canonical_tokens,
    _child_text,
    _collapse_ws,
    _iter_cpp_functions,
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
    _strip_comment_delims,
    export_tree,
    flatten_tree,
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

# T-0334: the same accumulator-with-clamp logic as
# tests/fixtures/dup_cross_lang's python/typescript pair (T-0198's litmus),
# kept inline here so `_canonical_tokens`'s cross-grammar claim is verified
# directly against the two grammars' real body node, not just eyeballed.
_ACCUM_PY = (
    "def compute_total(items):\n"
    "    total = 0\n"
    "    for item in items:\n"
    "        total = total + item\n"
    "        if total > 1000:\n"
    "            total = 1000\n"
    "    return total\n"
)

_ACCUM_TS = (
    "function computeTotal(items) {\n"
    "    let total = 0;\n"
    "    for (const item of items) {\n"
    "        total = total + item;\n"
    "        if (total > 1000) {\n"
    "            total = 1000;\n"
    "        }\n"
    "    }\n"
    "    return total;\n"
    "}\n"
)


def _py_tree(tmp_path: Path):
    path = tmp_path / "sample.py"
    path.write_text(_PY)
    return raw_tree(path).danger_ok


def _cpp_tree(tmp_path: Path):
    path = tmp_path / "sample.cpp"
    path.write_text(_CPP)
    return raw_tree(path).danger_ok


def _first_function_body(tmp_path: Path, name: str, source: str):
    """`_canonical_tokens`-ready body node of `source`'s first top-level
    function/def, for whichever grammar `name`'s extension dispatches to."""
    path = tmp_path / name
    path.write_text(source)
    tree, _source, language = raw_tree(path).danger_ok
    comment_types = (
        frozenset({"comment"})
        if language != "rust"
        else frozenset({"line_comment", "block_comment"})
    )
    fn = next(
        n
        for n in tree.root_node.children
        if n.type in ("function_definition", "function_declaration", "function_item")
    )
    body = fn.child_by_field_name("body")
    return body, comment_types


def test_collapse_ws_flattens_whitespace():
    # frob:tests src/frob/lang/_common.py::_collapse_ws kind="unit"
    assert _collapse_ws("  a\n\t b   c ") == "a b c"


def test_strip_comment_delims_handles_each_style():
    # frob:tests src/frob/lang/_common.py::_strip_comment_delims kind="unit"
    assert _strip_comment_delims("// hi") == "hi"
    assert _strip_comment_delims("/// hi") == "hi"
    assert _strip_comment_delims("# hi") == "hi"
    # delimiters (and continuation `*`) are stripped; interior whitespace is
    # left for the caller's _collapse_ws, so a two-line block joins with the
    # residual leading space preserved.
    assert _strip_comment_delims("/** a\n * b */") == "a  b"


def test_leaf_tokens_are_formatting_insensitive(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::_leaf_tokens kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    tokens = _leaf_tokens(tree.root_node, COMMENT_TYPES["python"])
    assert "def" in tokens and "greet" in tokens
    # the leading comment is a comment-typed leaf and must be excluded
    assert "# a leading comment" not in tokens


def test_span_of_is_one_based_inclusive(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::_span_of kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    start, end = _span_of(fn)
    assert start == 5  # `def greet` is the 5th line
    assert end >= start


def test_child_text_decodes_and_tolerates_none(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::_child_text kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    assert _child_text(fn.child_by_field_name("name")) == "greet"
    assert _child_text(None) == ""


def test_child_by_field_and_node_text_public_wrappers(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::child_by_field kind="unit"
    # frob:tests src/frob/lang/_nodes.py::child_by_field kind="unit"
    # frob:tests src/frob/lang/_nodes.py::node_text kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    name_node = child_by_field(fn, "name")
    assert node_text(name_node) == "greet"
    assert child_by_field(fn, "no-such-field") is None
    assert node_text(None) == ""


def test_leading_doc_comment_gathers_block(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::_leading_doc_comment kind="unit"
    tree, _src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    assert _leading_doc_comment(fn, COMMENT_TYPES["python"]) == "a leading comment"


def test_export_tree_and_flatten_tree_round_trip(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::export_tree kind="unit"
    # frob:tests src/frob/lang/_common.py::flatten_tree kind="unit"
    tree, src, _lang = _py_tree(tmp_path)
    fn = next(n for n in tree.root_node.children if n.type == "function_definition")
    node = export_tree(fn, COMMENT_TYPES["python"])
    labels, parents = flatten_tree(node)
    assert labels[0] == "function_definition"
    assert parents[0] == -1
    assert len(labels) == len(parents) >= 2
    assert all(0 <= parents[i] < i for i in range(1, len(parents)))

    # span carries the real tree-sitter byte offsets, not a placeholder.
    assert node.span == (fn.start_byte, fn.end_byte)
    start, end = node.span
    assert start < end
    assert src[start:end] == fn.text
    assert src[start:end].startswith(b"def greet(name):")
    # every child's span nests inside the parent's, and is itself well-formed.
    for child in node.children:
        c_start, c_end = child.span
        assert c_start < c_end
        assert start <= c_start and c_end <= end


def test_iter_cpp_functions_finds_free_and_member(tmp_path: Path):
    # frob:tests src/frob/lang/_common.py::_iter_cpp_functions kind="unit"
    tree, _src, _lang = _cpp_tree(tmp_path)
    names = {name for _node, name in _iter_cpp_functions(tree.root_node)}
    assert "add" in names
    assert "Widget::render" in names


def test_cpp_function_nodes_public_wrapper(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::cpp_function_nodes kind="unit"
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

    # TreeNode.span is real source byte offsets: unswapped, and slicing the
    # original source by it reproduces the function's exact literal text.
    start, end = node.span
    assert start < end
    source_bytes = _PY.encode("utf-8")
    covered = source_bytes[start:end].decode("utf-8")
    assert covered == ('def greet(name):\n    """Say hi."""\n    return name')


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


def test_supported_extensions_includes_tree_sitter_and_strata():
    # frob:tests src/frob/lang/__init__.py::supported_extensions kind="unit"
    exts = supported_extensions()
    assert ".py" in exts
    assert ".strata" in exts


def test_tree_sitter_extensions_excludes_strata():
    # frob:tests src/frob/lang/__init__.py::tree_sitter_extensions kind="unit"
    exts = tree_sitter_extensions()
    assert ".py" in exts
    assert ".strata" not in exts
    assert exts < supported_extensions()


def test_language_for_extension_covers_every_supported_extension():
    # frob:tests src/frob/lang/__init__.py::language_for_extension kind="unit"
    assert language_for_extension(".py") == "python"
    assert language_for_extension(".PY") == "python"
    assert language_for_extension(".strata") == "strata"
    assert language_for_extension(".nope") is None


def test_resolve_local_import_maps_to_repo_relative(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    root = tmp_path
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("x = 1\n")
    resolved = resolve_local_import("pkg.mod", "python", file_dir=root, root=root)
    assert resolved == "pkg/mod.py"
    assert resolve_local_import("os", "python", file_dir=root, root=root) is None


def test_resolve_local_import_python_package_init_branch(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # Exercises the second `suffix` candidate (`/__init__.py`) -- the
    # specifier names a package directory, not a bare module file.
    root = tmp_path
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("x = 1\n")
    resolved = resolve_local_import("pkg", "python", file_dir=root, root=root)
    assert resolved == "pkg/__init__.py"


def test_resolve_local_import_src_layout_absolute(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # T-2195: an absolute specifier (`pkg.mod`) must resolve under a
    # pyproject.toml-declared source root (`src/`), not just bare `root` --
    # the dominant real-world layout this repo itself uses.
    root = tmp_path
    (root / "pyproject.toml").write_text(
        '[tool.setuptools]\npackages = { find = { where = ["src"] } }\n'
    )
    pkg = root / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text("x = 1\n")
    resolved = resolve_local_import("pkg.mod", "python", file_dir=root, root=root)
    assert resolved == "src/pkg/mod.py"


def test_resolve_local_import_relative_sibling(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # T-2195: `from . import _land` / `from ._land import X` -- a single
    # leading dot resolves against the importer's OWN directory, no
    # pyproject.toml lookup required.
    root = tmp_path
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "_land.py").write_text("x = 1\n")
    resolved = resolve_local_import("._land", "python", file_dir=pkg, root=root)
    assert resolved == "pkg/_land.py"


def test_resolve_local_import_relative_bare_dot_is_package_init(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # T-2195: `from . import x` alone (bare `.` specifier, no trailing
    # module name) resolves to the importer's own `__init__.py`.
    root = tmp_path
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("x = 1\n")
    resolved = resolve_local_import(".", "python", file_dir=pkg, root=root)
    assert resolved == "pkg/__init__.py"


def test_resolve_local_import_relative_parent(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # T-2195: `from ..lang._nodes import X` -- two leading dots walk up one
    # directory from the importer before resolving the rest of the path.
    root = tmp_path
    (root / "lang").mkdir()
    (root / "lang" / "_nodes.py").write_text("x = 1\n")
    importer_dir = root / "tickets"
    importer_dir.mkdir()
    resolved = resolve_local_import(
        "..lang._nodes", "python", file_dir=importer_dir, root=root
    )
    assert resolved == "lang/_nodes.py"


def test_resolve_local_import_third_party_still_none(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # T-2195 regression guard: a genuinely third-party import must NOT
    # start resolving just because source-root discovery widened -- only
    # `os` was checked before this ticket; `pytest`/`tomllib` cover the
    # exact names the ticket calls out as must-still-fail controls.
    root = tmp_path
    (root / "pyproject.toml").write_text(
        '[tool.setuptools]\npackages = { find = { where = ["src"] } }\n'
    )
    (root / "src").mkdir()
    assert resolve_local_import("pytest", "python", file_dir=root, root=root) is None
    assert resolve_local_import("tomllib", "python", file_dir=root, root=root) is None


def test_resolve_local_import_scripts_fleet_status_still_resolves(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # T-2195 regression guard: the one absolute form that already worked
    # (a bare toplevel package under `root`, no src-layout declared at
    # all) must keep resolving unchanged.
    root = tmp_path
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "fleet_status.py").write_text("x = 1\n")
    resolved = resolve_local_import(
        "scripts.fleet_status", "python", file_dir=root, root=root
    )
    assert resolved == "scripts/fleet_status.py"


def test_resolve_local_import_cpp_resolves_relative_to_file_dir(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # Exercises the c/cpp branch's happy path: a real, in-root header
    # resolved relative to the including file's own directory.
    root = tmp_path
    sub = root / "src"
    sub.mkdir()
    (sub / "helper.h").write_text("// header\n")
    resolved = resolve_local_import("helper.h", "cpp", file_dir=sub, root=root)
    assert resolved == "src/helper.h"


def test_resolve_local_import_cpp_outside_root_is_none(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # Exercises the c/cpp branch's ValueError path: a specifier that
    # escapes `root` (relative_to raises) resolves to None, not a raise.
    root = tmp_path / "root"
    root.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    resolved = resolve_local_import(
        "../missing.h", "c", file_dir=outside_dir, root=root
    )
    assert resolved is None


def test_resolve_local_import_unknown_language_is_none(tmp_path: Path):
    # frob:tests src/frob/lang/_nodes.py::resolve_local_import kind="unit"
    # Exercises the trailing `return None` for a language the function
    # does not special-case at all.
    assert (
        resolve_local_import("anything", "rust", file_dir=tmp_path, root=tmp_path)
        is None
    )


class TestCanonicalTokensCrossGrammarVocabulary:
    """T-0334: `_canonical_tokens` is the primitive `RawSymbol.body_norm`
    delegates to (see each `_walk_*.py`'s `body_norm=_canonical_tokens(...)`
    call sites) -- these tests exercise it directly against real
    tree-sitter parses, the same way this file's other primitive tests do,
    rather than through `body_tokens`-only assertions that say nothing
    about the new vocabulary path."""

    # frob:tests src/frob/lang/_common.py::_canonical_tokens kind="unit"
    def test_shares_structural_tags_across_python_and_typescript(
        self, tmp_path: Path
    ) -> None:
        """The T-0198 litmus's own accumulator-with-clamp logic, expressed
        once in each grammar: `body_tokens` shares nothing across the pair
        (that is the whole T-0198 finding) but `body_norm` must share the
        control-flow/comparison vocabulary that makes the two bodies
        structurally the same shape."""
        py_body, py_comments = _first_function_body(tmp_path, "accum.py", _ACCUM_PY)
        ts_body, ts_comments = _first_function_body(tmp_path, "accum.ts", _ACCUM_TS)
        py_norm = _canonical_tokens(py_body, py_comments)
        ts_norm = _canonical_tokens(ts_body, ts_comments)

        # the T-0198 finding: body_tokens do not share the keyword/
        # punctuation vocabulary that would let R1-R3 bucket the pair
        # together -- neither `for`/`in`'s block-open colon nor `for`/`of`'s
        # brace survives across the grammars (still true, this diff never
        # touches body_tokens).
        py_tokens = set(_leaf_tokens(py_body, py_comments))
        ts_tokens = set(_leaf_tokens(ts_body, ts_comments))
        assert ":" in py_tokens and ":" not in ts_tokens
        assert "{" in ts_tokens and "{" not in py_tokens
        assert "of" in ts_tokens and "of" not in py_tokens

        # the T-0334 fix: body_norm shares the structural vocabulary a
        # cross-language R1-R3 bucketing rework would need.
        shared = {"FOR_KW", "ITER_KW", "IF_KW", "CMP_OP", "RETURN_KW"}
        assert shared <= set(py_norm)
        assert shared <= set(ts_norm)
        assert shared <= (set(py_norm) & set(ts_norm))

    # frob:tests src/frob/lang/_common.py::_canonical_tokens kind="unit"
    def test_identifier_and_literal_renaming_does_not_change_body_norm(
        self, tmp_path: Path
    ) -> None:
        """Two structurally identical functions, differing only in their
        variable name and literal value, must fingerprint identically under
        `body_norm` -- the whole point of collapsing identifier/literal
        leaves to `IDENT`/`LIT` is that renaming/reliteralizing must not
        break a structural match."""
        a_body, comments = _first_function_body(
            tmp_path,
            "a.py",
            "def f():\n    total = 0\n    return total\n",
        )
        b_body, _comments = _first_function_body(
            tmp_path,
            "b.py",
            "def g():\n    accumulator = 999\n    return accumulator\n",
        )
        assert _canonical_tokens(a_body, comments) == _canonical_tokens(
            b_body, comments
        )
        # body_tokens, by contrast, DOES change -- proves the abstraction is
        # actually doing something, not just two already-identical bodies.
        assert _leaf_tokens(a_body, comments) != _leaf_tokens(b_body, comments)

    # frob:tests src/frob/lang/_common.py::_canonical_tokens kind="unit"
    def test_unmapped_keyword_falls_back_to_other_tag(self, tmp_path: Path) -> None:
        """A construct neither `_CANONICAL_VOCAB` nor the identifier/literal
        tables recognize (python's `with`/`as`) must degrade to a distinct
        `OTHER:<node.type>` tag rather than being dropped or crashing."""
        body, comments = _first_function_body(
            tmp_path,
            "with_stmt.py",
            'def f():\n    with open("x") as fh:\n        return fh\n',
        )
        norm = _canonical_tokens(body, comments)
        assert "OTHER:with" in norm
        assert "OTHER:as" in norm
        # a recognized leaf right alongside the unmapped ones still maps
        # normally -- the fallback is per-leaf, not file-wide.
        assert "RETURN_KW" in norm

    # frob:tests src/frob/lang/_common.py::_canonical_tokens kind="unit"
    def test_deterministic_and_reformatting_insensitive(self, tmp_path: Path) -> None:
        """Same source parsed twice yields identical `body_norm` (pure
        function of the tree), and reflowing whitespace/indentation changes
        neither `body_tokens` nor `body_norm` -- the same formatting-
        insensitivity guarantee `TestFormattingInsensitivity` (test_lang.py)
        already locks in for `body_tokens`, extended to the new field."""
        source = "def f(x):\n    if x > 0:\n        return x\n    return 0\n"
        reformatted = "def f( x ):\n\n    if x > 0:\n\n        return x\n    return 0\n"

        body1, comments = _first_function_body(tmp_path, "d1.py", source)
        body2, _ = _first_function_body(tmp_path, "d2.py", source)
        assert _canonical_tokens(body1, comments) == _canonical_tokens(body2, comments)

        reflowed_body, _ = _first_function_body(tmp_path, "d3.py", reformatted)
        assert _canonical_tokens(body1, comments) == _canonical_tokens(
            reflowed_body, comments
        )
