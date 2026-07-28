import pytest

from frob.outline import OutlineError, outline_file


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
def rust_file(tmp_path, rust_sample):
    p = tmp_path / "sample.rs"
    p.write_bytes(rust_sample)
    return p


# ---------------------------------------------------------------------------
# Python outline
# ---------------------------------------------------------------------------


def test_py_outline_ok(py_file):
    # frob:tests src/frob/outline/__init__.py::outline_file kind="unit"
    result = outline_file(py_file)
    assert result.is_ok


def test_py_outline_lines(py_file, py_sample):
    outline = outline_file(py_file).danger_ok
    assert outline.lines == py_sample.count(b"\n") + 1


def test_py_outline_imports(py_file):
    outline = outline_file(py_file).danger_ok
    assert "os" in outline.imports
    assert "pathlib" in outline.imports


def test_py_outline_functions(py_file):
    outline = outline_file(py_file).danger_ok
    names = {f.name for f in outline.functions}
    assert "helper" in names
    assert "another" in names


def test_py_outline_classes(py_file):
    outline = outline_file(py_file).danger_ok
    names = {c.name for c in outline.classes}
    assert "MyClass" in names
    assert "Other" in names


def test_py_outline_methods(py_file):
    outline = outline_file(py_file).danger_ok
    classes_by_name = {c.name: c for c in outline.classes}
    cls = classes_by_name["MyClass"]
    method_names = {m.name for m in cls.methods}
    assert "process" in method_names
    assert "_private" in method_names


def test_py_outline_function_line(py_file, py_sample):
    outline = outline_file(py_file).danger_ok
    helper = next(f for f in outline.functions if f.name == "helper")
    # helper is the first function; check it's on the right line
    src_lines = py_sample.decode().splitlines()
    assert src_lines[helper.line - 1].startswith("def helper")


def test_py_outline_signature_includes_return(py_file):
    outline = outline_file(py_file).danger_ok
    helper = next(f for f in outline.functions if f.name == "helper")
    assert "-> str" in helper.signature


def test_py_outline_as_text(py_file):
    outline = outline_file(py_file).danger_ok
    text = outline.as_text()
    assert "helper" in text
    assert "MyClass" in text
    assert "[L" in text


def test_py_outline_as_json(py_file):
    import json

    outline = outline_file(py_file).danger_ok
    data = json.loads(outline.as_json())
    assert data["lines"] == outline.lines
    assert any(f["name"] == "helper" for f in data["functions"])


# ---------------------------------------------------------------------------
# C++ outline
# ---------------------------------------------------------------------------


def test_cpp_outline_ok(cpp_file):
    result = outline_file(cpp_file)
    assert result.is_ok


def test_cpp_outline_imports(cpp_file):
    outline = outline_file(cpp_file).danger_ok
    assert "vector" in outline.imports
    assert "local.h" in outline.imports


def test_cpp_outline_functions(cpp_file):
    outline = outline_file(cpp_file).danger_ok
    names = {f.name for f in outline.functions}
    assert "helper" in names


def test_cpp_outline_classes(cpp_file):
    outline = outline_file(cpp_file).danger_ok
    names = {c.name for c in outline.classes}
    assert "Engine" in names


def test_cpp_outline_methods(cpp_file):
    outline = outline_file(cpp_file).danger_ok
    classes_by_name = {c.name: c for c in outline.classes}
    cls = classes_by_name["Engine"]
    method_names = {m.name for m in cls.methods}
    assert "run" in method_names
    assert "status" in method_names


# ---------------------------------------------------------------------------
# Rust outline (T-0238)
# ---------------------------------------------------------------------------


def test_rust_outline_ok(rust_file):
    # frob:tests src/frob/outline/__init__.py::outline_file kind="unit"
    result = outline_file(rust_file)
    assert result.is_ok


def test_rust_outline_functions(rust_file):
    outline = outline_file(rust_file).danger_ok
    names = {f.name for f in outline.functions}
    assert "helper" in names


def test_rust_outline_classes(rust_file):
    outline = outline_file(rust_file).danger_ok
    names = {c.name for c in outline.classes}
    assert "Engine" in names


def test_rust_outline_methods(rust_file):
    outline = outline_file(rust_file).danger_ok
    classes_by_name = {c.name: c for c in outline.classes}
    cls = classes_by_name["Engine"]
    method_names = {m.name for m in cls.methods}
    assert "run" in method_names
    assert "status" in method_names


def test_rust_outline_as_text(rust_file):
    outline = outline_file(rust_file).danger_ok
    text = outline.as_text()
    assert "helper" in text
    assert "Engine" in text
    assert "[L" in text


# ---------------------------------------------------------------------------
# Unsupported language
# ---------------------------------------------------------------------------


def test_unsupported_language(tmp_path):
    f = tmp_path / "script.rb"
    f.write_text("def foo; end")
    result = outline_file(f)
    assert result.is_err
    assert result.danger_err == OutlineError.UnsupportedLanguage
