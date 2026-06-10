import pytest

from frob.ast import cpp


@pytest.fixture
def parsed(cpp_sample):
    return cpp.parse_bytes(cpp_sample)


# ---------------------------------------------------------------------------
# Structure queries
# ---------------------------------------------------------------------------


def test_get_classes(parsed):
    _, tree = parsed
    assert cpp.get_classes(tree) == ["Engine"]


def test_get_all_functions(parsed):
    _, tree = parsed
    names = cpp.get_all_functions(tree)
    assert "helper" in names
    assert "Engine::run" in names
    assert "Engine::status" in names


# ---------------------------------------------------------------------------
# Stub emission -- top-level function target
# ---------------------------------------------------------------------------


def test_stub_top_level_keeps_target(parsed):
    src, tree = parsed
    result = cpp.emit_stub(src, tree, "helper")
    assert "return;" in result


def test_stub_top_level_stubs_methods(parsed):
    src, tree = parsed
    result = cpp.emit_stub(src, tree, "helper")
    assert "i < cycles" not in result
    assert "return 0" not in result


# ---------------------------------------------------------------------------
# Stub emission -- method target
# ---------------------------------------------------------------------------


def test_stub_method_keeps_target(parsed):
    src, tree = parsed
    result = cpp.emit_stub(src, tree, "Engine::run")
    assert "i < cycles" in result


def test_stub_method_stubs_sibling(parsed):
    src, tree = parsed
    result = cpp.emit_stub(src, tree, "Engine::run")
    assert "return 0" not in result


def test_stub_method_stubs_top_level(parsed):
    src, tree = parsed
    result = cpp.emit_stub(src, tree, "Engine::run")
    assert "return;" not in result


def test_stub_preserves_signatures(parsed):
    src, tree = parsed
    result = cpp.emit_stub(src, tree, "Engine::run")
    assert "void helper(int x)" in result
    assert "int status()" in result
