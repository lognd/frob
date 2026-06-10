"""
End-to-end tests for `frob bundle`.
"""

import json
from pathlib import Path

import pytest

from tests.system.conftest import PY_FIXTURE, run

UTILS_PY = """\
def compute(x: int) -> int:
    return x * 2

def helper_util(s: str) -> str:
    return s.strip()
"""

MAIN_PY = """\
from utils import compute

def run(n: int) -> int:
    return compute(n) + 1

def other_run(n: int) -> int:
    return compute(n) - 1
"""


@pytest.fixture
def py_src(tmp_path):
    p = tmp_path / "sample.py"
    p.write_text(PY_FIXTURE)
    return p


@pytest.fixture
def multi_file_project(tmp_path):
    (tmp_path / "utils.py").write_text(UTILS_PY)
    (tmp_path / "main.py").write_text(MAIN_PY)
    return tmp_path


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_zero_valid_target(py_src):
    r = run("bundle", str(py_src), "helper")
    assert r.returncode == 0


def test_exit_nonzero_target_not_found(py_src):
    r = run("bundle", str(py_src), "nonexistent_func")
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_stdout_contains_focus_header(py_src):
    r = run("bundle", str(py_src), "helper")
    assert "FOCUS" in r.stdout


def test_stdout_contains_target_body(py_src):
    r = run("bundle", str(py_src), "helper")
    assert 'return str(x) + "hello"' in r.stdout


def test_stdout_contains_target_signature(py_src):
    r = run("bundle", str(py_src), "helper")
    assert "def helper" in r.stdout


def test_stdout_other_functions_stubbed(py_src):
    r = run("bundle", str(py_src), "helper")
    # other functions should be stubbed with ...
    assert "..." in r.stdout
    # their bodies should not appear
    assert "do_something" not in r.stdout


def test_multi_file_run_target_exit_zero(multi_file_project):
    main_py = multi_file_project / "main.py"
    r = run("bundle", str(main_py), "run")
    assert r.returncode == 0


def test_multi_file_run_contains_focus(multi_file_project):
    main_py = multi_file_project / "main.py"
    r = run("bundle", str(main_py), "run")
    assert "FOCUS" in r.stdout


def test_multi_file_run_body_present(multi_file_project):
    main_py = multi_file_project / "main.py"
    r = run("bundle", str(main_py), "run")
    assert "return compute(n) + 1" in r.stdout


def test_multi_file_dependency_compute_present(multi_file_project):
    main_py = multi_file_project / "main.py"
    r = run("bundle", str(main_py), "run")
    assert "compute" in r.stdout


# ---------------------------------------------------------------------------
# --depth flag
# ---------------------------------------------------------------------------


def test_depth_0_no_import_sections(py_src):
    r = run("bundle", str(py_src), "helper", "--depth", "0")
    assert r.returncode == 0
    # depth 0 means no dependency inlining
    assert "FOCUS" in r.stdout


# ---------------------------------------------------------------------------
# --format json
# ---------------------------------------------------------------------------


def test_json_format_exit_zero(py_src):
    r = run("bundle", str(py_src), "helper", "--format", "json")
    assert r.returncode == 0


def test_json_format_is_valid(py_src):
    r = run("bundle", str(py_src), "helper", "--format", "json")
    data = json.loads(r.stdout)
    assert isinstance(data, dict)


def test_json_has_target_field(py_src):
    r = run("bundle", str(py_src), "helper", "--format", "json")
    data = json.loads(r.stdout)
    assert "target" in data
    assert data["target"] == "helper"


def test_json_has_sections_field(py_src):
    r = run("bundle", str(py_src), "helper", "--format", "json")
    data = json.loads(r.stdout)
    assert "sections" in data
    assert isinstance(data["sections"], list)


def test_json_focus_section_present(py_src):
    r = run("bundle", str(py_src), "helper", "--format", "json")
    data = json.loads(r.stdout)
    roles = [s["role"] for s in data["sections"]]
    assert "focus" in roles


def test_json_focus_section_contains_body(py_src):
    r = run("bundle", str(py_src), "helper", "--format", "json")
    data = json.loads(r.stdout)
    focus = next(s for s in data["sections"] if s["role"] == "focus")
    assert 'return str(x) + "hello"' in focus["content"]


def test_json_has_total_tokens(py_src):
    r = run("bundle", str(py_src), "helper", "--format", "json")
    data = json.loads(r.stdout)
    assert "total_tokens" in data
    assert data["total_tokens"] > 0
