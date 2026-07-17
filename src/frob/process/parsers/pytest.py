"""
pytest terminal output parser.

Parses the text output of `pytest` (no plugins required).
For structured output, prefer JUnit XML via `pytest --junit-xml=out.xml`
and use the junit parser instead.

Recognizes:
  - PASSED / FAILED / ERROR / SKIPPED lines
  - Short test IDs (file::class::test)
  - The summary line at the end: "X failed, Y passed in Zs"
  - Failure sections from the "=== FAILURES ===" block
"""

from __future__ import annotations

import re

from frob.process.parsers.common import Diagnostic, TestCase, ToolResult

_RESULT_LINE = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED)\s+(.*?)(?:\s+-\s+(.*))?$")
_STATUS_LINE = re.compile(
    r"^(tests/\S+|src/\S+|\S+\.py::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)"
)
_SUMMARY_LINE = re.compile(r"=+\s+(.*?)\s+=+\s*$")
_SHORT_SUMMARY = re.compile(
    r"(\d+)\s+failed|(\d+)\s+passed|(\d+)\s+error|(\d+)\s+skipped|in\s+([\d.]+)s"
)
_FAIL_HEADER = re.compile(r"^_{5,}\s+(.*?)\s+_{5,}$")
_ERROR_LINE = re.compile(r"^E\s+(.*)$")
_LOCATION_LINE = re.compile(r"^(.*\.py):(\d+):\s+(.*)$")


# frob:ticket T-0045
def _e_lines(fail_lines: list[str]) -> list[str]:
    """The stripped `E ...` assertion lines of a pytest failure block."""
    return [ln[2:].strip() for ln in fail_lines if ln.startswith("E ")]


# frob:ticket T-0045
def _attach_failure(
    cases: list[TestCase], fail_name: str | None, fail_lines: list[str]
) -> None:
    """Attach the E-line failure text of a `=== FAILURES ===` block to its case."""
    if not fail_name or not cases:
        return
    e_lines = _e_lines(fail_lines)
    for c in reversed(cases):
        if c.name == fail_name or fail_name.endswith(c.name):
            if e_lines:
                object.__setattr__(c, "failure_message", e_lines[0])
                object.__setattr__(c, "failure_text", "\n".join(e_lines))
            break


# frob:ticket T-0045
def _testcase_from_status(match: re.Match) -> TestCase:
    """Build a TestCase from a `tests/foo.py::test_bar PASSED` status line match."""
    node_id, status = match.group(1), match.group(2)
    parts = node_id.rsplit("::", 1)
    return TestCase(
        suite=parts[0] if len(parts) > 1 else "",
        name=parts[-1] if parts else node_id,
        passed=status == "PASSED",
        skipped=status == "SKIPPED",
    )


# frob:ticket T-0045
def _location_diagnostic(line: str) -> Diagnostic | None:
    """A `file.py:line: message` diagnostic from a failure-block line, if any."""
    loc_match = _LOCATION_LINE.match(line)
    if loc_match is None or "AssertionError" in line:
        return None
    return Diagnostic(
        file=loc_match.group(1),
        line=int(loc_match.group(2)),
        severity="error",
        message=loc_match.group(3).strip(),
    )


# frob:ticket T-0045
def _fallback_summary(cases: list[TestCase]) -> str:
    """Count-based summary when pytest printed no recognizable summary line."""
    n_fail = sum(1 for c in cases if not c.passed and not c.skipped)
    n_pass = sum(1 for c in cases if c.passed)
    return f"{n_fail} failed, {n_pass} passed" if n_fail else f"{n_pass} passed"


# frob:ticket T-0045
def _summary_marker(line: str) -> str | None:
    """The inner text of a `=== N passed ... ===` pytest summary line, else None."""
    if not re.match(r"=+ .* =+", line):
        return None
    inner = re.sub(r"=+\s*", "", line).strip()
    if any(k in inner for k in ("failed", "passed", "error", "warning")):
        return inner
    return ""


# frob:ticket T-0045
def _scan_pytest_output(
    stdout: str,
) -> tuple[list[TestCase], list[Diagnostic], str]:
    """Scan pytest terminal output into (cases, diagnostics, summary line)."""
    cases: list[TestCase] = []
    diagnostics: list[Diagnostic] = []
    summary = ""
    fail_name: str | None = None
    fail_lines: list[str] = []
    in_failures = False

    for line in stdout.splitlines():
        fail_match = _FAIL_HEADER.match(line)
        if fail_match:
            _attach_failure(cases, fail_name, fail_lines)
            in_failures, fail_name, fail_lines = True, fail_match.group(1), []
        elif in_failures:
            fail_lines.append(line)
            diag = _location_diagnostic(line)
            if diag is not None:
                diagnostics.append(diag)
        elif status_match := _STATUS_LINE.match(line):
            cases.append(_testcase_from_status(status_match))
        elif (marker := _summary_marker(line)) is not None:
            _attach_failure(cases, fail_name, fail_lines)
            in_failures, fail_name, fail_lines = False, None, []
            summary = marker or summary

    _attach_failure(cases, fail_name, fail_lines)
    return cases, diagnostics, summary


# frob:doc docs/process.md#public-api
def parse_pytest(stdout: str, exit_code: int = 0) -> ToolResult:
    cases, diagnostics, summary = _scan_pytest_output(stdout)
    return ToolResult(
        tool="pytest",
        exit_code=exit_code,
        tests=cases,
        diagnostics=diagnostics,
        summary=summary or _fallback_summary(cases),
    )
