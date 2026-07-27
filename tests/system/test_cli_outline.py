"""
End-to-end tests for `frob outline`.
All tests run the real CLI via subprocess and assert exact output structure.
"""

import json

import pytest

from tests.system.conftest import PY_FIXTURE, run

CPP_FIXTURE = """\
#include <vector>

class Widget {
public:
    void draw(int x, int y);
    int width() const;
};

void Widget::draw(int x, int y) {
    return;
}

int Widget::width() const {
    return 0;
}
"""


@pytest.fixture
def py_src(tmp_path):
    p = tmp_path / "sample.py"
    p.write_text(PY_FIXTURE)
    return p


@pytest.fixture
def cpp_src(tmp_path):
    p = tmp_path / "widget.cpp"
    p.write_text(CPP_FIXTURE)
    return p


@pytest.fixture
def empty_py(tmp_path):
    p = tmp_path / "empty.py"
    p.write_text("")
    return p


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_code_zero_on_valid_python(py_src):
    r = run("outline", str(py_src))
    assert r.returncode == 0


def test_exit_code_zero_on_valid_cpp(cpp_src):
    r = run("outline", str(cpp_src))
    assert r.returncode == 0


def test_exit_nonzero_unsupported_extension(tmp_path):
    f = tmp_path / "script.rb"
    f.write_text("def foo; end\n")
    r = run("outline", str(f))
    assert r.returncode != 0


def test_exit_nonzero_nonexistent_file(tmp_path):
    r = run("outline", str(tmp_path / "does_not_exist.py"))
    assert r.returncode != 0


def test_empty_file_exits_zero(empty_py):
    r = run("outline", str(empty_py))
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# Text output - Python
# ---------------------------------------------------------------------------


def test_text_contains_helper(py_src):
    r = run("outline", str(py_src))
    assert "helper" in r.stdout


def test_text_contains_another(py_src):
    r = run("outline", str(py_src))
    assert "another" in r.stdout


def test_text_contains_myclass(py_src):
    r = run("outline", str(py_src))
    assert "MyClass" in r.stdout


def test_text_contains_other(py_src):
    r = run("outline", str(py_src))
    assert "Other" in r.stdout


def test_text_shows_helper_at_line_4(py_src):
    r = run("outline", str(py_src))
    # helper is defined at line 4 in the fixture
    assert "[L4]" in r.stdout


def test_text_shows_another_at_line_7(py_src):
    r = run("outline", str(py_src))
    assert "[L7]" in r.stdout


def test_text_shows_myclass_at_line_11(py_src):
    r = run("outline", str(py_src))
    assert "[L11]" in r.stdout


def test_text_shows_line_number_format(py_src):
    r = run("outline", str(py_src))
    assert "[L" in r.stdout


def test_empty_file_output_no_symbols(empty_py):
    r = run("outline", str(empty_py))
    assert "helper" not in r.stdout
    assert "class" not in r.stdout


# ---------------------------------------------------------------------------
# JSON output - Python
# ---------------------------------------------------------------------------


def test_json_exit_code_zero(py_src):
    r = run("outline", str(py_src), "--json")
    assert r.returncode == 0


def test_json_is_valid(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert isinstance(data, dict)


def test_json_has_functions_key(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert "functions" in data


def test_json_has_classes_key(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert "classes" in data


# frob:waive DUP001 reason="parallel CLI system-test scaffolding: independent commands \
# sharing the subprocess-dispatch arrange-act shape; extracting would obscure \
# per-command intent"
def test_json_functions_have_required_fields(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    for fn in data["functions"]:
        assert "name" in fn
        assert "line" in fn
        assert "signature" in fn


def test_json_helper_at_line_4(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    helper = next(f for f in data["functions"] if f["name"] == "helper")
    assert helper["line"] == 4


def test_json_another_at_line_7(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    another = next(f for f in data["functions"] if f["name"] == "another")
    assert another["line"] == 7


def test_json_helper_signature(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    helper = next(f for f in data["functions"] if f["name"] == "helper")
    assert "-> str" in helper["signature"]
    assert "x: int" in helper["signature"]


def test_json_myclass_has_methods(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    classes_by_name = {c["name"]: c for c in data["classes"]}
    myclass = classes_by_name["MyClass"]
    assert "methods" in myclass
    method_names = {m["name"] for m in myclass["methods"]}
    assert "process" in method_names
    assert "_private" in method_names


def test_json_other_has_method(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    classes_by_name = {c["name"]: c for c in data["classes"]}
    other = classes_by_name["Other"]
    method_names = {m["name"] for m in other["methods"]}
    assert "method" in method_names


def test_json_myclass_at_line_11(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    classes_by_name = {c["name"]: c for c in data["classes"]}
    myclass = classes_by_name["MyClass"]
    assert myclass["line"] == 11


def test_json_process_method_line(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    classes_by_name = {c["name"]: c for c in data["classes"]}
    myclass = classes_by_name["MyClass"]
    methods_by_name = {m["name"]: m for m in myclass["methods"]}
    process = methods_by_name["process"]
    assert process["line"] == 12


def test_json_exactly_two_functions(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert len(data["functions"]) == 2


def test_json_exactly_two_classes(py_src):
    r = run("outline", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert len(data["classes"]) == 2


# ---------------------------------------------------------------------------
# JSON output - C++
# ---------------------------------------------------------------------------


def test_cpp_json_exit_code_zero(cpp_src):
    r = run("outline", str(cpp_src), "--json")
    assert r.returncode == 0


def test_cpp_json_has_classes(cpp_src):
    r = run("outline", str(cpp_src), "--json")
    data = json.loads(r.stdout)
    assert "classes" in data


def test_cpp_json_widget_class_found(cpp_src):
    r = run("outline", str(cpp_src), "--json")
    data = json.loads(r.stdout)
    class_names = {c["name"] for c in data["classes"]}
    assert "Widget" in class_names


def test_cpp_json_widget_out_of_line_methods(cpp_src):
    # C++ out-of-line definitions (Widget::draw, Widget::width) appear as
    # top-level functions with qualified names, not inside the class methods list.
    r = run("outline", str(cpp_src), "--json")
    data = json.loads(r.stdout)
    fn_names = {f["name"] for f in data["functions"]}
    assert "Widget::draw" in fn_names
    assert "Widget::width" in fn_names


# ---------------------------------------------------------------------------
# txt extension (unsupported)
# ---------------------------------------------------------------------------


def test_txt_extension_exits_nonzero(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("some text\n")
    r = run("outline", str(f))
    assert r.returncode != 0
