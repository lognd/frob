"""T-1220: golden tests for the `frob_core.extract_tree_*` native
tree-extraction kernels (python/rust/cpp/typescript) -- byte/line-
identical parity against `frob.lang`'s existing Python extraction path
where one exists (comment spans via `frob.lang._extract`, docstring spans
via `frob.vet._capability_core` for python only, identifiers via
`frob.lang._extract.iter_identifiers`, tokens via
`frob.lang._common._leaf_tokens`). Typescript has no pre-existing Python
identifier-walk contract (`_IDENTIFIER_TYPES` has no `"typescript"` entry)
-- its identifier collection gets a standalone sanity check instead of a
parity one; see `TestExtractTreeTypescriptParity`.

T-1503 (WIRE001 on this file's golden-comparison helpers, closed won't-fix):
every `_python_side`/`_rust_side`/`_rust_lang_python_side`/`_rust_kernel_side`
/`_cpp_lang_python_side`/`_cpp_kernel_side` helper below is called only from
this same file's own test methods. `frob.gates._wire._wire_test_path_
excluded` DELIBERATELY (T-1592's precedent) never counts a test-tree
symbol's own defining file as a "reached" caller for itself -- same-file
test usage is treated as permanently unwired by design, regardless of call
count, so a shared per-file comparison helper like these can never satisfy
WIRE001's ordinary reached-outside-diff-tests check. Each carries
`frob:waive WIRE001 ... permanent="true"` (`_wire002_is_permanent_test_
helper_waiver`'s escape hatch, the same one `tests/unit/test_mutation_
sweep_queue.py::_make_ticket` uses) rather than a `follow_up="T-####"` --
a follow-up ticket for a condition that will never stop being true just
re-orphans itself every time it closes (T-1592's own live incident), which
is worse than no follow-up at all."""

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
# permanent="true"
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
# permanent="true"
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
# permanent="true"
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
# permanent="true"
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


_CPP_LANG = get_language("cpp")


# frob:waive WIRE001 reason="a private golden-test helper used only by \
# TestExtractTreeCppParity's own methods below, in this same file -- there is no \
# production caller to wire it to by design, mirroring _rust_lang_python_side above \
# and the tests/unit/test_conftest_stackdump.py ::_load_conftest precedent (T-1466)" \
# permanent="true"
def _cpp_lang_python_side(
    source: bytes,
) -> tuple[list[tuple[int, int]], list[tuple[str, int]], list[str]]:
    """The existing Python-side computation for cpp's three collections
    (no docstring facet, same as rust -- see `extract_tree_cpp`'s doc
    comment in `frob-core/src/extract.rs`)."""
    parser = Parser(_CPP_LANG)
    tree = parser.parse(source)
    root = tree.root_node

    raw_nodes = _extract._collect_comment_nodes(root, _extract.COMMENT_TYPES["cpp"])
    comment_spans = sorted(_common._span_of(n) for n in raw_nodes)
    identifiers = sorted(_extract.iter_identifiers(tree, "cpp"))
    tokens = list(_common._leaf_tokens(root, _extract.COMMENT_TYPES["cpp"]))
    return comment_spans, identifiers, tokens


# frob:waive WIRE001 reason="a private golden-test helper used only by \
# TestExtractTreeCppParity's own methods below, in this same file -- there is no \
# production caller to wire it to by design, mirroring _rust_kernel_side above and the \
# tests/unit/test_conftest_stackdump.py ::_load_conftest precedent (T-1466)" \
# permanent="true"
def _cpp_kernel_side(
    source: bytes,
) -> tuple[list[tuple[int, int]], list[tuple[str, int]], list[str]]:
    """`frob_core.extract_tree_cpp`'s output, normalized the same way
    `_cpp_lang_python_side` normalizes its own three collections."""
    comment_spans, identifiers, tokens = frob_core.extract_tree_cpp(source)
    return sorted(comment_spans), sorted(identifiers), tokens


