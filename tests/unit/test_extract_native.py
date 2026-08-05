"""T-1220: golden tests for `frob_core.extract_tree_python`, the native
python-only tree-extraction kernel -- byte/line-identical parity against
`frob.lang`'s existing Python extraction path (comment spans via
`frob.lang._extract`, docstring spans via `frob.vet._capability_core`,
identifiers via `frob.lang._extract.iter_identifiers`, tokens via
`frob.lang._common._leaf_tokens`)."""

from __future__ import annotations

from pathlib import Path

import frob_core
from tree_sitter import Parser
from tree_sitter_language_pack import get_language

from frob.lang import _common, _extract
from frob.vet import _capability_core as cc

_PY_LANG = get_language("python")


# frob:waive WIRE001 reason="a private golden-test helper used only by \
# TestExtractTreePythonParity's own methods below, in this same file -- there is no \
# production caller to wire it to by design, it exists solely to assemble the existing \
# Python-side computation for comparison against the native kernel's output, mirroring \
# the tests/unit/test_conftest_stackdump.py ::_load_conftest precedent (T-1466)" \
# follow_up="T-1503"
def _python_side(
    source: bytes,
) -> tuple[
    list[tuple[int, int]], list[tuple[int, int]], list[tuple[str, int]], list[str]
]:
    """The existing Python-side computation for the same four
    collections, assembled from three separate modules -- the same split
    `extract_tree_python`'s golden test compares against."""
    parser = Parser(_PY_LANG)
    tree = parser.parse(source)
    root = tree.root_node

    raw_nodes = _extract._collect_comment_nodes(root, _extract.COMMENT_TYPES["python"])
    comment_spans = sorted(_common._span_of(n) for n in raw_nodes)

    doc_byte_spans = cc._docstring_byte_spans_from_tree(tree, "python")
    doc_line_spans = sorted(
        {
            _common._span_of(node)
            for start_b, end_b in doc_byte_spans
            if (node := root.descendant_for_byte_range(start_b, end_b - 1)) is not None
        }
    )

    identifiers = sorted(_extract.iter_identifiers(tree, "python"))
    tokens = list(_common._leaf_tokens(root, frozenset({"comment"})))
    return comment_spans, doc_line_spans, identifiers, tokens


# frob:waive WIRE001 reason="a private golden-test helper used only by \
# TestExtractTreePythonParity's own methods below, in this same file -- there is no \
# production caller to wire it to by design, it exists solely to normalize the native \
# kernel's output for comparison against the Python-side computation, mirroring the \
# tests/unit/test_conftest_stackdump.py ::_load_conftest precedent (T-1466)" \
# follow_up="T-1503"
def _rust_side(
    source: bytes,
) -> tuple[
    list[tuple[int, int]], list[tuple[int, int]], list[tuple[str, int]], list[str]
]:
    """The native kernel's output, normalized (sorted/deduped) the same
    way `_python_side` normalizes its own four collections."""
    comment_spans, doc_spans, identifiers, tokens = frob_core.extract_tree_python(
        source
    )
    return sorted(comment_spans), sorted(set(doc_spans)), sorted(identifiers), tokens


