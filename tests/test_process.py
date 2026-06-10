"""
Tests for frob.process parsers.

Each test uses realistic tool output captured from real runs.
"""

from frob.process.parsers import (
    parse_clang,
    parse_junit_xml,
    parse_pytest,
    parse_ruff,
    parse_ruff_json,
    parse_ty,
)

# ---------------------------------------------------------------------------
# pytest parser
# ---------------------------------------------------------------------------

PYTEST_PASS = """\
tests/test_foo.py::test_alpha PASSED                                     [ 50%]
tests/test_foo.py::test_beta PASSED                                      [100%]

============================== 2 passed in 0.12s ==============================
"""

PYTEST_FAIL = """\
tests/test_foo.py::test_alpha PASSED                                     [ 33%]
tests/test_foo.py::test_beta FAILED                                      [ 66%]
tests/test_foo.py::test_gamma PASSED                                     [100%]

================================== FAILURES ==================================
______________________________ test_beta _____________________________

    def test_beta():
>       assert result.is_ok
E       AssertionError: assert False

tests/test_foo.py:15: AssertionError
================================ short test summary info ======================
FAILED tests/test_foo.py::test_beta - AssertionError: assert False
========================= 1 failed, 2 passed in 0.45s =========================
"""

PYTEST_SKIP = """\
tests/test_foo.py::test_alpha PASSED
tests/test_foo.py::test_beta SKIPPED (reason)
============================== 1 passed, 1 skipped in 0.10s ==============================
"""


def test_pytest_all_pass():
    r = parse_pytest(PYTEST_PASS, exit_code=0)
    assert r.passed
    assert len(r.tests) == 2
    assert all(t.passed for t in r.tests)


def test_pytest_failure_detected():
    r = parse_pytest(PYTEST_FAIL, exit_code=1)
    assert not r.passed
    assert len(r.failed_tests) == 1
    assert r.failed_tests[0].name == "test_beta"


def test_pytest_summary_present():
    r = parse_pytest(PYTEST_FAIL, exit_code=1)
    assert "failed" in r.summary.lower() or "1" in r.summary


def test_pytest_as_text_shows_failures():
    r = parse_pytest(PYTEST_FAIL, exit_code=1)
    text = r.as_text()
    assert "FAIL" in text
    assert "test_beta" in text


def test_pytest_as_text_hides_passes_by_default():
    r = parse_pytest(PYTEST_FAIL, exit_code=1)
    text = r.as_text()
    assert "test_alpha" not in text


def test_pytest_skipped():
    r = parse_pytest(PYTEST_SKIP, exit_code=0)
    skipped = [t for t in r.tests if t.skipped]
    assert len(skipped) == 1


def test_pytest_as_json():
    import json

    r = parse_pytest(PYTEST_FAIL, exit_code=1)
    data = json.loads(r.as_json())
    assert data["tool"] == "pytest"
    assert data["exit_code"] == 1


# ---------------------------------------------------------------------------
# ruff parser
# ---------------------------------------------------------------------------

RUFF_TEXT = """\
src/frob/ast/python.py:3:8: F401 [*] `os` imported but unused
src/frob/app/config.py:47:89: E501 Line too long (92 > 88 characters)
Found 2 errors.
"""

RUFF_JSON = """\
[
  {
    "cell": null,
    "code": "F401",
    "end_location": {"column": 10, "row": 3},
    "filename": "src/frob/ast/python.py",
    "fix": null,
    "location": {"column": 8, "row": 3},
    "message": "`os` imported but unused",
    "noqa_row": 3,
    "url": "https://docs.astral.sh/ruff/rules/unused-import"
  },
  {
    "cell": null,
    "code": "E501",
    "end_location": {"column": 93, "row": 47},
    "filename": "src/frob/app/config.py",
    "fix": null,
    "location": {"column": 89, "row": 47},
    "message": "Line too long (92 > 88 characters)",
    "noqa_row": 47,
    "url": "https://docs.astral.sh/ruff/rules/line-too-long"
  }
]
"""

RUFF_CLEAN = "[]"


def test_ruff_text_parses():
    r = parse_ruff(RUFF_TEXT, exit_code=1)
    assert len(r.diagnostics) == 2


def test_ruff_text_codes():
    r = parse_ruff(RUFF_TEXT, exit_code=1)
    codes = {d.code for d in r.diagnostics}
    assert "F401" in codes
    assert "E501" in codes


def test_ruff_json_parses():
    r = parse_ruff_json(RUFF_JSON, exit_code=1)
    assert len(r.diagnostics) == 2


def test_ruff_json_files():
    r = parse_ruff_json(RUFF_JSON, exit_code=1)
    files = {d.file for d in r.diagnostics}
    assert "src/frob/ast/python.py" in files


def test_ruff_clean():
    r = parse_ruff(RUFF_CLEAN, exit_code=0)
    assert r.passed
    assert r.error_count == 0
    assert "no issues" in r.summary


def test_ruff_autodetect_json():
    r = parse_ruff(RUFF_JSON, exit_code=1)
    assert len(r.diagnostics) == 2


def test_ruff_as_text():
    r = parse_ruff(RUFF_JSON, exit_code=1)
    text = r.as_text()
    assert "F401" in text or "E501" in text