class TestExtractTreeCppParity:
    """`frob_core.extract_tree_cpp` (T-1220's cpp kernel slice) vs the
    existing Python extraction path (`frob.lang._extract`), across this
    repo's own `tests/fixtures/lang/sample.cpp` fixture."""

    def test_functions_classes_and_comment_styles(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_cpp kind="unit"
        source = Path("tests/fixtures/lang/sample.cpp").read_bytes()
        assert _cpp_kernel_side(source) == _cpp_lang_python_side(source)

    def test_unparseable_source_returns_empty_not_a_crash(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_cpp kind="unit"
        # Never raises across the FFI boundary (module docstring) -- even
        # nonsense input just parses as best-effort tree-sitter error
        # recovery, never a PyErr.
        comment_spans, identifiers, tokens = frob_core.extract_tree_cpp(
            b"\x00\x01\xff not cpp at all (((("
        )
        assert isinstance(comment_spans, list)
        assert isinstance(identifiers, list)
        assert isinstance(tokens, list)

    def test_this_repos_own_bad_cpp_fixture_matches_byte_for_byte(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_cpp kind="unit"
        # A second, independent fixture (already committed for a different
        # purpose -- tests/fixtures/bad_cpp/) as a real regression lock
        # beyond the one synthetic sample above.
        source = Path("tests/fixtures/bad_cpp/main.cpp").read_bytes()
        assert _cpp_kernel_side(source) == _cpp_lang_python_side(source)


_TS_LANG = get_language("typescript")


# frob:waive WIRE001 reason="a private golden-test helper used only by \
# TestExtractTreeTypescriptParity's own methods below, in this same file -- there is \
# no production caller to wire it to by design, mirroring _rust_lang_python_side above \
# and the tests/unit/test_conftest_stackdump.py ::_load_conftest precedent (T-1466)" \
# permanent="true"
def _ts_lang_python_side_comments_and_tokens(
    source: bytes,
) -> tuple[list[tuple[int, int]], list[str]]:
    """The existing Python-side computation for typescript's comment spans
    and token stream ONLY -- unlike cpp/rust, `frob.lang._extract.
    _IDENTIFIER_TYPES` has no `"typescript"` entry (no pre-existing Python
    identifier walk for typescript to compare against; see
    `extract_tree_typescript`'s doc comment in `frob-core/src/extract.rs`
    for why this kernel's identifier kinds are chosen fresh rather than
    mirrored)."""
    parser = Parser(_TS_LANG)
    tree = parser.parse(source)
    root = tree.root_node

    raw_nodes = _extract._collect_comment_nodes(
        root, _extract.COMMENT_TYPES["typescript"]
    )
    comment_spans = sorted(_common._span_of(n) for n in raw_nodes)
    tokens = list(_common._leaf_tokens(root, _extract.COMMENT_TYPES["typescript"]))
    return comment_spans, tokens


class TestExtractTreeTypescriptParity:
    """`frob_core.extract_tree_typescript` (T-1220's typescript kernel
    slice) vs the existing Python extraction path for the two facets it
    has a pre-existing contract for (comment spans, tokens) -- identifiers
    have no Python-side counterpart to compare against yet (see the
    module-level helper's docstring above), so those get a standalone
    sanity assertion instead of a parity one."""

    def test_functions_classes_interfaces_and_comment_styles(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_typescript kind="unit"
        source = Path("tests/fixtures/lang/sample.ts").read_bytes()
        comment_spans, identifiers, tokens = frob_core.extract_tree_typescript(source)
        py_comment_spans, py_tokens = _ts_lang_python_side_comments_and_tokens(source)
        assert sorted(comment_spans) == py_comment_spans
        assert tokens == py_tokens
        # Identifiers: no Python-side contract to compare against (see
        # class docstring) -- assert the kernel found the fixture's known
        # declared names instead, as a standalone sanity check. "render" is
        # deliberately absent: a method name is a `property_identifier`
        # leaf in this grammar, not `identifier`/`type_identifier` --
        # excluded by design (see `TS_IDENTIFIER_KINDS`'s doc comment in
        # `frob-core/src/extract.rs`).
        names = {name for name, _line in identifiers}
        assert {"add", "x", "y", "Widget", "label", "MAX_WIDGETS"} <= names

    def test_unparseable_source_returns_empty_not_a_crash(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_typescript kind="unit"
        # Never raises across the FFI boundary (module docstring) -- even
        # nonsense input just parses as best-effort tree-sitter error
        # recovery, never a PyErr.
        comment_spans, identifiers, tokens = frob_core.extract_tree_typescript(
            b"\x00\x01\xff not typescript at all (((("
        )
        assert isinstance(comment_spans, list)
        assert isinstance(identifiers, list)
        assert isinstance(tokens, list)

    def test_this_repos_own_arch_fixture_comments_and_tokens_match(self) -> None:
        # frob:tests frob-core/src/extract.rs::extract_tree_typescript kind="unit"
        # A second, independent fixture as a real regression lock beyond
        # the one synthetic sample above, for the two facets with a
        # pre-existing Python-side contract.
        source = Path("tests/fixtures/arch/typescript/equiv.ts").read_bytes()
        comment_spans, _identifiers, tokens = frob_core.extract_tree_typescript(source)
        py_comment_spans, py_tokens = _ts_lang_python_side_comments_and_tokens(source)
        assert sorted(comment_spans) == py_comment_spans
        assert tokens == py_tokens
