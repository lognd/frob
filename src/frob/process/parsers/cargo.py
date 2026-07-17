"""
Cargo output parser (check, clippy, test, build).

Supports cargo's JSON message format (`--message-format json`) for
check/clippy, and plain text for cargo test.
"""

from __future__ import annotations

import json
import re

from frob.process.parsers.common import (
    Diagnostic,
    TestCase,
    ToolResult,
    summarize_severity,
)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# cargo test output: "test foo::bar ... FAILED" or "FAILED" summary
_TEST_LINE = re.compile(r"^test (.+?) \.\.\. (ok|FAILED|ignored)$")
_FAILURE_SEP = re.compile(r"^---- (.+?) stdout ----$")
_PANIC_LINE = re.compile(r"^thread '.*?' panicked at '(.*?)'")


# frob:doc docs/process.md#public-api
def parse_cargo(stdout: str, exit_code: int = 0, tool: str = "cargo") -> ToolResult:
    """
    Unified cargo parser. Detects JSON message format automatically;
    falls back to plain text parsing for cargo test output.
    """
    text = _ANSI.sub("", stdout)
    lines = text.splitlines()

    # Detect JSON message format (cargo check/clippy --message-format json)
    json_lines = [ln for ln in lines if ln.startswith("{")]
    if json_lines:
        return _parse_cargo_json(json_lines, exit_code, tool)

    # Plain text: likely cargo test or cargo build
    return _parse_cargo_text(lines, exit_code, tool)


# frob:ticket T-0045
def _cargo_json_diagnostic(raw: str) -> Diagnostic | None:
    """A Diagnostic from one cargo `compiler-message` JSON line, or None."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if msg.get("reason") != "compiler-message":
        return None
    m = msg.get("message", {})
    level = m.get("level", "")
    if level not in ("error", "warning"):
        return None
    spans = m.get("spans", [])
    primary = next(
        (s for s in spans if s.get("is_primary")), spans[0] if spans else None
    )
    code_obj = m.get("code")
    text = m.get("rendered") or m.get("message", "")
    return Diagnostic(
        file=primary.get("file_name") if primary else None,
        line=primary.get("line_start") if primary else None,
        col=primary.get("column_start") if primary else None,
        severity="error" if level == "error" else "warning",
        code=code_obj.get("code") if code_obj else None,
        message=text.splitlines()[0].strip() if text else m.get("message", ""),
    )


def _parse_cargo_json(json_lines: list[str], exit_code: int, tool: str) -> ToolResult:
    diagnostics: list[Diagnostic] = []
    for raw in json_lines:
        diag = _cargo_json_diagnostic(raw)
        if diag is not None:
            diagnostics.append(diag)

    summary = summarize_severity(diagnostics, empty="ok", collapse_errorless=True)
    return ToolResult(
        tool=tool, exit_code=exit_code, diagnostics=diagnostics, summary=summary
    )


# frob:ticket T-0045
def _enrich_with_failures(
    tests: list[TestCase], failures: dict[str, list[str]]
) -> list[TestCase]:
    """Attach captured failure output to each failed cargo test case."""
    enriched: list[TestCase] = []
    for t in tests:
        if not t.passed and t.name in failures:
            lines_out = failures[t.name]
            msg = next((ln.strip() for ln in lines_out if ln.strip()), None)
            enriched.append(
                TestCase(
                    name=t.name,
                    passed=False,
                    failure_message=msg,
                    failure_text="\n".join(lines_out[:20]),
                )
            )
        else:
            enriched.append(t)
    return enriched


# frob:ticket T-0045
def _cargo_test_summary(tests: list[TestCase], exit_code: int) -> str:
    """Compact `N failed, M passed, K ignored` summary for cargo test cases."""
    n_fail = sum(1 for t in tests if not t.passed and not t.skipped)
    n_pass = sum(1 for t in tests if t.passed)
    n_skip = sum(1 for t in tests if t.skipped)
    parts = []
    if n_fail:
        parts.append(f"{n_fail} failed")
    if n_pass:
        parts.append(f"{n_pass} passed")
    if n_skip:
        parts.append(f"{n_skip} ignored")
    return ", ".join(parts) if parts else ("ok" if not exit_code else "failed")


# frob:ticket T-0045
def _accumulate_failure(
    line: str, current_failure: str, failures: dict[str, list[str]]
) -> str | None:
    """Append `line` to the open failure block, or end it on a blank separator."""
    if line.strip() == "" and len(failures.get(current_failure, [])) > 2:
        return None
    failures[current_failure].append(line)
    return current_failure


# frob:ticket T-0045
def _collect_cargo_text(
    lines: list[str],
) -> tuple[list[TestCase], list[Diagnostic], dict[str, list[str]]]:
    """Scan cargo test text into (test cases, compiler diagnostics, failure blocks)."""
    tests: list[TestCase] = []
    diagnostics: list[Diagnostic] = []
    failures: dict[str, list[str]] = {}
    current_failure: str | None = None

    for line in lines:
        m = _TEST_LINE.match(line)
        if m:
            name, status = m.groups()
            tests.append(
                TestCase(
                    name=name, passed=(status == "ok"), skipped=(status == "ignored")
                )
            )
            continue

        m2 = _FAILURE_SEP.match(line)
        if m2:
            current_failure = m2.group(1)
            failures[current_failure] = []
            continue

        if current_failure is not None:
            current_failure = _accumulate_failure(line, current_failure, failures)

        if line.startswith("error[") or line.startswith("error:"):
            diagnostics.append(Diagnostic(severity="error", message=line.strip()))

    return tests, diagnostics, failures


def _parse_cargo_text(lines: list[str], exit_code: int, tool: str) -> ToolResult:
    tests, diagnostics, failures = _collect_cargo_text(lines)
    enriched = _enrich_with_failures(tests, failures)
    summary = _cargo_test_summary(enriched, exit_code)
    return ToolResult(
        tool=tool,
        exit_code=exit_code,
        tests=enriched,
        diagnostics=diagnostics,
        summary=summary,
    )
