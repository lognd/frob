import pytest

from frob.ast import python as py


@pytest.fixture
def parsed(py_sample):
    return py.parse_bytes(py_sample)


# ---------------------------------------------------------------------------
# Structure queries
# ---------------------------------------------------------------------------


def test_get_classes(parsed):
    _, tree = parsed
    assert py.get_classes(tree) == ["MyClass", "Other"]


def test_get_all_functions(parsed):
    _, tree = parsed
    assert py.get_all_functions(tree) == ["helper", "another"]


def test_get_class_functions(parsed):
    _, tree = parsed
    node = py.find_class_node(tree, "MyClass")
    assert node is not None
    assert py.get_class_functions(node) == ["process", "_private"]


# ---------------------------------------------------------------------------
# Stub emission -- top-level function target
# ---------------------------------------------------------------------------


def test_stub_top_level_keeps_target(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "helper")
    assert "return str(x)" in result


def test_stub_top_level_stubs_other_functions(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "helper")
    assert "do_something" not in result
    assert "return 42" not in result


def test_stub_top_level_stubs_methods(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "helper")
    assert "return data.decode" not in result


def test_stub_top_level_uses_ellipsis(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "helper")
    assert "..." in result


# ---------------------------------------------------------------------------
# Stub emission -- method target
# ---------------------------------------------------------------------------


def test_stub_method_keeps_target(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "MyClass.process")
    assert "return data.decode().splitlines()" in result


def test_stub_method_stubs_sibling_methods(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "MyClass.process")
    assert "do_something" not in result


def test_stub_method_stubs_top_level_functions(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "MyClass.process")
    assert "return str(x)" not in result


def test_stub_method_stubs_other_class_methods(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "MyClass.process")
    assert "return 42" not in result


def test_stub_preserves_signatures(parsed):
    src, tree = parsed
    result = py.emit_stub(src, tree, "MyClass.process")
    assert "def helper(x: int) -> str:" in result
    assert "def _private(self) -> None:" in result


def test_stub_correct_indentation(parsed):
    """Stubbed bodies must be indented to match their containing def."""
    src, tree = parsed
    result = py.emit_stub(src, tree, "MyClass.process")
    lines = result.splitlines()
    stub_lines = [l for l in lines if l.strip() == "..."]
    for line in stub_lines:
        assert line.startswith(" "), repr(line)
