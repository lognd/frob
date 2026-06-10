"""
End-to-end tests for `frob xref`.
"""

import json
from pathlib import Path

import pytest

from tests.system.conftest import run

A_PY = """\
def util(x):
    return x + 1
"""

B_PY = """\
from a import util
def foo():
    return util(2)
"""

C_PY = """\
from a import util
result = util(99)
"""


@pytest.fixture
def xref_project(tmp_path):
    (tmp_path / "a.py").write_text(A_PY)
    (tmp_path / "b.py").write_text(B_PY)
    (tmp_path / "c.py").write_text(C_PY)
    return tmp_path


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_zero_found_symbol(xref_project):
    r = run("xref", "util", str(xref_project))
    assert r.returncode == 0


def test_exit_zero_unknown_symbol(xref_project):
    r = run("xref", "totally_unknown_xyz", str(xref_project))
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_text_shows_defined(xref_project):
    r = run("xref", "util", str(xref_project))
    assert "defined" in r.stdout.lower()


def test_text_mentions_a_py_as_definition(xref_project):
    r = run("xref", "util", str(xref_project))
    assert "a.py" in r.stdout


def test_text_mentions_b_py_as_caller(xref_project):
    r = run("xref", "util", str(xref_project))
    assert "b.py" in r.stdout


def test_text_mentions_c_py_as_caller(xref_project):
    r = run("xref", "util", str(xref_project))
    assert "c.py" in r.stdout


# ---------------------------------------------------------------------------
# --json flag
# ---------------------------------------------------------------------------


def test_json_exit_zero(xref_project):
    r = run("xref", "util", str(xref_project), "--json")
    assert r.returncode == 0


def test_json_is_valid(xref_project):
    r = run("xref", "util", str(xref_project), "--json")
    data = json.loads(r.stdout)
    assert isinstance(data, dict)


def test_json_symbol_field(xref_project):
    r = run("xref", "util", str(xref_project), "--json")
    data = json.loads(r.stdout)
    assert data["symbol"] == "util"


def test_json_definition_not_none(xref_project):
    r = run("xref", "util", str(xref_project), "--json")
    data = json.loads(r.stdout)
    assert data["definition"] is not None


def test_json_definition_file_is_a_py(xref_project):
    r = run("xref", "util", str(xref_project), "--json")
    data = json.loads(r.stdout)
    assert "a.py" in data["definition"]["file"]


def test_json_definition_line_is_1(xref_project):
    r = run("xref", "util", str(xref_project), "--json")
    data = json.loads(r.stdout)
    assert data["definition"]["line"] == 1


def test_json_usages_has_entries(xref_project):
    r = run("xref", "util", str(xref_project), "--json")
    data = json.loads(r.stdout)
    assert isinstance(data["usages"], list)
    assert len(data["usages"]) >= 2


def test_json_usages_mention_b_and_c(xref_project):
    r = run("xref", "util", str(xref_project), "--json")
    data = json.loads(r.stdout)
    usage_files = [u["file"] for u in data["usages"]]
    assert any("b.py" in f for f in usage_files)
    assert any("c.py" in f for f in usage_files)


# ---------------------------------------------------------------------------
# Symbol with no definition
# ---------------------------------------------------------------------------


def test_unknown_symbol_json_definition_null(xref_project):
    r = run("xref", "totally_unknown_xyz", str(xref_project), "--json")
    data = json.loads(r.stdout)
    assert data["definition"] is None


def test_unknown_symbol_json_usages_empty(xref_project):
    r = run("xref", "totally_unknown_xyz", str(xref_project), "--json")
    data = json.loads(r.stdout)
    assert data["usages"] == []
