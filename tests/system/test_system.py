"""
System tests: run the frob CLI end-to-end via subprocess.

Each test exercises a complete user-facing command and checks stdout/stderr
and exit codes. These catch wiring bugs (argparse, runner dispatch, logging)
that unit tests cannot.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

FROB = [sys.executable, "-m", "frob"]


def run(*args, cwd=None, input=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        FROB + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
        input=input,
    )


# ---------------------------------------------------------------------------
# fixtures for outline/xref
# ---------------------------------------------------------------------------


@pytest.fixture
def py_src(tmp_path, py_sample):
    p = tmp_path / "sample.py"
    p.write_bytes(py_sample)
    return p


# ---------------------------------------------------------------------------
# frob outline
# ---------------------------------------------------------------------------


def test_outline_exits_zero(py_src):
    r = run("outline", str(py_src))
    assert r.returncode == 0


def test_outline_shows_functions(py_src):
    r = run("outline", str(py_src))
    assert "helper" in r.stdout
    assert "MyClass" in r.stdout


def test_outline_shows_line_numbers(py_src):
    r = run("outline", str(py_src))
    assert "[L" in r.stdout


def test_outline_json(py_src):
    r = run("outline", str(py_src), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "functions" in data
    assert any(f["name"] == "helper" for f in data["functions"])


def test_outline_unsupported_exits_nonzero(tmp_path):
    f = tmp_path / "script.rb"
    f.write_text("def foo; end")
    r = run("outline", str(f))
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# frob map
# ---------------------------------------------------------------------------


def test_map_exits_zero(tmp_path, py_sample):
    (tmp_path / "a.py").write_bytes(py_sample)
    r = run("map", str(tmp_path))
    assert r.returncode == 0


def test_map_shows_files(tmp_path, py_sample):
    (tmp_path / "a.py").write_bytes(py_sample)
    r = run("map", str(tmp_path))
    assert "a.py" in r.stdout


def test_map_json(tmp_path, py_sample):
    (tmp_path / "a.py").write_bytes(py_sample)
    r = run("map", str(tmp_path), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "files" in data


# ---------------------------------------------------------------------------
# frob xref
# ---------------------------------------------------------------------------


def test_xref_exits_zero(py_src):
    r = run("xref", "helper", str(py_src))
    assert r.returncode == 0


def test_xref_shows_definition(py_src):
    r = run("xref", "helper", str(py_src))
    assert "defined" in r.stdout


def test_xref_json(py_src):
    r = run("xref", "helper", str(py_src), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["symbol"] == "helper"


def test_xref_no_files_nonzero(tmp_path):
    r = run("xref", "foo", str(tmp_path))
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# frob parse
# ---------------------------------------------------------------------------

PYTEST_FAIL_OUTPUT = """\
tests/test_foo.py::test_alpha PASSED
tests/test_foo.py::test_beta FAILED
============================== 1 failed, 1 passed in 0.3s ==============================
"""

RUFF_JSON_OUTPUT = '[{"code":"F401","filename":"foo.py","location":{"row":1,"column":1},"end_location":{"row":1,"column":5},"message":"unused import","fix":null,"cell":null,"noqa_row":1,"url":"x"}]'


def test_parse_pytest_exit_zero():
    r = run("parse", "pytest", "--exit-code", "0", input=PYTEST_FAIL_OUTPUT)
    assert r.returncode == 0


def test_parse_pytest_shows_failure(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text(PYTEST_FAIL_OUTPUT)
    r = run("parse", "pytest", str(f), "--exit-code", "1")
    assert r.returncode == 0
    assert "FAIL" in r.stdout or "fail" in r.stdout.lower()


def test_parse_ruff_json():
    r = run("parse", "ruff", "--exit-code", "1", input=RUFF_JSON_OUTPUT)
    assert r.returncode == 0
    assert "F401" in r.stdout


def test_parse_clang(tmp_path):
    f = tmp_path / "build.log"
    f.write_text("src/foo.cpp:5:3: error: expected ';' before '}' token\n")
    r = run("parse", "clang", str(f), "--exit-code", "1")
    assert r.returncode == 0
    assert "error" in r.stdout.lower()


def test_parse_json_output():
    r = run("parse", "ruff", "--json", "--exit-code", "1", input=RUFF_JSON_OUTPUT)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["tool"] == "ruff"


def test_parse_passthrough_propagates_failure():
    r = run(
        "parse", "pytest", "--exit-code", "1", "--passthrough", input=PYTEST_FAIL_OUTPUT
    )
    assert r.returncode != 0


def test_parse_unknown_tool():
    r = run("parse", "unknown_tool_xyz")
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# frob cycle
# ---------------------------------------------------------------------------


def test_cycle_no_cycle_exits_zero(tmp_path, py_sample):
    (tmp_path / "a.py").write_bytes(py_sample)
    r = run("cycle", str(tmp_path))
    assert r.returncode == 0


def test_cycle_detects_cycle(tmp_path):
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from a import something\n")
    r = run("cycle", str(tmp_path))
    assert r.returncode == 0
    assert "cycle" in r.stdout.lower()


def test_cycle_suggest_flag(tmp_path):
    (tmp_path / "a.py").write_text("from b import something\n")
    (tmp_path / "b.py").write_text("from a import something\n")
    r = run("cycle", str(tmp_path), "--suggest")
    assert r.returncode == 0
    assert "suggest" in r.stdout.lower()


# ---------------------------------------------------------------------------
# frob dup
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_dup_exits_zero():
    r = run("dup", str(FIXTURES / "dup_python"))
    assert r.returncode == 0


def test_dup_detects_clone():
    r = run("dup", str(FIXTURES / "dup_python"))
    assert "duplicate" in r.stdout.lower() or "group" in r.stdout.lower()


def test_dup_no_clones_clean_dir(tmp_path, py_sample):
    (tmp_path / "a.py").write_bytes(py_sample)
    r = run("dup", str(tmp_path))
    assert r.returncode == 0
    assert "no duplicates" in r.stdout.lower()


def test_dup_json_output():
    r = run("dup", str(FIXTURES / "dup_python"), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "groups" in data
    assert len(data["groups"]) >= 1


def test_dup_min_lines_flag():
    r = run("dup", str(FIXTURES / "dup_python"), "--min-lines", "100")
    assert r.returncode == 0
    assert "no duplicates" in r.stdout.lower()


# ---------------------------------------------------------------------------
# frob arch
# ---------------------------------------------------------------------------


def test_arch_exits_zero():
    r = run("arch", str(FIXTURES / "arch_python"))
    assert r.returncode == 0


def test_arch_detects_god_class():
    r = run("arch", str(FIXTURES / "arch_python"))
    assert "god-class" in r.stdout


def test_arch_detects_long_function():
    r = run("arch", str(FIXTURES / "arch_python"))
    assert "long-function" in r.stdout


def test_arch_detects_deep_nesting():
    r = run("arch", str(FIXTURES / "arch_python"))
    assert "deep-nesting" in r.stdout


def test_arch_json_output():
    r = run("arch", str(FIXTURES / "arch_python"), "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "suggestions" in data
    assert len(data["suggestions"]) >= 3


def test_arch_clean_dir_no_warnings(tmp_path, py_sample):
    (tmp_path / "a.py").write_bytes(py_sample)
    r = run("arch", str(tmp_path))
    assert r.returncode == 0


def test_arch_max_function_lines_flag():
    r = run("arch", str(FIXTURES / "arch_python"), "--max-function-lines", "200")
    assert r.returncode == 0
    assert "long-function" not in r.stdout
