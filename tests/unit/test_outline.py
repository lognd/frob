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


# ---------------------------------------------------------------------------
# Parse-failure and privacy/doc-rendering branches (T-1302)
# ---------------------------------------------------------------------------


def test_py_outline_parse_failed_when_source_over_size_cap(tmp_path):
    # frob:tests src/frob/outline/__init__.py::outline_file kind="unit"
    # A file over frob.lang's 8 MiB size cap makes `parse_file` return
    # `Err(LangError.FileTooLarge)` -- a non-UnsupportedLanguage error --
    # which exercises `_parse_for_outline`'s "any other LangError maps to
    # OutlineError.ParseFailed" branch and `outline_file`'s own
    # `parsed_pair.is_err` propagation branch, distinct from the
    # UnsupportedLanguage path `test_unsupported_language` covers.
    f = tmp_path / "huge.py"
    f.write_bytes(b"x = 1\n" * (2 * 1024 * 1024))  # well over 8 MiB
    result = outline_file(f)
    assert result.is_err
    assert result.danger_err == OutlineError.ParseFailed


def test_py_outline_as_text_hides_private_and_shows_docs(tmp_path):
    # frob:tests src/frob/outline/__init__.py::ModuleOutline.as_text kind="unit"
    # Exercises the private-function/private-class/private-method hidden
    # branches of `_functions_as_text`/`_classes_as_text`, plus the
    # `fn.doc`/`m.doc` doc-line-append branches -- none of which the
    # existing docstring-free py_sample fixture reaches.
    src = (
        b'"""module doc."""\n'
        b"def visible(x: int) -> str:\n"
        b'    """Visible function doc."""\n'
        b"    return str(x)\n"
        b"\n"
        b"def _hidden():\n"
        b"    pass\n"
        b"\n"
        b"class Visible:\n"
        b"    def method(self):\n"
        b'        """Visible method doc."""\n'
        b"        pass\n"
        b"\n"
        b"    def _hidden_method(self):\n"
        b"        pass\n"
        b"\n"
        b"class _Hidden:\n"
        b"    def anything(self):\n"
        b"        pass\n"
    )
    f = tmp_path / "priv.py"
    f.write_bytes(src)
    outline = outline_file(f).danger_ok

    default_text = outline.as_text()
    assert "visible" in default_text
    assert "Visible function doc." in default_text
    assert "Visible method doc." in default_text
    assert "_hidden" not in default_text
    assert "_Hidden" not in default_text
    assert "private -- use --all to show" in default_text

    full_text = outline.as_text(include_private=True)
    assert "_hidden" in full_text
    assert "_Hidden" in full_text
    assert "_hidden_method" in full_text
    assert "private -- use --all to show" not in full_text


def test_py_outline_nested_class_method_has_no_top_level_owner(tmp_path):
    # frob:tests src/frob/outline/__init__.py::outline_file kind="unit"
    # `_build_classes` only tracks TOP-LEVEL classes (qualname has no "."),
    # so a method on a nested class has an owner qualname `_assign_functions`
    # cannot resolve -- exercises the `cls is not None` branch's False side
    # (the method is silently dropped, not crashed on) instead of always
    # hitting the True/found side every other outline test exercises.
    src = (
        b"class Outer:\n"
        b"    class Inner:\n"
        b"        def nested_method(self):\n"
        b"            pass\n"
        b"\n"
        b"    def outer_method(self):\n"
        b"        pass\n"
    )
    f = tmp_path / "nested.py"
    f.write_bytes(src)
    outline = outline_file(f).danger_ok
    names = {c.name for c in outline.classes}
    assert names == {"Outer"}
    outer = next(c for c in outline.classes if c.name == "Outer")
    method_names = {m.name for m in outer.methods}
    assert "outer_method" in method_names
    assert "nested_method" not in method_names


def test_py_outline_doc_with_no_period_uses_80_char_fallback(tmp_path):
    # frob:tests src/frob/outline/__init__.py::outline_file kind="unit"
    # A docstring with no "." at all exercises `_first_doc_line`'s
    # `0 < idx < 80` False branch (idx == -1 here), falling through to the
    # first-80-chars truncation instead of the sentence-split path every
    # other outline test's dot-terminated docstrings take.
    long_no_period = "x" * 120
    src = (
        f'def f():\n    """{long_no_period}"""\n    pass\n'.encode()
    )
    f = tmp_path / "nodoc_period.py"
    f.write_bytes(src)
    outline = outline_file(f).danger_ok
    fn = next(fn for fn in outline.functions if fn.name == "f")
    assert fn.doc == long_no_period[:80]
    assert len(fn.doc) == 80


def test_py_outline_dedupes_repeated_import_root(tmp_path):
    # frob:tests src/frob/outline/__init__.py::outline_file kind="unit"
    # Two imports sharing the same top-level dotted segment ("os") exercise
    # `_dedupe_imports`'s "already seen -- skip" branch, not just its
    # first-time-append branch.
    src = b"import os\nimport os.path\n\ndef f():\n    pass\n"
    f = tmp_path / "dup_imports.py"
    f.write_bytes(src)
    outline = outline_file(f).danger_ok
    assert outline.imports.count("os") == 1
