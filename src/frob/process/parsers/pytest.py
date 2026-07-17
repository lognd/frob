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


# frob:doc docs/process.md#public-api
def parse_pytest(stdout: str, exit_code: int = 0) -> ToolResult:
    lines = stdout.splitlines()

    cases: list[TestCase] = []
    diagnostics: list[Diagnostic] = []
    summary = ""
    current_fail_name: str | None = None
    current_fail_lines: list[str] = []
    in_failures = False

    def flush_failure() -> None:
        nonlocal current_fail_name, current_fail_lines
        if current_fail_name and cases:
            # Find the matching test case and attach failure text
            for c in reversed(cases):
                if c.name == current_fail_name or current_fail_name.endswith(c.name):
                    # Extract the E-lines as the compact failure message
                    e_lines = [
                        ln[2:].strip()
                        for ln in current_fail_lines
                        if ln.startswith("E ")
                    ]
                    if e_lines:
                        object.__setattr__(c, "failure_message", e_lines[0])
                        object.__setattr__(c, "failure_text", "\n".join(e_lines))
                    break
        current_fail_name = None
        current_fail_lines = []

    for line in lines:
        # Detect failure section header
        fail_match = _FAIL_HEADER.match(line)
        if fail_match:
            flush_failure()
            in_failures = True
            current_fail_name = fail_match.group(1)
            continue

        if in_failures:
            current_fail_lines.append(line)
            # Diagnostic: file:line: message in failure block
            loc_match = _LOCATION_LINE.match(line)
            if loc_match and "AssertionError" not in line:
                diagnostics.append(
                    Diagnostic(
                        file=loc_match.group(1),
                        line=int(loc_match.group(2)),
                        severity="error",
                        message=loc_match.group(3).strip(),
                    )
                )
            continue

        # Status line: "tests/foo.py::test_bar PASSED"
        status_match = _STATUS_LINE.match(line)
        if status_match:
            node_id = status_match.group(1)
            status = status_match.group(2)
            parts = node_id.rsplit("::", 1)
            name = parts[-1] if parts else node_id
            suite = parts[0] if len(parts) > 1 else ""
            cases.append(
                TestCase(
                    suite=suite,
                    name=name,
                    passed=status == "PASSED",
                    skipped=status == "SKIPPED",
                )
            )
            continue

        # Final summary line
        if re.match(r"=+ .* =+", line):
            flush_failure()
            in_failures = False
            inner = re.sub(r"=+\s*", "", line).strip()
            if any(k in inner for k in ("failed", "passed", "error", "warning")):
                summary = inner

    flush_failure()

    if not summary:
        n_fail = sum(1 for c in cases if not c.passed and not c.skipped)
        n_pass = sum(1 for c in cases if c.passed)
        summary = f"{n_fail} failed, {n_pass} passed" if n_fail else f"{n_pass} passed"

    return ToolResult(
        tool="pytest",
        exit_code=exit_code,
        tests=cases,
        diagnostics=diagnostics,
        summary=summary,
    )