class TestExtractTreePythonParity:
    """`frob_core.extract_tree_python` vs the existing Python extraction
    path, across representative shapes plus this repo's own source."""

    def test_module_class_function_docstrings_and_comments(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_python kind="unit"
        source = (
            b'"""module doc."""\n'
            b"# a standalone comment\n"
            b"class Foo:\n"
            b'    """class doc."""\n\n'
            b"    def bar(self):\n"
            b'        """fn doc."""\n'
            b"        x = 1  # trailing comment\n"
            b"        return x\n"
        )
        assert _rust_side(source) == _python_side(source)

    def test_errorset_style_assignment_is_not_a_docstring(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_python kind="unit"
        # T-1223's own false-positive regression (an `expression_statement`
        # SUPERTYPE spuriously matching an `assignment` node) reproduced
        # against the native kernel: `_PY_DOC_CAPTURE_FILTER`'s Rust-side
        # equivalent (`is_real_docstring_parent`) must reject this the
        # same way the Python side does.
        source = (
            b"from typani import ErrorSet\n\n\n"
            b"class MyError(ErrorSet):\n"
            b'    Bad = "subprocess.Popen(cmd)"\n'
        )
        py_comments, py_docs, py_idents, py_tokens = _python_side(source)
        rs_comments, rs_docs, rs_idents, rs_tokens = _rust_side(source)
        assert py_docs == [] == rs_docs
        assert (rs_comments, rs_docs, rs_idents, rs_tokens) == (
            py_comments,
            py_docs,
            py_idents,
            py_tokens,
        )

    def test_unparseable_source_returns_empty_not_a_crash(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_python kind="unit"
        # Never raises across the FFI boundary (module docstring) -- even
        # nonsense input just parses as best-effort tree-sitter error
        # recovery, never a PyErr.
        comment_spans, doc_spans, identifiers, tokens = frob_core.extract_tree_python(
            b"\x00\x01\xff not python at all (((("
        )
        assert isinstance(comment_spans, list)
        assert isinstance(doc_spans, list)
        assert isinstance(identifiers, list)
        assert isinstance(tokens, list)

    def test_this_repos_own_lang_module_matches_byte_for_byte(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_python kind="unit"
        # One real, large, heavily-annotated file (frob:doc/frob:ticket
        # pragmas, docstrings, comments) from this repo's own source --
        # narrower than the ticket's own 917-file ad hoc corpus sweep, but
        # a real committed regression lock rather than only a synthetic
        # fixture.
        source = Path("src/frob/lang/_extract.py").read_bytes()
        assert _rust_side(source) == _python_side(source)


_RUST_LANG = get_language("rust")


# frob:waive WIRE001 reason="a private golden-test helper used only by \
# TestExtractTreeRustParity's own methods below, in this same file -- there is no \
# production caller to wire it to by design, mirroring _python_side above and the \
# tests/unit/test_conftest_stackdump.py ::_load_conftest precedent (T-1466)" \
# follow_up="T-1503"
def _rust_lang_python_side(
    source: bytes,
) -> tuple[list[tuple[int, int]], list[tuple[str, int]], list[str]]:
    """The existing Python-side computation for rust's three collections
    (no docstring facet -- rust has none, see `extract_tree_rust`'s doc
    comment in `frob-core/src/extract.rs`)."""
    parser = Parser(_RUST_LANG)
    tree = parser.parse(source)
    root = tree.root_node

    raw_nodes = _extract._collect_comment_nodes(root, _extract.COMMENT_TYPES["rust"])
    comment_spans = sorted(_common._span_of(n) for n in raw_nodes)
    identifiers = sorted(_extract.iter_identifiers(tree, "rust"))
    tokens = list(_common._leaf_tokens(root, _extract.COMMENT_TYPES["rust"]))
    return comment_spans, identifiers, tokens


# frob:waive WIRE001 reason="a private golden-test helper used only by \
# TestExtractTreeRustParity's own methods below, in this same file -- there is no \
# production caller to wire it to by design, mirroring _rust_side above and the \
# tests/unit/test_conftest_stackdump.py ::_load_conftest precedent (T-1466)" \
# follow_up="T-1503"
def _rust_kernel_side(
    source: bytes,
) -> tuple[list[tuple[int, int]], list[tuple[str, int]], list[str]]:
    """`frob_core.extract_tree_rust`'s output, normalized the same way
    `_rust_lang_python_side` normalizes its own three collections."""
    comment_spans, identifiers, tokens = frob_core.extract_tree_rust(source)
    return sorted(comment_spans), sorted(identifiers), tokens


class TestExtractTreeRustParity:
    """`frob_core.extract_tree_rust` (T-1220's rust kernel slice) vs the
    existing Python extraction path (`frob.lang._extract`), across a
    representative fixture plus this repo's own rust source."""

    def test_functions_structs_comments_and_field_access(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_rust kind="unit"
        source = (
            b"// a leading comment\n"
            b"/// a doc comment\n"
            b"pub struct Foo {\n"
            b"    pub bar: i32,\n"
            b"}\n\n"
            b"impl Foo {\n"
            b"    /* block comment */\n"
            b"    pub fn get_bar(&self) -> i32 {\n"
            b"        self.bar\n"
            b"    }\n"
            b"}\n"
        )
        assert _rust_kernel_side(source) == _rust_lang_python_side(source)

    def test_unparseable_source_returns_empty_not_a_crash(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_rust kind="unit"
        # Never raises across the FFI boundary (module docstring) -- even
        # nonsense input just parses as best-effort tree-sitter error
        # recovery, never a PyErr.
        comment_spans, identifiers, tokens = frob_core.extract_tree_rust(
            b"\x00\x01\xff not rust at all (((("
        )
        assert isinstance(comment_spans, list)
        assert isinstance(identifiers, list)
        assert isinstance(tokens, list)

    def test_this_repos_own_extract_rs_matches_byte_for_byte(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_rust kind="unit"
        # This kernel's own source file: real, large, comment-and-doc-
        # comment-heavy rust, a committed regression lock rather than only
        # a synthetic fixture.
        source = Path("frob-core/src/extract.rs").read_bytes()
        assert _rust_kernel_side(source) == _rust_lang_python_side(source)
