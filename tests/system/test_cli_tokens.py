"""
End-to-end tests for `frob tokens`.
"""

import json

import pytest

from tests.system.conftest import PY_FIXTURE, run


@pytest.fixture
def py_src(tmp_path):
    p = tmp_path / "sample.py"
    p.write_text(PY_FIXTURE)
    return p


@pytest.fixture
def empty_py(tmp_path):
    p = tmp_path / "empty.py"
    p.write_text("")
    return p


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_zero(py_src):
    r = run("tokens", str(py_src))
    assert r.returncode == 0


def test_empty_file_exit_zero(empty_py):
    r = run("tokens", str(empty_py))
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_stdout_contains_tokens_word(py_src):
    r = run("tokens", str(py_src))
    assert "tokens" in r.stdout.lower() or "tok" in r.stdout


def test_stdout_contains_number(py_src):
    import re

    r = run("tokens", str(py_src))
    assert re.search(r"\d+", r.stdout)


# ---------------------------------------------------------------------------
# --detail flag
# ---------------------------------------------------------------------------


def test_detail_exit_zero(py_src):
    r = run("tokens", str(py_src), "--detail")
    assert r.returncode == 0


def test_detail_shows_function_name(py_src):
    r = run("tokens", str(py_src), "--detail")
    assert "helper" in r.stdout or "MyClass" in r.stdout


# ---------------------------------------------------------------------------
# --json flag
# ---------------------------------------------------------------------------


def test_json_exit_zero(py_src):
    r = run("tokens", str(py_src), "--json")
    assert r.returncode == 0


def test_json_is_valid(py_src):
    r = run("tokens", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert isinstance(data, dict)


def test_json_has_total_tokens(py_src):
    r = run("tokens", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert "total_tokens" in data


def test_json_total_tokens_is_positive(py_src):
    r = run("tokens", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert isinstance(data["total_tokens"], int)
    assert data["total_tokens"] > 0


def test_json_has_files_list(py_src):
    r = run("tokens", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert "files" in data
    assert isinstance(data["files"], list)


def test_json_files_nonempty(py_src):
    r = run("tokens", str(py_src), "--json")
    data = json.loads(r.stdout)
    assert len(data["files"]) >= 1


def test_json_empty_file_total_minimal(empty_py):
    r = run("tokens", str(empty_py), "--json")
    data = json.loads(r.stdout)
    # tokenizer has small overhead; empty file produces near-zero count
    assert data["total_tokens"] <= 5


# ---------------------------------------------------------------------------
# Multiple files
# ---------------------------------------------------------------------------


def test_multiple_files_exit_zero(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("def foo(): pass\n")
    b.write_text("def bar(): pass\n")
    r = run("tokens", str(a), str(b))
    assert r.returncode == 0


def test_multiple_files_json_total_is_sum(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    content = "def foo(x: int) -> int:\n    return x + 1\n"
    a.write_text(content)
    b.write_text(content)
    ra = run("tokens", str(a), "--json")
    rb = run("tokens", str(b), "--json")
    rab = run("tokens", str(a), str(b), "--json")
    ta = json.loads(ra.stdout)["total_tokens"]
    tb = json.loads(rb.stdout)["total_tokens"]
    tab = json.loads(rab.stdout)["total_tokens"]
    assert tab == ta + tb


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------


def test_directory_json_sums_all_py_files(tmp_path):
    for i in range(3):
        (tmp_path / f"m{i}.py").write_text(
            f"def func_{i}(x: int) -> int:\n    return x + {i}\n"
        )
    r = run("tokens", str(tmp_path), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["total_tokens"] > 0
    assert len(data["files"]) == 3
