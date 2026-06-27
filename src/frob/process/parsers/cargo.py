"""
Cargo output parser (check, clippy, test, build).

Supports cargo's JSON message format (`--message-format json`) for
check/clippy, and plain text for cargo test.
"""

from __future__ import annotations

import json
import re

from frob.process.parsers.common import Diagnostic, Severity, TestCase, ToolResult

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# cargo test output: "test foo::bar ... FAILED" or "FAILED" summary
_TEST_LINE = re.compile(r"^test (.+?) \.\.\. (ok|FAILED|ignored)$")
_FAILURE_SEP = re.compile(r"^---- (.+?) stdout ----$")
_PANIC_LINE = re.compile(r"^thread '.*?' panicked at '(.*?)'")


def parse_cargo(stdout: str, exit_code: int = 0, tool: str = "cargo") -> ToolResult:
    """
    Unified cargo parser. Detects JSON message format automatically;
    falls back to plain text parsing for cargo test output.
    """
    text = _ANSI.sub("", stdout)
    lines = text.splitlines()

    # Detect JSON message format (cargo check/clippy --message-format json)
    json_lines = [l for l in lines if l.startswith("{")]
    if json_lines:
        return _parse_cargo_json(json_lines, exit_code, tool)

    # Plain text: likely cargo test or cargo build
    return _parse_cargo_text(lines, exit_code, tool)


def _parse_cargo_json(json_lines: list[str], exit_code: int, tool: str) -> ToolResult:
    diagnostics: list[Diagnostic] = []

    for raw in json_lines:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if msg.get("reason") != "compiler-message":
            continue
        m = msg.get("message", {})
        level = m.get("level", "")
        if level not in ("error", "warning"):
            continue
        spans = m.get("spans", [])
        primary = next((s for s in spans if s.get("is_primary")), spans[0] if spans else None)
        file = primary.get("file_name") if primary else None
        line = primary.get("line_start") if primary else None
        col = primary.get("column_start") if primary else None
        code_obj = m.get("code")
        code = code_obj.get("code") if code_obj else None
        text = m.get("rendered") or m.get("message", "")
        # Use first line of rendered output as message
        message = text.splitlines()[0].strip() if text else m.get("message", "")
        diagnostics.append(Diagnostic(
            file=file, line=line, col=col,
            severity="error" if level == "error" else "warning",
            code=code, message=message,
        ))

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = len(diagnostics) - errors
    summary = f"{errors} errors, {warnings} warnings" if errors else (
        f"{warnings} warnings" if warnings else "ok"
    )
    return ToolResult(tool=tool, exit_code=exit_code, diagnostics=diagnostics, summary=summary)


def _parse_cargo_text(lines: list[str], exit_code: int, tool: str) -> ToolResult:
    tests: list[TestCase] = []
    diagnostics: list[Diagnostic] = []
    failures: dict[str, list[str]] = {}
    current_failure: str | None = None

    for line in lines:
        m = _TEST_LINE.match(line)
        if m:
            name, status = m.groups()
            tests.append(TestCase(name=name, passed=(status == "ok"), skipped=(status == "ignored")))
            continue

        m2 = _FAILURE_SEP.match(line)
        if m2:
            current_failure = m2.group(1)
            failures[current_failure] = []
            continue

        if current_failure is not None:
            if line.strip() == "" and current_failure in failures and len(failures[current_failure]) > 2:
                current_failure = None
            else:
                failures[current_failure].append(line)

        # Also pick up compiler errors in plain text
        if line.startswith("error[") or line.startswith("error:"):
            diagnostics.append(Diagnostic(severity="error", message=line.strip()))

    # Attach failure output to test cases
    enriched: list[TestCase] = []
    for t in tests:
        if not t.passed and t.name in failures:
            lines_out = failures[t.name]
            msg = next((l.strip() for l in lines_out if l.strip()), None)
            enriched.append(TestCase(
                name=t.name, passed=False,
                failure_message=msg,
                failure_text="\n".join(lines_out[:20]),
            ))
        else:
            enriched.append(t)

    n_fail = sum(1 for t in enriched if not t.passed and not t.skipped)
    n_pass = sum(1 for t in enriched if t.passed)
    n_skip = sum(1 for t in enriched if t.skipped)
    parts = []
    if n_fail:
        parts.append(f"{n_fail} failed")
    if n_pass:
        parts.append(f"{n_pass} passed")
    if n_skip:
        parts.append(f"{n_skip} ignored")
    summary = ", ".join(parts) if parts else ("ok" if exit_code == 0 else "failed")
    return ToolResult(tool=tool, exit_code=exit_code, tests=enriched, diagnostics=diagnostics, summary=summary)
