"""
End-to-end tests for `frob parse`.
Each tool is tested with realistic fixture strings.
"""

import json

from tests.system.conftest import run

# ---------------------------------------------------------------------------
# Fixture inputs
# ---------------------------------------------------------------------------

PYTEST_INPUT = """\
tests/test_foo.py::test_alpha PASSED
tests/test_foo.py::test_beta FAILED - assert False
tests/test_foo.py::test_skip SKIPPED (reason)
============================== 1 failed, 2 passed, 1 skipped in 0.5s ==============================
"""

RUFF_JSON_INPUT = (
    '[{"code":"F401","filename":"src/foo.py",'
    '"location":{"row":3,"column":1},"end_location":{"row":3,"column":9},'
    '"message":"\'os\' imported but unused","fix":null,"cell":null,'
    '"noqa_row":3,"url":"https://docs.astral.sh/ruff/rules/unused-import"}]'
)

TY_INPUT = """\
error[unresolved-import] src/foo.py:1:8: Cannot resolve imported module `missing_mod`
warning[possibly-undefined] src/bar.py:5:4: Name "x" is possibly unbound
Found 1 error, 1 warning
"""

CLANG_INPUT = """\
src/main.cpp:5:3: error: expected ';' before '}' token
src/main.cpp:10:1: warning: unused variable 'x' [-Wunused-variable]
src/main.cpp:5:3: note: to match this '{'
"""

JUNIT_INPUT = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="MyTests" tests="2" failures="1" errors="0" time="0.5">
    <testcase name="test_ok" classname="MyTests" time="0.1"/>
    <testcase name="test_fail" classname="MyTests" time="0.2">
      <failure message="assertion failed">assert 1 == 2</failure>
    </testcase>
  </testsuite>
