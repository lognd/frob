"""
JUnit XML parser -- shared by pytest (--junit-xml), gtest, Catch2, CTest.

Adapted from lograder.process.parsers.junit.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from frob.process.parsers.common import TestCase, ToolResult


# frob:ticket T-0045
def _extract_suites(root: ET.Element) -> list[ET.Element]:
    """All `<testsuite>` elements, whether the root is a suites-wrapper or one."""
    if root.tag == "testsuite":
        return [root] + [el for el in root.iter("testsuite") if el is not root]
    return list(root.iter("testsuite"))


# frob:ticket T-0045
def _parse_testcase(suite_name: str, tc: ET.Element) -> TestCase:
    """One `<testcase>` element into a TestCase (failure/error/skipped aware)."""
    raw_time = tc.get("time")
    failure_el = tc.find("failure")
    error_el = tc.find("error")
    skipped_el = tc.find("skipped")

    failure_message = None
    failure_text = None
    detail_el = failure_el if failure_el is not None else error_el
    if detail_el is not None:
        failure_message = detail_el.get("message") or ""
        failure_text = (detail_el.text or "").strip()

    return TestCase(
        suite=suite_name,
        name=tc.get("name", ""),
        passed=(failure_el is None and error_el is None and skipped_el is None),
        skipped=skipped_el is not None,
        duration=float(raw_time) if raw_time is not None else None,
        failure_message=failure_message,
        failure_text=failure_text,
    )


# frob:ticket T-0045
def _summarize_cases(cases: list[TestCase]) -> tuple[int, str]:
    """Return `(failed_count, summary_line)` for parsed test cases."""
    passed = sum(1 for c in cases if c.passed)
    failed = sum(1 for c in cases if not c.passed and not c.skipped)
    skipped = sum(1 for c in cases if c.skipped)
    total_time = sum(c.duration or 0 for c in cases)

    parts = []
    if failed:
        parts.append(f"{failed} failed")
    parts.append(f"{passed} passed")
    if skipped:
        parts.append(f"{skipped} skipped")
    parts.append(f"({total_time:.2f}s)")
    summary = ", ".join(parts[:3]) + " " + parts[-1] if parts else "no tests"
    return failed, summary


# frob:doc docs/process.md#public-api
def parse_junit_xml(content: str, tool: str = "junit") -> ToolResult:
    """Parse JUnit XML into a ToolResult."""
    try:
        root = ET.fromstring(content.strip())
    except ET.ParseError as exc:
        return ToolResult(
            tool=tool,
            exit_code=1,
            summary=f"malformed JUnit XML: {exc}",
        )

    cases: list[TestCase] = []
    for suite in _extract_suites(root):
        suite_name = suite.get("name", "")
        for tc in suite.findall("testcase"):
            cases.append(_parse_testcase(suite_name, tc))

    failed, summary = _summarize_cases(cases)
    return ToolResult(
        tool=tool,
        exit_code=1 if failed else 0,
        tests=cases,
        summary=summary,
    )
