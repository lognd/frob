"""
End-to-end tests for `frob arch`.
"""

import json

from tests.system.conftest import FIXTURES, PY_FIXTURE, run

ARCH_PYTHON_DIR = FIXTURES / "arch_python"


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_zero():
    r = run("arch", str(ARCH_PYTHON_DIR))
    assert r.returncode == 0


def test_exit_zero_clean_dir(tmp_path):
    (tmp_path / "a.py").write_text(PY_FIXTURE)
    r = run("arch", str(tmp_path))
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_text_shows_god_class():
    r = run("arch", str(ARCH_PYTHON_DIR))
    assert "god-class" in r.stdout


def test_text_shows_long_function():
    r = run("arch", str(ARCH_PYTHON_DIR))
    assert "long-function" in r.stdout


def test_text_shows_deep_nesting():
    r = run("arch", str(ARCH_PYTHON_DIR))
    assert "deep-nesting" in r.stdout


def test_text_mentions_big_class_file():
    r = run("arch", str(ARCH_PYTHON_DIR))
    assert "big_class.py" in r.stdout


def test_text_mentions_long_func_file():
    r = run("arch", str(ARCH_PYTHON_DIR))
    assert "long_func.py" in r.stdout


def test_text_mentions_deep_nest_file():
    r = run("arch", str(ARCH_PYTHON_DIR))
    assert "deep_nest.py" in r.stdout


def test_clean_dir_no_suggestions(tmp_path):
    (tmp_path / "a.py").write_text(PY_FIXTURE)
    r = run("arch", str(tmp_path))
    assert "god-class" not in r.stdout
    assert "long-function" not in r.stdout
    assert "deep-nesting" not in r.stdout


# ---------------------------------------------------------------------------
# --json flag
# ---------------------------------------------------------------------------


def test_json_exit_zero():
    r = run("arch", str(ARCH_PYTHON_DIR), "--json")
    assert r.returncode == 0


def test_json_is_valid():
    r = run("arch", str(ARCH_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    assert isinstance(data, dict)


def test_json_has_suggestions_key():
    r = run("arch", str(ARCH_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    assert "suggestions" in data


def test_json_suggestions_count():
    r = run("arch", str(ARCH_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    assert len(data["suggestions"]) >= 3


def test_json_god_class_entry():
    r = run("arch", str(ARCH_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    god = next(s for s in data["suggestions"] if s["category"] == "god-class")
    assert god["file"].endswith("big_class.py")
    assert god["severity"] == "warning"
    assert isinstance(god["line"], int)
    assert god["line"] > 0


# frob:waive DUP001 reason="parallel CLI system-test scaffolding: \
# independent commands sharing the subprocess-dispatch arrange-act shape; \
# extracting would obscure per-command intent"
def test_json_long_function_entry():
    r = run("arch", str(ARCH_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    lf = next(s for s in data["suggestions"] if s["category"] == "long-function")
    assert lf["file"].endswith("long_func.py")
    assert isinstance(lf["line"], int)
    assert lf["line"] > 0


# frob:waive DUP001 reason="parallel CLI system-test scaffolding: \
# independent commands sharing the subprocess-dispatch arrange-act shape; \
# extracting would obscure per-command intent"
def test_json_deep_nesting_entry():
    r = run("arch", str(ARCH_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    dn = next(s for s in data["suggestions"] if s["category"] == "deep-nesting")
    assert dn["file"].endswith("deep_nest.py")
    assert isinstance(dn["line"], int)
    assert dn["line"] > 0


def test_json_suggestion_has_message_field():
    r = run("arch", str(ARCH_PYTHON_DIR), "--json")
    data = json.loads(r.stdout)
    for s in data["suggestions"]:
        assert "message" in s
        assert len(s["message"]) > 0


# ---------------------------------------------------------------------------
# --max-function-lines flag
# ---------------------------------------------------------------------------


def test_max_function_lines_200_no_long_function():
    r = run("arch", str(ARCH_PYTHON_DIR), "--max-function-lines", "200")
    assert r.returncode == 0
    assert "long-function" not in r.stdout


def test_max_function_lines_200_still_shows_god_class():
    r = run("arch", str(ARCH_PYTHON_DIR), "--max-function-lines", "200")
    assert "god-class" in r.stdout


# ---------------------------------------------------------------------------
# --max-class-methods flag
# ---------------------------------------------------------------------------


def test_max_class_methods_50_no_god_class():
    r = run("arch", str(ARCH_PYTHON_DIR), "--max-class-methods", "50")
    assert r.returncode == 0
    assert "god-class" not in r.stdout


def test_max_class_methods_50_still_shows_long_function():
    r = run("arch", str(ARCH_PYTHON_DIR), "--max-class-methods", "50")
    assert "long-function" in r.stdout
