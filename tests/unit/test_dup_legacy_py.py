# frob:ticket T-0160
"""Unit tests for `frob.dup._legacy_py`'s tree-sitter-node walkers.

Drives the local-collection/serialization/function-iteration helpers
directly off a real tree-sitter `Node` (via `frob.lang.raw_tree`) so every
parameter/statement/pattern shape (splat args, tuple-unpack `for`,
multi-item `with`, nested classes/functions, string/number literal
normalization) is reachable without needing two duplicate fragments large
enough to trip `find_duplicates`'s `min_lines` threshold end-to-end.
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Node

from frob.dup._legacy_py import (
    _collect_locals_py,
    _enclosing_class_py,
    _iter_functions_py,
    _serialize_py_body,
)
from frob.lang import child_by_field as _child
from frob.lang import raw_tree

_SRC = """
def f(a, b=1, *args, **kwargs):
    x = 1
    for i, j in items:
        y = i
    with open("f") as fh, open("g") as gh:
        z = fh
    if True:
        w = 1
    while True:
        v = 1
    try:
        pass
    except Exception:
        pass
    n = 3.14
    s = "literal"
    # a comment
    return a, b, x, y, z, w, v, n, s


class C:
    def method(self, a: int, b: int = 2):
        return a + b

    def outer():
        def nested():
            pass
        return nested
"""


def _parse(tmp_path: Path):
    """Parse `_SRC` into a real tree-sitter tree, returning `(root_node,)`."""
    path = tmp_path / "mod.py"
    path.write_text(_SRC)
    tree, _source, _lang = raw_tree(path).danger_ok
    return tree.root_node


def _funcs(tmp_path: Path) -> dict[str, Node]:
    """`{qualname: func_node}` for every function in `_SRC`."""
    root = _parse(tmp_path)
    return dict((sym, node) for node, sym in _iter_functions_py(root))


# frob:tests \
# tests/unit/test_dup_legacy_py.py::test_iter_functions_py_yields_qualified_names
def test_iter_functions_py_yields_qualified_names(tmp_path: Path) -> None:
    """Top-level, method, and nested-function symbols are all yielded, with
    the method qualified by its enclosing class, and a nested closure
    qualified by the FULL enclosing class/function chain (T-1035: was
    class-only, so this would have read "C.nested" -- indistinguishable
    from a same-named closure nested in any OTHER method of C)."""
    funcs = _funcs(tmp_path)
    assert "f" in funcs
    assert "C.method" in funcs
    assert "C.outer" in funcs
    # nested function inside C.outer -- qualified by both C and outer
    assert "C.outer.nested" in funcs


# frob:tests \
# tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_none_for_top_level_function
def test_enclosing_class_py_none_for_top_level_function(tmp_path: Path) -> None:
    """A top-level function (not inside any class) has no enclosing class."""
    funcs = _funcs(tmp_path)
    assert _enclosing_class_py(funcs["f"]) is None


# frob:tests \
# tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_finds_class_for_method
def test_enclosing_class_py_finds_class_for_method(tmp_path: Path) -> None:
    """A method's enclosing class name is recovered by walking up through
    the `block` node to the `class_definition`."""
    funcs = _funcs(tmp_path)
    assert _enclosing_class_py(funcs["C.method"]) == "C"


# frob:tests \
# tests/unit/test_dup_legacy_py.py::test_collect_locals_py_covers_every_binding_shape
def test_collect_locals_py_covers_every_binding_shape(tmp_path: Path) -> None:
    """`_collect_locals_py` harvests plain/default/splat params, tuple-unpack
    `for`, multi-item `with ... as`, and assignments nested inside
    if/while/try blocks -- every binding shape `f` exercises."""
    funcs = _funcs(tmp_path)
    locals_ = _collect_locals_py(funcs["f"])
    # `with ... as <name>` binding names ARE collected: `with_item` nests
    # under a `with_clause`, and the bound name lives under
    # `as_pattern`/`as_pattern_target` (field `alias` on the `as_pattern`,
    # not on `with_item` itself) -- `_harvest_with` walks that shape.
    assert locals_ >= {
        "a",
        "b",
        "args",
        "kwargs",  # params: plain, default, *args, **kwargs
        "i",
        "j",  # for-loop tuple unpack
        "w",  # if-block assignment
        "v",  # while-block assignment
        "x",
        "y",
        "z",
        "n",
        "s",  # plain assignments
        "fh",
        "gh",  # multi-item `with ... as` bindings
    }


# frob:tests tests/unit/test_dup_legacy_py.py::test_collect_locals_py_with_tuple_target
def test_collect_locals_py_with_tuple_target(tmp_path: Path) -> None:
    """`with X as (a, b):` unpacks the tuple pattern under
    `as_pattern_target` -- both leaf names are collected, exercising
    `_harvest_with_item`'s delegation to the recursive `_harvest_pattern`
    walker (not just the single-identifier fast path)."""
    src = "def g():\n    with ctx() as (p, q):\n        return p, q\n"
    path = tmp_path / "tup.py"
    path.write_text(src)
    tree, _source, _lang = raw_tree(path).danger_ok
    funcs = dict((sym, node) for node, sym in _iter_functions_py(tree.root_node))
    assert _collect_locals_py(funcs["g"]) >= {"p", "q"}


# frob:tests \
# tests/unit/test_dup_legacy_py.py::test_collect_locals_py_method_includes_typed_defaul\
# t_param
def test_collect_locals_py_method_includes_typed_default_param(tmp_path: Path) -> None:
    """Typed and typed-default parameters (`a: int`, `b: int = 2`) are
    still recognized as local bindings via their `name` field."""
    funcs = _funcs(tmp_path)
    locals_ = _collect_locals_py(funcs["C.method"])
    assert locals_ == {"self", "a", "b"}


# frob:tests \
# tests/unit/test_dup_legacy_py.py::test_collect_locals_py_empty_for_body_with_no_bindi\
# ngs
def test_collect_locals_py_empty_for_body_with_no_bindings(tmp_path: Path) -> None:
    """A function whose body only defines a nested function has no locals
    of its own (the nested def is not itself an assignment binding)."""
    funcs = _funcs(tmp_path)
    assert _collect_locals_py(funcs["C.outer.nested"]) == set()


# frob:tests \
# tests/unit/test_dup_legacy_py.py::test_serialize_py_body_renames_locals_and_normalize\
# s_literals
def test_serialize_py_body_renames_locals_and_normalizes_literals(
    tmp_path: Path,
) -> None:
    """String and numeric literals normalize to placeholder tokens, and
    local identifiers rename to positional `_vN` slots -- comments are
    dropped entirely."""
    funcs = _funcs(tmp_path)
    node = funcs["f"]
    locals_ = _collect_locals_py(node)
    body = _child(node, "body")
    assert body is not None
    serialized = _serialize_py_body(body, locals_)
    assert "_S_" in serialized  # the "literal" string and "f"/"g" open() args
    assert "_N_" in serialized  # 3.14 and the default b=1
    assert "a comment" not in serialized
    assert "_v0" in serialized  # at least one renamed local
