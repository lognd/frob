"""
Comprehensive tests for frob.process parsers (unit) and frob parse CLI (system).

Unit tests cover every parser directly: happy path, error cases, edge cases,
output format (text and JSON), and boundary conditions.

System tests run `frob parse <tool>` via subprocess and verify stdout/stderr
and exit codes end-to-end.
"""

from __future__ import annotations

import json
import subprocess
import sys

from frob.process.parsers import (
    parse_clang,
    parse_junit_xml,
    parse_pytest,
    parse_ruff,
    parse_ruff_json,
    parse_ruff_text,
    parse_ty,
)
from frob.process.parsers.common import Diagnostic, TestCase, ToolResult

FROB = [sys.executable, "-m", "frob"]


# frob:waive DUP001 reason="parallel test fixtures across 2 sibling test file(s) (2 \
# sites) sharing an arrange-act scaffold typical of exhaustive per-case/per-scenario \
# coverage; extracting would obscure per-case intent"
def run(*args, input: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        FROB + list(args),
        capture_output=True,
        text=True,
        input=input,
    )


# ===========================================================================
# common.Diagnostic unit tests
# ===========================================================================


class TestDiagnosticAsText:
    def test_full(self):
        d = Diagnostic(
            file="foo.py",
            line=10,
            col=3,
            severity="error",
            code="E501",
            message="too long",
        )
        text = d.as_text()
        assert "foo.py" in text
        assert "10" in text
        assert "3" in text
        assert "E501" in text
        assert "too long" in text

    def test_no_file(self):
        d = Diagnostic(severity="error", code="F401", message="unused")
        text = d.as_text()
        assert "F401" in text
        assert "unused" in text

    def test_file_no_col(self):
        d = Diagnostic(file="bar.py", line=5, severity="warning", message="warn")
        text = d.as_text()
        assert "bar.py:5" in text

    def test_no_code(self):
        d = Diagnostic(file="a.py", line=1, severity="error", message="oops")
        text = d.as_text()
        assert "oops" in text
        assert "None" not in text


# ===========================================================================
# common.ToolResult unit tests
# ===========================================================================


class TestToolResult:
    def _make(self, exit_code: int = 0) -> ToolResult:
        return ToolResult(
            tool="pytest",
            exit_code=exit_code,
            diagnostics=[
                Diagnostic(severity="error", code="E1", message="err"),
                Diagnostic(severity="warning", code="W1", message="warn"),
                Diagnostic(severity="note", message="note"),
            ],
            tests=[
                TestCase(name="test_pass", passed=True),
                TestCase(name="test_fail", passed=False, failure_message="oops"),
                TestCase(name="test_skip", passed=True, skipped=True),
            ],
            summary="1 failed, 1 passed",
        )

    def test_passed_false_when_nonzero(self):
        r = self._make(exit_code=1)
        assert not r.passed

    def test_passed_true_when_zero(self):
        r = self._make(exit_code=0)
        assert r.passed

    def test_error_count(self):
        r = self._make()
        assert r.error_count == 1

    def test_warning_count(self):
        r = self._make()
        assert r.warning_count == 1

    def test_failed_tests_excludes_skip(self):
        r = self._make(exit_code=1)
        assert len(r.failed_tests) == 1
        assert r.failed_tests[0].name == "test_fail"

    def test_as_text_shows_errors(self):
        r = self._make(exit_code=1)
        text = r.as_text()
        assert "err" in text
        assert "E1" in text

    def test_as_text_shows_failed_test(self):
        r = self._make(exit_code=1)
        text = r.as_text()
        assert "FAIL" in text
        assert "test_fail" in text

    def test_as_text_hides_passing_by_default(self):
        r = self._make()
        text = r.as_text()
        assert "test_pass" not in text

    def test_as_text_verbose_shows_passes(self):
        r = self._make()
        text = r.as_text(verbose=True)
        assert "test_pass" in text

    def test_as_text_verbose_shows_failure_text(self):
        r = ToolResult(
            tool="pytest",
            exit_code=1,
            tests=[
                TestCase(
                    name="t",
                    passed=False,
                    failure_message="msg",
                    failure_text="line1\nline2",
                )
            ],
            summary="1 failed",
        )
        text = r.as_text(verbose=True)
        assert "line1" in text

    def test_as_text_verbose_shows_notes(self):
        r = self._make()
        text = r.as_text(verbose=True)
        assert "note" in text

    def test_as_json_valid(self):
        r = self._make()
        data = json.loads(r.as_json())
        assert data["tool"] == "pytest"
        assert "diagnostics" in data
        assert "tests" in data

    def test_as_json_exit_code(self):
        r = self._make(exit_code=2)
        data = json.loads(r.as_json())
        assert data["exit_code"] == 2