</testsuites>
"""


# ---------------------------------------------------------------------------
# pytest
# ---------------------------------------------------------------------------


def test_pytest_exit_zero_with_exit_code_0():
    r = run("parse", "pytest", "--exit-code", "0", input=PYTEST_INPUT)
    assert r.returncode == 0


def test_pytest_exit_zero_with_exit_code_1():
    r = run("parse", "pytest", "--exit-code", "1", input=PYTEST_INPUT)
    assert r.returncode == 0


def test_pytest_text_shows_fail():
    r = run("parse", "pytest", "--exit-code", "1", input=PYTEST_INPUT)
    assert "fail" in r.stdout.lower() or "FAIL" in r.stdout


def test_pytest_text_shows_test_name():
    r = run("parse", "pytest", "--exit-code", "1", input=PYTEST_INPUT)
    assert "test_beta" in r.stdout


def test_pytest_json_exit_zero():
    r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_INPUT)
    assert r.returncode == 0


def test_pytest_json_tool_field():
    r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_INPUT)
    data = json.loads(r.stdout)
    assert data["tool"] == "pytest"


def test_pytest_json_exit_code_field():
    r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_INPUT)
    data = json.loads(r.stdout)
    assert data["exit_code"] == 1


def test_pytest_json_tests_list_length():
    r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_INPUT)
    data = json.loads(r.stdout)
    assert len(data["tests"]) == 3


def test_pytest_json_test_beta_failed():
    r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_INPUT)
    data = json.loads(r.stdout)
    beta = next(t for t in data["tests"] if t["name"] == "test_beta")
    assert beta["passed"] is False
    assert beta["skipped"] is False


def test_pytest_json_test_alpha_passed():
    r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_INPUT)
    data = json.loads(r.stdout)
    alpha = next(t for t in data["tests"] if t["name"] == "test_alpha")
    assert alpha["passed"] is True


def test_pytest_json_test_skip_skipped():
    r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_INPUT)
    data = json.loads(r.stdout)
    skip = next(t for t in data["tests"] if t["name"] == "test_skip")
    assert skip["skipped"] is True


def test_pytest_json_summary_field():
    r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_INPUT)
    data = json.loads(r.stdout)
    assert "summary" in data
    assert "failed" in data["summary"].lower()


def test_pytest_passthrough_propagates_failure():
    r = run("parse", "pytest", "--exit-code", "1", "--passthrough", input=PYTEST_INPUT)
    assert r.returncode != 0


def test_pytest_passthrough_no_failure():
    r = run("parse", "pytest", "--exit-code", "0", "--passthrough", input=PYTEST_INPUT)
    assert r.returncode == 0


def test_pytest_file_arg(tmp_path):
    f = tmp_path / "pytest_out.txt"
    f.write_text(PYTEST_INPUT)
    r = run("parse", "pytest", str(f), "--exit-code", "1")
    assert r.returncode == 0
    assert "test_beta" in r.stdout


# ---------------------------------------------------------------------------
# ruff
# ---------------------------------------------------------------------------


def test_ruff_exit_zero():
    r = run("parse", "ruff", "--exit-code", "1", input=RUFF_JSON_INPUT)
    assert r.returncode == 0


def test_ruff_text_shows_code():
    r = run("parse", "ruff", "--exit-code", "1", input=RUFF_JSON_INPUT)
    assert "F401" in r.stdout


def test_ruff_text_shows_file():
    r = run("parse", "ruff", "--exit-code", "1", input=RUFF_JSON_INPUT)
    assert "src/foo.py" in r.stdout


def test_ruff_json_tool_field():
    r = run("parse", "ruff", "--json", "--exit-code", "1", input=RUFF_JSON_INPUT)
    data = json.loads(r.stdout)
    assert data["tool"] == "ruff"


def test_ruff_json_diagnostics_length():
    r = run("parse", "ruff", "--json", "--exit-code", "1", input=RUFF_JSON_INPUT)
    data = json.loads(r.stdout)
    assert len(data["diagnostics"]) == 1


def test_ruff_json_diagnostic_fields():
    r = run("parse", "ruff", "--json", "--exit-code", "1", input=RUFF_JSON_INPUT)
    data = json.loads(r.stdout)
    diag = data["diagnostics"][0]
    assert diag["file"] == "src/foo.py"
    assert diag["line"] == 3
    assert diag["code"] == "F401"
    assert "imported but unused" in diag["message"]


def test_ruff_json_severity_error():
    r = run("parse", "ruff", "--json", "--exit-code", "1", input=RUFF_JSON_INPUT)
    data = json.loads(r.stdout)
    assert data["diagnostics"][0]["severity"] == "error"


def test_ruff_passthrough_propagates():
    r = run("parse", "ruff", "--exit-code", "1", "--passthrough", input=RUFF_JSON_INPUT)
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# ty
# ---------------------------------------------------------------------------


def test_ty_exit_zero():
    r = run("parse", "ty", "--exit-code", "1", input=TY_INPUT)
    assert r.returncode == 0


def test_ty_text_shows_file():
    r = run("parse", "ty", "--exit-code", "1", input=TY_INPUT)
    assert "src/foo.py" in r.stdout or "src/bar.py" in r.stdout


def test_ty_json_tool_field():
    r = run("parse", "ty", "--json", "--exit-code", "1", input=TY_INPUT)
    data = json.loads(r.stdout)
    assert data["tool"] == "ty"


def test_ty_json_diagnostics_length():
    r = run("parse", "ty", "--json", "--exit-code", "1", input=TY_INPUT)
    data = json.loads(r.stdout)
    assert len(data["diagnostics"]) == 2


def test_ty_json_error_diagnostic():
    r = run("parse", "ty", "--json", "--exit-code", "1", input=TY_INPUT)
    data = json.loads(r.stdout)
    err = next(d for d in data["diagnostics"] if d["severity"] == "error")
    assert err["file"] == "src/foo.py"
    assert err["line"] == 1
    assert err["col"] == 8
    assert err["code"] == "unresolved-import"
    assert "missing_mod" in err["message"]


def test_ty_json_warning_diagnostic():
    r = run("parse", "ty", "--json", "--exit-code", "1", input=TY_INPUT)
    data = json.loads(r.stdout)
    warn = next(d for d in data["diagnostics"] if d["severity"] == "warning")
    assert warn["file"] == "src/bar.py"
    assert warn["line"] == 5
    assert warn["col"] == 4
    assert warn["code"] == "possibly-undefined"


# ---------------------------------------------------------------------------
# clang
# ---------------------------------------------------------------------------


def test_clang_exit_zero():
    r = run("parse", "clang", "--exit-code", "1", input=CLANG_INPUT)
    assert r.returncode == 0


def test_clang_text_shows_error():
    r = run("parse", "clang", "--exit-code", "1", input=CLANG_INPUT)
    assert "error" in r.stdout.lower()


def test_clang_text_shows_file():
    r = run("parse", "clang", "--exit-code", "1", input=CLANG_INPUT)
    assert "src/main.cpp" in r.stdout


def test_clang_json_tool_field():
    r = run("parse", "clang", "--json", "--exit-code", "1", input=CLANG_INPUT)
    data = json.loads(r.stdout)
    assert data["tool"] == "clang"


def test_clang_json_diagnostics_count():
    # error + warning + note = 3 entries
    r = run("parse", "clang", "--json", "--exit-code", "1", input=CLANG_INPUT)
    data = json.loads(r.stdout)
    assert len(data["diagnostics"]) == 3


def test_clang_json_error_diagnostic():
    r = run("parse", "clang", "--json", "--exit-code", "1", input=CLANG_INPUT)
    data = json.loads(r.stdout)
    err = next(d for d in data["diagnostics"] if d["severity"] == "error")
    assert err["file"] == "src/main.cpp"
    assert err["line"] == 5
    assert err["col"] == 3
    assert "expected ';'" in err["message"]


def test_clang_json_warning_diagnostic():
    r = run("parse", "clang", "--json", "--exit-code", "1", input=CLANG_INPUT)
    data = json.loads(r.stdout)
    warn = next(d for d in data["diagnostics"] if d["severity"] == "warning")
    assert warn["file"] == "src/main.cpp"
    assert warn["line"] == 10
    assert "unused variable" in warn["message"]


def test_clang_passthrough_propagates():
    r = run("parse", "clang", "--exit-code", "1", "--passthrough", input=CLANG_INPUT)
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# junit
# ---------------------------------------------------------------------------


def test_junit_exit_zero():
    r = run("parse", "junit", "--exit-code", "1", input=JUNIT_INPUT)
    assert r.returncode == 0


def test_junit_text_shows_fail():
    r = run("parse", "junit", "--exit-code", "1", input=JUNIT_INPUT)
    assert "fail" in r.stdout.lower() or "FAIL" in r.stdout


def test_junit_json_tool_field():
    r = run("parse", "junit", "--json", "--exit-code", "1", input=JUNIT_INPUT)
    data = json.loads(r.stdout)
    assert data["tool"] == "junit"


def test_junit_json_tests_length():
    r = run("parse", "junit", "--json", "--exit-code", "1", input=JUNIT_INPUT)
    data = json.loads(r.stdout)
    assert len(data["tests"]) == 2


def test_junit_json_failed_test():
    r = run("parse", "junit", "--json", "--exit-code", "1", input=JUNIT_INPUT)
    data = json.loads(r.stdout)
    fail = next(t for t in data["tests"] if t["name"] == "test_fail")
    assert fail["passed"] is False


def test_junit_json_passed_test():
    r = run("parse", "junit", "--json", "--exit-code", "1", input=JUNIT_INPUT)
    data = json.loads(r.stdout)
    ok = next(t for t in data["tests"] if t["name"] == "test_ok")
    assert ok["passed"] is True


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------


def test_unknown_tool_exits_nonzero():
    r = run("parse", "totally_unknown_tool_xyz")
    assert r.returncode != 0
