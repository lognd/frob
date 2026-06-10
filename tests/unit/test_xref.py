import pytest

from frob.xref import XrefError, xref


@pytest.fixture
def py_file(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    return p


@pytest.fixture
def cpp_file(tmp_path, cpp_sample):
    p = tmp_path / "sample.cpp"
    p.write_bytes(cpp_sample)
    return p


@pytest.fixture
def py_dir(tmp_path, py_sample):
    """Two Python files: one defines helper, one calls it."""
    (tmp_path / "defn.py").write_bytes(py_sample)
    (tmp_path / "caller.py").write_text(
        "from defn import helper\n\nresult = helper(42)\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Python xref
# ---------------------------------------------------------------------------


def test_py_finds_definition(py_file):
    result = xref("helper", py_file)
    assert result.is_ok
    xr = result.danger_ok
    assert xr.definition is not None
    assert "sample.py" in xr.definition.file


def test_py_definition_correct_line(py_file, py_sample):
    xr = xref("helper", py_file).danger_ok
    src_lines = py_sample.decode().splitlines()
    assert src_lines[xr.definition.line - 1].startswith("def helper")


def test_py_finds_class_definition(py_file):
    xr = xref("MyClass", py_file).danger_ok
    assert xr.definition is not None


def test_py_usages_include_calls(py_dir):
    xr = xref("helper", py_dir).danger_ok
    files_with_usage = {u.file for u in xr.usages}
    assert any("caller.py" in f for f in files_with_usage)


def test_py_usage_context_is_line_text(py_dir):
    xr = xref("helper", py_dir).danger_ok
    caller_usages = [u for u in xr.usages if "caller.py" in u.file]
    assert any("helper" in u.context for u in caller_usages)


def test_py_missing_symbol_no_definition(py_file):
    xr = xref("nonexistent_symbol_xyz", py_file).danger_ok
    assert xr.definition is None
    assert xr.usages == []


# ---------------------------------------------------------------------------
# C++ xref
# ---------------------------------------------------------------------------


def test_cpp_finds_definition(cpp_file):
    xr = xref("helper", cpp_file).danger_ok
    assert xr.definition is not None


def test_cpp_finds_class(cpp_file):
    xr = xref("Engine", cpp_file).danger_ok
    assert xr.definition is not None or len(xr.usages) > 0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_no_files_found(tmp_path):
    result = xref("foo", tmp_path)
    assert result.is_err
    assert result.danger_err == XrefError.NoFilesFound


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def test_as_text(py_file):
    xr = xref("helper", py_file).danger_ok
    text = xr.as_text()
    assert "helper" in text
    assert "defined" in text


def test_as_json(py_file):
    import json

    xr = xref("helper", py_file).danger_ok
    data = json.loads(xr.as_json())
    assert data["symbol"] == "helper"
    assert "definition" in data
