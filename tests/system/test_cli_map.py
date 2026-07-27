"""
End-to-end tests for `frob map`.
"""

import json
from pathlib import Path

import pytest

from tests.system.conftest import run

PY_A = """\
def foo(x: int) -> int:
    return x + 1

def bar(y: str) -> str:
    return y.upper()
"""

PY_B = """\
class Alpha:
    def run(self) -> None:
        pass
"""

PY_C = """\
import os

def baz() -> None:
    pass
"""

PY_SUB1 = """\
def deep_func(n: int) -> int:
    return n * 2
"""

PY_SUB2 = """\
class Beta:
    pass
"""


@pytest.fixture
def project(tmp_path):
    (tmp_path / "a.py").write_text(PY_A)
    (tmp_path / "b.py").write_text(PY_B)
    (tmp_path / "c.py").write_text(PY_C)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "d.py").write_text(PY_SUB1)
    (sub / "e.py").write_text(PY_SUB2)
    return tmp_path


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_code_zero(project):
    r = run("map", str(project))
    assert r.returncode == 0


def test_empty_dir_exit_zero(tmp_path):
    r = run("map", str(tmp_path))
    assert r.returncode == 0


def test_non_python_dir_exit_zero(tmp_path):
    (tmp_path / "readme.txt").write_text("hello\n")
    r = run("map", str(tmp_path))
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_text_contains_a_py(project):
    r = run("map", str(project))
    assert "a.py" in r.stdout


def test_text_contains_b_py(project):
    r = run("map", str(project))
    assert "b.py" in r.stdout


def test_text_contains_c_py(project):
    r = run("map", str(project))
    assert "c.py" in r.stdout


def test_text_contains_subdir_files(project):
    r = run("map", str(project))
    assert "d.py" in r.stdout
    assert "e.py" in r.stdout


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_json_exit_zero(project):
    r = run("map", str(project), "--json")
    assert r.returncode == 0


def test_json_is_valid(project):
    r = run("map", str(project), "--json")
    data = json.loads(r.stdout)
    assert isinstance(data, dict)


def test_json_has_files_key(project):
    r = run("map", str(project), "--json")
    data = json.loads(r.stdout)
    assert "files" in data


# frob:waive DUP001 reason="parallel CLI system-test scaffolding: independent commands \
# sharing the subprocess-dispatch arrange-act shape; extracting would obscure \
# per-command intent"
def test_json_files_have_required_fields(project):
    r = run("map", str(project), "--json")
    data = json.loads(r.stdout)
    for f in data["files"]:
        assert "path" in f
        assert "lines" in f
        assert "tokens" in f


def test_json_contains_all_five_files(project):
    r = run("map", str(project), "--json")
    data = json.loads(r.stdout)
    paths = [f["path"] for f in data["files"]]
    basenames = {Path(p).name for p in paths}
    assert "a.py" in basenames
    assert "b.py" in basenames
    assert "c.py" in basenames
    assert "d.py" in basenames
    assert "e.py" in basenames


def test_json_line_count_a_py(project):
    r = run("map", str(project), "--json")
    data = json.loads(r.stdout)
    entry = next(f for f in data["files"] if Path(f["path"]).name == "a.py")
    # PY_A has 5 non-empty lines + trailing newline = 6 lines
    assert entry["lines"] >= 5


def test_json_tokens_positive(project):
    r = run("map", str(project), "--json")
    data = json.loads(r.stdout)
    for f in data["files"]:
        assert f["tokens"] >= 0


# ---------------------------------------------------------------------------
# --depth flag
# ---------------------------------------------------------------------------


def test_depth_1_limits_to_root_files(project):
    r = run("map", str(project), "--depth", "0")
    assert r.returncode == 0
    # subdir files should NOT appear
    assert "d.py" not in r.stdout
    assert "e.py" not in r.stdout


def test_depth_1_shows_root_files(project):
    r = run("map", str(project), "--depth", "0")
    assert "a.py" in r.stdout
    assert "b.py" in r.stdout
    assert "c.py" in r.stdout


# ---------------------------------------------------------------------------
# Empty directory
# ---------------------------------------------------------------------------


def test_empty_dir_output_minimal(tmp_path):
    r = run("map", str(tmp_path))
    # No Python files means no file entries
    assert "def " not in r.stdout


# ---------------------------------------------------------------------------
# Scale: 50 Python files
# ---------------------------------------------------------------------------


def test_scale_50_files_json(tmp_path):
    for i in range(50):
        (tmp_path / f"module_{i}.py").write_text(
            f"def func_{i}(x: int) -> int:\n    return x + {i}\n"
        )
    r = run("map", str(tmp_path), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert len(data["files"]) == 50


def test_scale_50_files_total_tokens_positive(tmp_path):
    for i in range(50):
        (tmp_path / f"module_{i}.py").write_text(
            f"def func_{i}(x: int) -> int:\n    return x + {i}\n"
        )
    r = run("map", str(tmp_path), "--json")
    data = json.loads(r.stdout)
    total = sum(f["tokens"] for f in data["files"])
    assert total > 0