# ---------------------------------------------------------------------------
# ty parser
# ---------------------------------------------------------------------------

TY_OUTPUT = """\
error[incompatible-types] src/frob/app/config.py:23:5: Argument of type "str" is not assignable to parameter "path" of type "Path"
warning[possibly-undefined] src/frob/ast/python.py:41:12: Name "node" is possibly unbound
Found 1 error, 1 warning
"""

TY_CLEAN = "All checks passed!"


def test_ty_parses_errors():
    r = parse_ty(TY_OUTPUT, exit_code=1)
    assert r.error_count == 1
    assert r.warning_count == 1


def test_ty_error_code():
    r = parse_ty(TY_OUTPUT, exit_code=1)
    error = next(d for d in r.diagnostics if d.severity == "error")
    assert error.code == "incompatible-types"


def test_ty_error_file():
    r = parse_ty(TY_OUTPUT, exit_code=1)
    error = next(d for d in r.diagnostics if d.severity == "error")
    assert "config.py" in error.file


def test_ty_as_text():
    r = parse_ty(TY_OUTPUT, exit_code=1)
    text = r.as_text()
    assert "incompatible-types" in text or "config.py" in text


def test_ty_clean_exit():
    r = parse_ty(TY_CLEAN, exit_code=0)
    assert r.passed
    assert r.error_count == 0


# ---------------------------------------------------------------------------
# clang/gcc parser
# ---------------------------------------------------------------------------

CLANG_OUTPUT = """\
src/engine.cpp:12:5: error: use of undeclared identifier 'foo'
src/engine.cpp:15:10: warning: unused variable 'x' [-Wunused-variable]
src/engine.cpp:18:1: note: in expansion of macro 'BAR'
"""

GCC_OUTPUT = """\
src/main.c:5:3: error: expected ';' before '}' token
src/main.c:10:12: warning: implicit declaration of function 'printf' [-Wimplicit-function-declaration]
"""


def test_clang_parses():
    r = parse_clang(CLANG_OUTPUT, exit_code=1)
    assert r.error_count == 1
    assert r.warning_count == 1


def test_clang_file():
    r = parse_clang(CLANG_OUTPUT, exit_code=1)
    error = next(d for d in r.diagnostics if d.severity == "error")
    assert "engine.cpp" in error.file


def test_clang_line_number():
    r = parse_clang(CLANG_OUTPUT, exit_code=1)
    error = next(d for d in r.diagnostics if d.severity == "error")
    assert error.line == 12


def test_clang_strips_flag_annotation():
    r = parse_clang(CLANG_OUTPUT, exit_code=1)
    warning = next(d for d in r.diagnostics if d.severity == "warning")
    assert "[-W" not in warning.message


def test_gcc_parses():
    r = parse_clang(GCC_OUTPUT, exit_code=1, tool="gcc")
    assert r.tool == "gcc"
    assert r.error_count == 1


def test_clang_as_text():
    r = parse_clang(CLANG_OUTPUT, exit_code=1)
    text = r.as_text()
    assert "error" in text
    assert "engine.cpp" in text


# ---------------------------------------------------------------------------
# JUnit XML parser
# ---------------------------------------------------------------------------

JUNIT_PASS = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="MyTests" tests="3" failures="0" time="0.5">
    <testcase name="test_alpha" classname="MyTests" time="0.1"/>
    <testcase name="test_beta"  classname="MyTests" time="0.2"/>
    <testcase name="test_gamma" classname="MyTests" time="0.2"/>
  </testsuite>
</testsuites>
"""

JUNIT_FAIL = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="MySuite" tests="2" failures="1" time="1.0">
    <testcase name="test_pass" classname="MySuite" time="0.3"/>
    <testcase name="test_fail" classname="MySuite" time="0.7">
      <failure message="AssertionError: expected 1 got 2" type="AssertionError">
Expected 1 but got 2 at line 42
      </failure>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_SKIP = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="Suite" tests="2" skipped="1">
  <testcase name="test_run" classname="Suite"/>
  <testcase name="test_skip" classname="Suite">
    <skipped message="not implemented"/>
  </testcase>
</testsuite>
"""


def test_junit_all_pass():
    r = parse_junit_xml(JUNIT_PASS, tool="gtest")
    assert r.passed
    assert len(r.tests) == 3


def test_junit_failure():
    r = parse_junit_xml(JUNIT_FAIL)
    assert not r.passed
    assert len(r.failed_tests) == 1
    assert r.failed_tests[0].name == "test_fail"


def test_junit_failure_message():
    r = parse_junit_xml(JUNIT_FAIL)
    assert "AssertionError" in (r.failed_tests[0].failure_message or "")


def test_junit_skipped():
    r = parse_junit_xml(JUNIT_SKIP)
    skipped = [t for t in r.tests if t.skipped]
    assert len(skipped) == 1


def test_junit_summary_contains_counts():
    r = parse_junit_xml(JUNIT_FAIL)
    assert "failed" in r.summary or "1" in r.summary


def test_junit_as_text():
    r = parse_junit_xml(JUNIT_FAIL)
    text = r.as_text()
    assert "FAIL" in text
    assert "test_fail" in text


def test_junit_malformed():
    r = parse_junit_xml("not xml at all")
    assert not r.passed
    assert "malformed" in r.summary.lower()
