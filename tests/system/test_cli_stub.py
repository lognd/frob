"""
End-to-end tests for `frob stub`.
"""

import pytest

from tests.system.conftest import PY_FIXTURE, run


@pytest.fixture
def py_src(tmp_path):
    p = tmp_path / "sample.py"
    p.write_text(PY_FIXTURE)
    return p


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_zero_on_valid_target(py_src):
    r = run("stub", str(py_src), "helper")
    assert r.returncode == 0


def test_exit_nonzero_nonexistent_target(py_src):
    r = run("stub", str(py_src), "nonexistent_function")
    assert r.returncode != 0


def test_exit_nonzero_nonexistent_file(tmp_path):
    r = run("stub", str(tmp_path / "missing.py"), "helper")
    assert r.returncode != 0


def test_exit_nonzero_stderr_message(py_src):
    r = run("stub", str(py_src), "nonexistent_function")
    assert r.returncode != 0
    assert r.stderr.strip() != ""


# ---------------------------------------------------------------------------
# helper function stub
# ---------------------------------------------------------------------------


def test_helper_body_present(py_src):
    r = run("stub", str(py_src), "helper")
    assert 'return str(x) + "hello"' in r.stdout


def test_helper_signature_present(py_src):
    r = run("stub", str(py_src), "helper")
    assert "def helper(x: int) -> str:" in r.stdout


def test_helper_does_not_contain_another_body(py_src):
    r = run("stub", str(py_src), "helper")
    assert "do_something" not in r.stdout


def test_helper_does_not_contain_do_more(py_src):
    r = run("stub", str(py_src), "helper")
    assert "do_more" not in r.stdout


def test_helper_other_functions_stubbed_with_ellipsis(py_src):
    r = run("stub", str(py_src), "helper")
    assert "..." in r.stdout


# ---------------------------------------------------------------------------
# MyClass.process method stub
# ---------------------------------------------------------------------------


def test_method_target_exit_zero(py_src):
    r = run("stub", str(py_src), "MyClass.process")
    assert r.returncode == 0


def test_method_body_present(py_src):
    r = run("stub", str(py_src), "MyClass.process")
    assert "return data.decode().splitlines()" in r.stdout


def test_method_other_method_stubbed(py_src):
    r = run("stub", str(py_src), "MyClass.process")
    # _private body should not appear
    assert "do_something" not in r.stdout
    assert "do_more" not in r.stdout


# ---------------------------------------------------------------------------
# --output flag
# ---------------------------------------------------------------------------


def test_output_file_created(py_src, tmp_path):
    out = tmp_path / "out.py"
    r = run("stub", str(py_src), "helper", "--output", str(out))
    assert r.returncode == 0
    assert out.exists()


def test_output_file_has_correct_content(py_src, tmp_path):
    out = tmp_path / "out.py"
    run("stub", str(py_src), "helper", "--output", str(out))
    content = out.read_text()
    assert 'return str(x) + "hello"' in content


def test_output_file_has_stubs(py_src, tmp_path):
    out = tmp_path / "out.py"
    run("stub", str(py_src), "helper", "--output", str(out))
    content = out.read_text()
    assert "..." in content
