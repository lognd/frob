"""
JUnit XML parser -- shared by pytest (--junit-xml), gtest, Catch2, CTest.

Adapted from lograder.process.parsers.junit.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from frob.process.parsers.common import TestCase, ToolResult


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

    if root.tag == "testsuites":
        suites = list(root.iter("testsuite"))
    elif root.tag == "testsuite":
        suites = [root] + [el for el in root.iter("testsuite") if el is not root]
    else:
        suites = list(root.iter("testsuite"))

    cases: list[TestCase] = []
    for suite in suites:
        suite_name = suite.get("name", "")
        for tc in suite.findall("testcase"):
            name = tc.get("name", "")
            raw_time = tc.get("time")
            duration = float(raw_time) if raw_time is not None else None

            failure_el = tc.find("failure")
            error_el = tc.find("error")
            skipped_el = tc.find("skipped")

            failure_message = None
            failure_text = None
            if failure_el is not None:
                failure_message = failure_el.get("message") or ""
                failure_text = (failure_el.text or "").strip()
            elif error_el is not None:
                failure_message = error_el.get("message") or ""
                failure_text = (error_el.text or "").strip()

            cases.append(TestCase(
                suite=suite_name,
                name=name,
                passed=(failure_el is None and error_el is None and skipped_el is None),
                skipped=skipped_el is not None,
                duration=duration,
                failure_message=failure_message,
                failure_text=failure_text,
            ))

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

    return ToolResult(
        tool=tool,
        exit_code=1 if failed else 0,
        tests=cases,
        summary=summary,
    )
