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
    assert xr.definition is not None
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


def test_as_text_no_definition_no_usages(py_file):
    # frob:tests src/frob/xref/__init__.py::XrefResult.as_text kind="unit"
    # `definition is None` and empty `usages` exercise as_text's
    # "(not found)"/"(none found)" branches, neither of which
    # test_as_text (a found-definition, has-usages case) reaches.
    xr = xref("nonexistent_symbol_xyz", py_file).danger_ok
    text = xr.as_text()
    assert "defined:  (not found)" in text
    assert "used by: (none found)" in text


def test_as_text_cross_file_filters_and_reports_skipped(tmp_path):
    # frob:tests src/frob/xref/__init__.py::XrefResult.as_text kind="unit"
    # `cross_file=True` exercises the same-file-usage filtering branch and
    # the "N same-file usages hidden" skipped-count branch -- both
    # unreached by the default (cross_file=False) rendering path.
    (tmp_path / "defn.py").write_text(
        "def helper(x):\n    return x\n\nresult = helper(1)\n"
    )
    (tmp_path / "caller.py").write_text(
        "from defn import helper\n\nresult = helper(42)\n"
    )
    xr = xref("helper", tmp_path).danger_ok
    default_text = xr.as_text()
    cross_text = xr.as_text(cross_file=True)
    assert "used by:" in default_text
    assert "used by (cross-file):" in cross_text
    # defn.py both defines and calls helper in its own body, so filtering
    # same-file usages should report at least one hidden.
    assert "same-file usages hidden" in cross_text


# ---------------------------------------------------------------------------
# Non-tree-sitter (text-search) files and hidden-path skipping (T-1312)
# ---------------------------------------------------------------------------


def test_text_search_finds_usages_in_strata_file(tmp_path):
    # frob:tests src/frob/xref/__init__.py::xref kind="unit"
    # `.strata` is a known extension but not in `_SOURCE_EXTS`, so it
    # routes through `_search_text` (plain substring scan) instead of
    # `_search_parsed` -- exercising a code path none of the .py/.cpp
    # tests above reach at all. `_search_text` never yields a definition
    # (it has no symbol-kind awareness), only usages.
    f = tmp_path / "spec.strata"
    f.write_text("widget defines the widget contract\nuse widget here\n")
    xr = xref("widget", f).danger_ok
    assert xr.definition is None
    assert {u.line for u in xr.usages} == {1, 2}


def test_collect_source_files_skips_hidden_directory(tmp_path):
    # frob:tests src/frob/xref/__init__.py::xref kind="unit"
    # A dot-prefixed directory exercises `_collect_source_files`'s
    # `_is_hidden` skip branch -- the file inside it must never surface
    # as a definition or usage even though its extension matches.
    hidden_dir = tmp_path / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "secret.py").write_text("def helper():\n    pass\n")
    (tmp_path / "visible.py").write_text("def other():\n    pass\n")
    # An extension xref does not collect at all (`_collect_source_files`'s
    # own "wrong extension -- continue" branch, distinct from the
    # hidden-directory skip this test is otherwise about).
    (tmp_path / "notes.txt").write_text("helper mentioned here\n")
    xr = xref("helper", tmp_path).danger_ok
    assert xr.definition is None
    assert xr.usages == []
