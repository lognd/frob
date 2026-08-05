# frob:ticket T-1307
"""Unit tests for `frob.dup._legacy_cpp`'s tree-sitter-node walkers.

Mirrors `tests/unit/test_dup_legacy_py.py`'s approach for the C++ grammar:
drives the local-collection/serialization/function-iteration helpers
directly off a real tree-sitter `Node` (via `frob.lang.raw_tree`) so every
shape (params incl. pointer/reference declarators, `for`/range-for
bindings, nested control flow, string/number literal normalization,
enclosing class/struct name) is reachable without needing two duplicate
C++ fragments large enough to trip `find_duplicates`'s end-to-end
`min_lines` threshold.
"""

from __future__ import annotations

from pathlib import Path

from frob.dup._legacy_cpp import (
    _collect_locals_cpp,
    _enclosing_class_cpp,
    _iter_functions_cpp,
    _serialize_cpp_body,
)
from frob.lang import child_by_field as _child
from frob.lang import raw_tree

_SRC = """
int f(int a, int* b, int& c) {
    int x = 1;
    for (int i = 0; i < 10; i++) {
        int y = i;
    }
    for (int v : items) {
        int z = v;
    }
    if (true) {
        int w = 1;
    }
    while (true) {
        int u = 1;
    }
    try {
    } catch (...) {
    }
    double n = 3.14;
    const char* s = "literal";
    // a comment
    return a + b + c + x + y + z + w + u + n;
}

class C {
    int method(int a, int b) {
        return a + b;
    }
};
"""


def _parse(tmp_path: Path):
    """Parse `_SRC` into a real tree-sitter tree, returning the root node."""
    path = tmp_path / "mod.cpp"
    path.write_text(_SRC)
    tree, _source, _lang = raw_tree(path).danger_ok
    return tree.root_node


# frob:tests \
# tests/unit/test_dup_legacy_cpp.py::test_iter_functions_cpp_yields_qualified_names
def test_iter_functions_cpp_yields_qualified_names(tmp_path: Path) -> None:
    """Top-level and method function symbols are yielded, the method
    qualified by its enclosing class name."""
    root = _parse(tmp_path)
    funcs = dict((sym, node) for node, sym in _iter_functions_cpp(root))
    assert "f" in funcs
    assert "C.method" in funcs


# frob:tests \
# tests/unit/test_dup_legacy_cpp.py::test_enclosing_class_cpp_none_for_top_level_functi\
# on
def test_enclosing_class_cpp_none_for_top_level_function(tmp_path: Path) -> None:
    """A free function's enclosing class is None."""
    root = _parse(tmp_path)
    func_node, _sym = next((n, s) for n, s in _iter_functions_cpp(root) if s == "f")
    assert _enclosing_class_cpp(func_node) is None


# frob:tests \
# tests/unit/test_dup_legacy_cpp.py::test_enclosing_class_cpp_names_the_struct_or_class
def test_enclosing_class_cpp_names_the_struct_or_class(tmp_path: Path) -> None:
    """A method's enclosing class name is recovered via the field_declaration_list parent."""
    root = _parse(tmp_path)
    func_node, _sym = next(
        (n, s) for n, s in _iter_functions_cpp(root) if s == "C.method"
    )
    assert _enclosing_class_cpp(func_node) == "C"


# frob:tests tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_covers_bindings
def test_collect_locals_cpp_covers_bindings(tmp_path: Path) -> None:
    """For-loop and range-for bindings, plain declarations, AND function
    parameters (T-1509) are all collected as locals.

    T-1509 fix: `_collect_locals_cpp` used to look up the `parameters`
    field on `func_node` (`function_definition`) directly, but
    tree-sitter's cpp grammar puts that field on the function's
    `function_declarator` child instead -- so function PARAMETERS were
    never actually added to the local set here (unlike `_legacy_py`'s
    equivalent, which does collect params). `_cpp_function_declarator`
    now unwraps to the real `function_declarator` node first, matching
    `_cpp_func_name`'s own pointer/reference-declarator unwrap."""
    root = _parse(tmp_path)
    func_node, _sym = next((n, s) for n, s in _iter_functions_cpp(root) if s == "f")
    locals_ = _collect_locals_cpp(func_node)
    # plain declaration + for/range-for bindings
    assert "x" in locals_
    assert "i" in locals_
    assert "y" in locals_
    assert "v" in locals_
    assert "z" in locals_
    assert "n" in locals_
    # params ARE now collected, including pointer/reference declarators
    assert "a" in locals_
    assert "b" in locals_
    assert "c" in locals_


# frob:tests \
# tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_method_params_too
def test_collect_locals_cpp_method_params_too(tmp_path: Path) -> None:
    """A class method's plain (non-pointer) parameters are also collected
    as locals (T-1509) -- the fix must not be pointer/reference-only."""
    root = _parse(tmp_path)
    func_node, _sym = next(
        (n, s) for n, s in _iter_functions_cpp(root) if s == "C.method"
    )
    locals_ = _collect_locals_cpp(func_node)
    assert "a" in locals_
    assert "b" in locals_


# frob:tests \
# tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_param_folds_to_positional_\
# token
def test_collect_locals_cpp_param_folds_to_positional_token(
    tmp_path: Path,
) -> None:
    """T-1509's real detection-quality fix: two functions identical except
    for parameter NAMES now fingerprint identically, because a parameter
    identifier folds to a positional `_vN` token like every other local
    (it did not before this fix -- a raw, un-folded parameter name would
    make the serialized token strings differ between two such functions)."""
    src_a = "int f(int alpha, int beta) { return alpha + beta; }\n"
    src_b = "int f(int gamma, int delta) { return gamma + delta; }\n"

    def _serialize(src: str) -> str:
        path = tmp_path / f"{hash(src) & 0xFFFF}.cpp"
        path.write_text(src)
        tree, _source, _lang = raw_tree(path).danger_ok
        func_node, _sym = next(_iter_functions_cpp(tree.root_node))
        body = _child(func_node, "body")
        assert body is not None
        locals_ = _collect_locals_cpp(func_node)
        return _serialize_cpp_body(body, locals_)

    assert _serialize(src_a) == _serialize(src_b)


# frob:tests \
# tests/unit/test_dup_legacy_cpp.py::test_serialize_cpp_body_normalizes_locals_strings_\
# and_numbers
def test_serialize_cpp_body_normalizes_locals_strings_and_numbers(
    tmp_path: Path,
) -> None:
    """Local identifiers fold to positional `_vN` tokens, string/char
    literals fold to `_S_`, and numeric literals fold to `_N_`."""
    root = _parse(tmp_path)
    func_node, _sym = next((n, s) for n, s in _iter_functions_cpp(root) if s == "f")
    body = _child(func_node, "body")
    assert body is not None
    locals_ = _collect_locals_cpp(func_node)
    serialized = _serialize_cpp_body(body, locals_)
    assert "_S_" in serialized
    assert "_N_" in serialized
    assert "literal" not in serialized
    assert "3.14" not in serialized
    # a local identifier from a plain declaration ("x") must have been
    # replaced with a positional _vN token, not left verbatim
    assert " x " not in f" {serialized} "