# ===========================================================================
# pytest parser unit tests
# ===========================================================================

PYTEST_ALL_PASS = """\
tests/test_foo.py::test_alpha PASSED                                     [ 50%]
tests/test_foo.py::test_beta PASSED                                      [100%]

============================== 2 passed in 0.12s ==============================
"""

PYTEST_ONE_FAIL = """\
tests/test_foo.py::test_alpha PASSED                                     [ 33%]
tests/test_foo.py::test_beta FAILED                                      [ 66%]
tests/test_foo.py::test_gamma PASSED                                     [100%]

================================== FAILURES ==================================
______________________________ test_beta _____________________________

    def test_beta():
>       assert result.is_ok
E       AssertionError: assert False
E       where False = result.is_ok

tests/test_foo.py:15: AssertionError
================================ short test summary info ======================
FAILED tests/test_foo.py::test_beta - AssertionError: assert False
========================= 1 failed, 2 passed in 0.45s =========================
"""

PYTEST_TWO_FAIL = """\
tests/test_bar.py::test_x FAILED
tests/test_bar.py::test_y FAILED
============================== 2 failed in 0.10s ==============================
"""

PYTEST_SKIPPED = """\
tests/test_foo.py::test_alpha PASSED
tests/test_foo.py::test_skip SKIPPED (not implemented)
============================== 1 passed, 1 skipped in 0.10s ==============================
"""

PYTEST_ERROR = """\
ERROR collecting tests/test_bad.py
============================== 1 error in 0.05s ==============================
"""

PYTEST_EMPTY = ""
PYTEST_ONLY_SUMMARY = (
    "============================== 0 passed in 0.01s =============================="
)


class TestParsePytest:
    def test_all_pass_count(self):
        r = parse_pytest(PYTEST_ALL_PASS, exit_code=0)
        assert len(r.tests) == 2
        assert all(t.passed for t in r.tests)

    def test_all_pass_result(self):
        r = parse_pytest(PYTEST_ALL_PASS, exit_code=0)
        assert r.passed

    def test_failure_detected(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        assert not r.passed
        assert len(r.failed_tests) == 1

    def test_failure_name(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        assert r.failed_tests[0].name == "test_beta"

    def test_failure_message_extracted(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        assert r.failed_tests[0].failure_message is not None
        assert "AssertionError" in r.failed_tests[0].failure_message

    def test_two_failures(self):
        r = parse_pytest(PYTEST_TWO_FAIL, exit_code=1)
        assert len(r.failed_tests) == 2

    def test_skipped_case(self):
        r = parse_pytest(PYTEST_SKIPPED, exit_code=0)
        skipped = [t for t in r.tests if t.skipped]
        assert len(skipped) == 1

    def test_skipped_not_in_failed(self):
        r = parse_pytest(PYTEST_SKIPPED, exit_code=0)
        assert len(r.failed_tests) == 0

    def test_summary_present(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        assert r.summary != ""

    def test_summary_contains_counts(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        assert "1" in r.summary

    def test_tool_name(self):
        r = parse_pytest(PYTEST_ALL_PASS, exit_code=0)
        assert r.tool == "pytest"

    def test_exit_code_stored(self):
        r = parse_pytest(PYTEST_ALL_PASS, exit_code=5)
        assert r.exit_code == 5

    def test_empty_input(self):
        r = parse_pytest(PYTEST_EMPTY, exit_code=0)
        assert r.tool == "pytest"
        assert r.tests == []

    def test_only_summary_line(self):
        r = parse_pytest(PYTEST_ONLY_SUMMARY, exit_code=0)
        assert r.tool == "pytest"

    def test_error_collection(self):
        r = parse_pytest(PYTEST_ERROR, exit_code=2)
        assert not r.passed

    def test_as_text_has_tool_name(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        assert "[pytest]" in r.as_text()

    def test_as_text_hides_passing(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        assert "test_alpha" not in r.as_text()
        assert "test_gamma" not in r.as_text()

    def test_as_text_shows_failure(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        assert "test_beta" in r.as_text()

    def test_as_json_structure(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        data = json.loads(r.as_json())
        assert data["tool"] == "pytest"
        assert len(data["tests"]) == 3

    def test_suite_extracted_from_node_id(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        t = next(t for t in r.tests if t.name == "test_beta")
        assert "test_foo.py" in t.suite

    def test_as_text_verbose_shows_failure_details(self):
        r = parse_pytest(PYTEST_ONE_FAIL, exit_code=1)
        text = r.as_text(verbose=True)
        assert "AssertionError" in text


# ===========================================================================
# ruff parser unit tests
# ===========================================================================

RUFF_TEXT_TWO = """\
src/frob/ast/python.py:3:8: F401 [*] `os` imported but unused
src/frob/app/config.py:47:89: E501 Line too long (92 > 88 characters)
Found 2 errors.
"""

RUFF_TEXT_WARNING = """\
src/foo.py:1:1: W291 trailing whitespace
"""

RUFF_TEXT_CLEAN_EMPTY = ""
RUFF_TEXT_NO_ISSUES = "All checks passed!"

RUFF_JSON_TWO = json.dumps(
    [
        {
            "cell": None,
            "code": "F401",
            "end_location": {"column": 10, "row": 3},
            "filename": "src/frob/ast/python.py",
            "fix": None,
            "location": {"column": 8, "row": 3},
            "message": "`os` imported but unused",
            "noqa_row": 3,
            "url": "x",
        },
        {
            "cell": None,
            "code": "E501",
            "end_location": {"column": 93, "row": 47},
            "filename": "src/frob/app/config.py",
            "fix": None,
            "location": {"column": 89, "row": 47},
            "message": "Line too long (92 > 88 characters)",
            "noqa_row": 47,
            "url": "x",
        },
    ]
)

RUFF_JSON_EMPTY = "[]"
RUFF_JSON_W_ONLY = json.dumps(
    [
        {
            "cell": None,
            "code": "W291",
            "end_location": {"column": 5, "row": 1},
            "filename": "src/foo.py",
            "fix": None,
            "location": {"column": 1, "row": 1},
            "message": "trailing whitespace",
            "noqa_row": 1,
            "url": "x",
        }
    ]
)


class TestParseRuffText:
    def test_two_errors_parsed(self):
        # frob:tests src/frob/process/parsers/ruff.py::parse_ruff_text kind="unit"
        r = parse_ruff_text(RUFF_TEXT_TWO, exit_code=1)
        assert len(r.diagnostics) == 2

    def test_codes_correct(self):
        r = parse_ruff_text(RUFF_TEXT_TWO, exit_code=1)
        codes = {d.code for d in r.diagnostics}
        assert "F401" in codes
        assert "E501" in codes

    def test_severity_e_is_error(self):
        r = parse_ruff_text(RUFF_TEXT_TWO, exit_code=1)
        e501 = next(d for d in r.diagnostics if d.code == "E501")
        assert e501.severity == "error"

    def test_severity_f_is_error(self):
        r = parse_ruff_text(RUFF_TEXT_TWO, exit_code=1)
        f401 = next(d for d in r.diagnostics if d.code == "F401")
        assert f401.severity == "error"

    def test_severity_w_is_warning(self):
        r = parse_ruff_text(RUFF_TEXT_WARNING, exit_code=1)
        assert r.diagnostics[0].severity == "warning"

    def test_line_number(self):
        r = parse_ruff_text(RUFF_TEXT_TWO, exit_code=1)
        f401 = next(d for d in r.diagnostics if d.code == "F401")
        assert f401.line == 3

    def test_col_number(self):
        r = parse_ruff_text(RUFF_TEXT_TWO, exit_code=1)
        f401 = next(d for d in r.diagnostics if d.code == "F401")
        assert f401.col == 8

    def test_file(self):
        r = parse_ruff_text(RUFF_TEXT_TWO, exit_code=1)
        files = {d.file for d in r.diagnostics}
        assert "src/frob/ast/python.py" in files

    def test_clean_empty(self):
        r = parse_ruff_text(RUFF_TEXT_CLEAN_EMPTY, exit_code=0)
        assert r.diagnostics == []
        assert "no issues" in r.summary

    def test_summary_has_counts(self):
        r = parse_ruff_text(RUFF_TEXT_TWO, exit_code=1)
        assert "2" in r.summary


class TestParseRuffJson:
    def test_two_parsed(self):
        r = parse_ruff_json(RUFF_JSON_TWO, exit_code=1)
        assert len(r.diagnostics) == 2

    def test_empty_array(self):
        r = parse_ruff_json(RUFF_JSON_EMPTY, exit_code=0)
        assert r.diagnostics == []
        assert "no issues" in r.summary
        assert r.passed

    def test_warning_only(self):
        r = parse_ruff_json(RUFF_JSON_W_ONLY, exit_code=1)
        assert r.diagnostics[0].severity == "warning"

    def test_malformed_json(self):
        r = parse_ruff_json("not json", exit_code=1)
        assert not r.passed
        assert "malformed" in r.summary

    def test_file_extracted(self):
        r = parse_ruff_json(RUFF_JSON_TWO, exit_code=1)
        files = {d.file for d in r.diagnostics}
        assert "src/frob/ast/python.py" in files

    def test_message_extracted(self):
        r = parse_ruff_json(RUFF_JSON_TWO, exit_code=1)
        f401 = next(d for d in r.diagnostics if d.code == "F401")
        assert "unused" in f401.message


class TestParseRuffAutodetect:
    def test_json_autodetected(self):
        r = parse_ruff(RUFF_JSON_TWO, exit_code=1)
        assert len(r.diagnostics) == 2

    def test_text_autodetected(self):
        r = parse_ruff(RUFF_TEXT_TWO, exit_code=1)
        assert len(r.diagnostics) == 2

    def test_empty_json_autodetected(self):
        r = parse_ruff(RUFF_JSON_EMPTY, exit_code=0)
        assert r.diagnostics == []

    def test_as_text_contains_tool(self):
        r = parse_ruff(RUFF_JSON_TWO, exit_code=1)
        assert "[ruff]" in r.as_text()

    def test_as_json_tool_field(self):
        r = parse_ruff(RUFF_JSON_TWO, exit_code=1)
        assert json.loads(r.as_json())["tool"] == "ruff"


# ===========================================================================
# ty parser unit tests
# ===========================================================================

TY_BRACKET = """\
error[incompatible-types] src/frob/app/config.py:23:5: Argument of type "str" is not assignable to parameter "path" of type "Path"
warning[possibly-undefined] src/frob/ast/python.py:41:12: Name "node" is possibly unbound
Found 1 error, 1 warning
"""

TY_ANSI = "\x1b[31merror\x1b[0m[incompatible-types] src/foo.py:1:1: bad type"

TY_SIMPLE = """\
error src/bar.py:5:3: something wrong
"""

TY_NOTE = """\
note[some-note] src/baz.py:2:1: this is informational
"""

TY_CLEAN = "All checks passed!"
TY_EMPTY = ""
TY_MULTI_ERROR = """\
error[e1] src/a.py:1:1: first error
error[e2] src/b.py:2:2: second error
warning[w1] src/c.py:3:3: a warning
"""


class TestParseTy:
    def test_error_count(self):
        # frob:tests src/frob/process/parsers/ty.py::parse_ty kind="unit"
        r = parse_ty(TY_BRACKET, exit_code=1)
        assert r.error_count == 1

    def test_warning_count(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        assert r.warning_count == 1

    def test_error_code(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        err = next(d for d in r.diagnostics if d.severity == "error")
        assert err.code == "incompatible-types"

    def test_error_file(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        err = next(d for d in r.diagnostics if d.severity == "error")
        assert err.file and "config.py" in err.file

    def test_error_line(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        err = next(d for d in r.diagnostics if d.severity == "error")
        assert err.line == 23

    def test_error_col(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        err = next(d for d in r.diagnostics if d.severity == "error")
        assert err.col == 5

    def test_ansi_stripped(self):
        r = parse_ty(TY_ANSI, exit_code=1)
        assert r.error_count == 1
        assert r.diagnostics[0].code == "incompatible-types"

    def test_simple_format(self):
        r = parse_ty(TY_SIMPLE, exit_code=1)
        assert r.error_count == 1

    def test_note_severity(self):
        r = parse_ty(TY_NOTE, exit_code=0)
        notes = [d for d in r.diagnostics if d.severity == "note"]
        assert len(notes) == 1

    def test_clean_passes(self):
        r = parse_ty(TY_CLEAN, exit_code=0)
        assert r.passed
        assert r.error_count == 0

    def test_empty_input(self):
        r = parse_ty(TY_EMPTY, exit_code=0)
        assert r.diagnostics == []

    def test_summary_uses_found_line(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        assert "1 error" in r.summary

    def test_summary_fallback(self):
        # No "Found X error" line
        r = parse_ty(TY_MULTI_ERROR, exit_code=1)
        assert "2" in r.summary

    def test_multi_error(self):
        r = parse_ty(TY_MULTI_ERROR, exit_code=1)
        assert r.error_count == 2
        assert r.warning_count == 1

    def test_tool_name(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        assert r.tool == "ty"

    def test_as_text_tool_header(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        assert "[ty]" in r.as_text()

    def test_as_json(self):
        r = parse_ty(TY_BRACKET, exit_code=1)
        data = json.loads(r.as_json())
        assert data["tool"] == "ty"
        assert len(data["diagnostics"]) == 2


# ===========================================================================
# clang/gcc parser unit tests
# ===========================================================================

CLANG_BASIC = """\
src/engine.cpp:12:5: error: use of undeclared identifier 'foo'
src/engine.cpp:15:10: warning: unused variable 'x' [-Wunused-variable]
src/engine.cpp:18:1: note: in expansion of macro 'BAR'
"""

CLANG_ANSI = (
    "\x1b[1msrc/foo.cpp:1:1:\x1b[0m \x1b[1;31merror:\x1b[0m undeclared identifier"
)

GCC_BASIC = """\
src/main.c:5:3: error: expected ';' before '}' token
src/main.c:10:12: warning: implicit declaration of function 'printf' [-Wimplicit-function-declaration]
"""

CLANG_MULTI_ERROR = """\
a.cpp:1:1: error: first
b.cpp:2:2: error: second
c.cpp:3:3: warning: third
"""

CLANG_EMPTY = ""


class TestParseClang:
    def test_error_count(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        assert r.error_count == 1

    def test_warning_count(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        assert r.warning_count == 1

    def test_note_not_counted_as_warning(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        assert r.warning_count == 1

    def test_error_file(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        err = next(d for d in r.diagnostics if d.severity == "error")
        assert err.file and "engine.cpp" in err.file

    def test_error_line(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        err = next(d for d in r.diagnostics if d.severity == "error")
        assert err.line == 12

    def test_error_col(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        err = next(d for d in r.diagnostics if d.severity == "error")
        assert err.col == 5

    def test_strips_w_flag_annotation(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        warn = next(d for d in r.diagnostics if d.severity == "warning")
        assert "[-W" not in warn.message

    def test_gcc_tool_name(self):
        r = parse_clang(GCC_BASIC, exit_code=1, tool="gcc")
        assert r.tool == "gcc"

    def test_gcc_errors(self):
        r = parse_clang(GCC_BASIC, exit_code=1, tool="gcc")
        assert r.error_count == 1

    def test_multi_error(self):
        r = parse_clang(CLANG_MULTI_ERROR, exit_code=1)
        assert r.error_count == 2
        assert r.warning_count == 1

    def test_empty_input(self):
        r = parse_clang(CLANG_EMPTY, exit_code=0)
        assert r.diagnostics == []

    def test_tool_name_default_clang(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        assert r.tool == "clang"

    def test_as_text_shows_error(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        text = r.as_text()
        assert "error" in text
        assert "engine.cpp" in text

    def test_as_text_tool_header(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        assert "[clang]" in r.as_text()

    def test_as_json(self):
        r = parse_clang(CLANG_BASIC, exit_code=1)
        data = json.loads(r.as_json())
        assert data["tool"] == "clang"


# ===========================================================================
# junit xml parser unit tests
# ===========================================================================

JUNIT_ALL_PASS = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="MyTests" tests="3" failures="0" time="0.5">
    <testcase name="test_alpha" classname="MyTests" time="0.1"/>
    <testcase name="test_beta" classname="MyTests" time="0.2"/>
    <testcase name="test_gamma" classname="MyTests" time="0.2"/>
  </testsuite>
</testsuites>
"""

JUNIT_ONE_FAIL = """\
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

JUNIT_BARE_TESTSUITE = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="Bare" tests="1" failures="0">
  <testcase name="only_test" classname="Bare"/>
</testsuite>
"""

JUNIT_MULTI_SUITE = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="Suite1" tests="2" failures="1">
    <testcase name="pass1" classname="Suite1"/>
    <testcase name="fail1" classname="Suite1">
      <failure message="boom"/>
    </testcase>
  </testsuite>
  <testsuite name="Suite2" tests="1" failures="0">
    <testcase name="pass2" classname="Suite2"/>
  </testsuite>
</testsuites>
"""

JUNIT_MALFORMED = "not xml at all"
JUNIT_EMPTY_SUITE = '<testsuites><testsuite name="Empty" tests="0"/></testsuites>'


class TestParseJunit:
    def test_all_pass(self):
        # frob:tests src/frob/process/parsers/junit.py::parse_junit_xml kind="unit"
        r = parse_junit_xml(JUNIT_ALL_PASS)
        assert r.passed
        assert len(r.tests) == 3

    def test_all_tests_pass(self):
        r = parse_junit_xml(JUNIT_ALL_PASS)
        assert all(t.passed for t in r.tests)

    def test_one_fail(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        assert not r.passed
        assert len(r.failed_tests) == 1

    def test_fail_name(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        assert r.failed_tests[0].name == "test_fail"

    def test_fail_message(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        assert "AssertionError" in (r.failed_tests[0].failure_message or "")

    def test_fail_text(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        assert r.failed_tests[0].failure_text is not None
        assert "42" in r.failed_tests[0].failure_text

    def test_skip(self):
        r = parse_junit_xml(JUNIT_SKIP)
        skipped = [t for t in r.tests if t.skipped]
        assert len(skipped) == 1

    def test_skip_not_in_failed(self):
        r = parse_junit_xml(JUNIT_SKIP)
        assert len(r.failed_tests) == 0

    def test_bare_testsuite_root(self):
        r = parse_junit_xml(JUNIT_BARE_TESTSUITE)
        assert len(r.tests) == 1
        assert r.tests[0].name == "only_test"

    def test_multi_suite(self):
        r = parse_junit_xml(JUNIT_MULTI_SUITE)
        assert len(r.tests) == 3
        assert len(r.failed_tests) == 1

    def test_tool_override(self):
        r = parse_junit_xml(JUNIT_ALL_PASS, tool="gtest")
        assert r.tool == "gtest"

    def test_default_tool_name(self):
        r = parse_junit_xml(JUNIT_ALL_PASS)
        assert r.tool == "junit"

    def test_malformed(self):
        r = parse_junit_xml(JUNIT_MALFORMED)
        assert not r.passed
        assert "malformed" in r.summary.lower()

    def test_empty_suite(self):
        r = parse_junit_xml(JUNIT_EMPTY_SUITE)
        assert r.tests == []

    def test_summary_has_counts(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        assert "1" in r.summary

    def test_as_text_shows_failure(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        text = r.as_text()
        assert "FAIL" in text
        assert "test_fail" in text

    def test_as_text_tool_header(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        assert "[junit]" in r.as_text()

    def test_as_json(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        data = json.loads(r.as_json())
        assert data["tool"] == "junit"
        assert len(data["tests"]) == 2

    def test_duration_stored(self):
        r = parse_junit_xml(JUNIT_ONE_FAIL)
        durations = [t.duration for t in r.tests if t.duration is not None]
        assert len(durations) > 0


# ===========================================================================
# frob parse CLI system tests (subprocess end-to-end)
# ===========================================================================

PYTEST_FAIL_CLI = """\
tests/test_foo.py::test_alpha PASSED
tests/test_foo.py::test_beta FAILED
============================== 1 failed, 1 passed in 0.3s ==============================
"""

RUFF_JSON_CLI = json.dumps(
    [
        {
            "cell": None,
            "code": "F401",
            "filename": "foo.py",
            "location": {"row": 1, "column": 1},
            "end_location": {"row": 1, "column": 5},
            "message": "unused import",
            "fix": None,
            "noqa_row": 1,
            "url": "x",
        }
    ]
)

TY_CLI = "error[incompatible-types] src/foo.py:1:1: bad"

CLANG_CLI = "src/foo.cpp:5:3: error: expected ';'\n"

JUNIT_CLI = """\
<?xml version="1.0"?>
<testsuites>
  <testsuite name="S" tests="1" failures="1">
    <testcase name="fail" classname="S">
      <failure message="oops"/>
    </testcase>
  </testsuite>
</testsuites>
"""


class TestParseCliPytest:
    def test_exits_zero(self):
        r = run("parse", "pytest", "--exit-code", "0", input=PYTEST_FAIL_CLI)
        assert r.returncode == 0

    def test_shows_failure(self):
        r = run("parse", "pytest", "--exit-code", "1", input=PYTEST_FAIL_CLI)
        assert "test_beta" in r.stdout or "FAIL" in r.stdout

    def test_shows_tool_name(self):
        r = run("parse", "pytest", "--exit-code", "0", input=PYTEST_FAIL_CLI)
        assert "pytest" in r.stdout

    def test_passthrough_nonzero_on_failure(self):
        r = run(
            "parse",
            "pytest",
            "--exit-code",
            "1",
            "--passthrough",
            input=PYTEST_FAIL_CLI,
        )
        assert r.returncode != 0

    def test_passthrough_zero_on_success(self):
        r = run(
            "parse",
            "pytest",
            "--exit-code",
            "0",
            "--passthrough",
            input=PYTEST_FAIL_CLI,
        )
        assert r.returncode == 0

    def test_json_output(self):
        r = run("parse", "pytest", "--json", "--exit-code", "1", input=PYTEST_FAIL_CLI)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["tool"] == "pytest"

    def test_from_file(self, tmp_path):
        f = tmp_path / "out.txt"
        f.write_text(PYTEST_FAIL_CLI)
        r = run("parse", "pytest", str(f), "--exit-code", "1")
        assert r.returncode == 0
        assert "test_beta" in r.stdout or "FAIL" in r.stdout


class TestParseCliRuff:
    def test_exits_zero(self):
        r = run("parse", "ruff", "--exit-code", "1", input=RUFF_JSON_CLI)
        assert r.returncode == 0

    def test_shows_code(self):
        r = run("parse", "ruff", "--exit-code", "1", input=RUFF_JSON_CLI)
        assert "F401" in r.stdout

    def test_json_output(self):
        r = run("parse", "ruff", "--json", "--exit-code", "1", input=RUFF_JSON_CLI)
        data = json.loads(r.stdout)
        assert data["tool"] == "ruff"

    def test_passthrough(self):
        r = run(
            "parse", "ruff", "--exit-code", "1", "--passthrough", input=RUFF_JSON_CLI
        )
        assert r.returncode != 0

    def test_clean_input(self):
        r = run("parse", "ruff", "--exit-code", "0", input="[]")
        assert r.returncode == 0
        assert "no issues" in r.stdout


class TestParseCliTy:
    def test_exits_zero(self):
        r = run("parse", "ty", "--exit-code", "1", input=TY_CLI)
        assert r.returncode == 0

    def test_shows_error(self):
        r = run("parse", "ty", "--exit-code", "1", input=TY_CLI)
        assert "incompatible-types" in r.stdout or "foo.py" in r.stdout

    def test_json_output(self):
        r = run("parse", "ty", "--json", "--exit-code", "1", input=TY_CLI)
        data = json.loads(r.stdout)
        assert data["tool"] == "ty"


class TestParseCliClang:
    def test_exits_zero(self):
        r = run("parse", "clang", "--exit-code", "1", input=CLANG_CLI)
        assert r.returncode == 0

    def test_shows_error(self):
        r = run("parse", "clang", "--exit-code", "1", input=CLANG_CLI)
        assert "error" in r.stdout.lower()

    def test_from_file(self, tmp_path):
        f = tmp_path / "build.log"
        f.write_text(CLANG_CLI)
        r = run("parse", "clang", str(f), "--exit-code", "1")
        assert r.returncode == 0
        assert "error" in r.stdout.lower()

    def test_gcc_alias(self):
        r = run("parse", "gcc", "--exit-code", "1", input=CLANG_CLI)
        assert r.returncode == 0

    def test_json_output(self):
        r = run("parse", "clang", "--json", "--exit-code", "1", input=CLANG_CLI)
        data = json.loads(r.stdout)
        assert data["tool"] == "clang"


class TestParseCliJunit:
    def test_exits_zero(self):
        r = run("parse", "junit", "--exit-code", "1", input=JUNIT_CLI)
        assert r.returncode == 0

    def test_shows_failure(self):
        r = run("parse", "junit", "--exit-code", "1", input=JUNIT_CLI)
        assert "FAIL" in r.stdout

    def test_from_file(self, tmp_path):
        f = tmp_path / "results.xml"
        f.write_text(JUNIT_CLI)
        r = run("parse", "junit", str(f), "--exit-code", "1")
        assert r.returncode == 0

    def test_json_output(self):
        r = run("parse", "junit", "--json", "--exit-code", "1", input=JUNIT_CLI)
        data = json.loads(r.stdout)
        assert data["tool"] == "junit"


class TestParseCliMisc:
    def test_unknown_tool_exits_nonzero(self):
        r = run("parse", "unknown_xyz_tool")
        assert r.returncode != 0

    def test_verbose_flag_accepted(self):
        r = run(
            "parse", "pytest", "--exit-code", "0", "--verbose", input=PYTEST_FAIL_CLI
        )
        assert r.returncode == 0

    def test_no_exit_code_defaults_zero(self):
        r = run("parse", "ruff", input="[]")
        assert r.returncode == 0

    def test_passthrough_propagates_on_nonzero(self):
        r = run("parse", "ty", "--exit-code", "1", "--passthrough", input=TY_CLI)
        assert r.returncode != 0


class TestSummarizeSeverity:
    def test_empty_default(self):
        # frob:tests src/frob/process/parsers/common.py::summarize_severity kind="unit"
        from frob.process.parsers.common import summarize_severity

        assert summarize_severity([]) == "no issues"

    def test_empty_custom(self):
        from frob.process.parsers.common import summarize_severity

        assert summarize_severity([], empty="clean") == "clean"

    def test_errors_and_warnings(self):
        from frob.process.parsers.common import Diagnostic, summarize_severity

        diags = [Diagnostic(severity="error"), Diagnostic(severity="warning")]
        assert summarize_severity(diags) == "1 errors, 1 warnings"

    def test_collapse_errorless(self):
        from frob.process.parsers.common import Diagnostic, summarize_severity

        diags = [Diagnostic(severity="warning"), Diagnostic(severity="warning")]
        assert summarize_severity(diags, collapse_errorless=True) == "2 warnings"

    def test_no_collapse_shows_both(self):
        from frob.process.parsers.common import Diagnostic, summarize_severity

        diags = [Diagnostic(severity="warning")]
        assert summarize_severity(diags) == "0 errors, 1 warnings"
