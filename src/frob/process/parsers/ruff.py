"""
ruff output parser.

Supports both the default text format and JSON format (--output-format json).
JSON format is preferred for reliability; use `ruff check --output-format json`.
"""

from __future__ import annotations

import json
import re

from frob.process.parsers.common import Diagnostic, ToolResult

_TEXT_LINE = re.compile(r"^(.*?):(\d+):(\d+):\s+([A-Z]\d+)\s+(.*)$")


def parse_ruff_json(stdout: str, exit_code: int = 0) -> ToolResult:
    """Parse `ruff check --output-format json` output."""
    try:
        items = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return ToolResult(
            tool="ruff",
            exit_code=1,
            summary=f"malformed JSON: {exc}",
        )

    diagnostics: list[Diagnostic] = []
    for item in items:
        loc = item.get("location", {})
        # ruff severity: errors are fixable/unfixable; treat all as warnings
        # unless they are in the "E" or "F" category which are errors
        code = item.get("code", "")
        severity = "error" if code.startswith(("E", "F")) else "warning"
        diagnostics.append(
            Diagnostic(
                file=item.get("filename"),
                line=loc.get("row"),
                col=loc.get("column"),
                severity=severity,
                code=code,
                message=item.get("message", ""),
            )
        )

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")
    if errors or warnings:
        summary = (
            f"{errors} errors, {warnings} warnings"
            if errors
            else f"{warnings} warnings"
        )
    else:
        summary = "no issues"

    return ToolResult(
        tool="ruff",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )


def parse_ruff_text(stdout: str, exit_code: int = 0) -> ToolResult:
    """Parse default `ruff check` text output."""
    diagnostics: list[Diagnostic] = []
    for line in stdout.splitlines():
        m = _TEXT_LINE.match(line.strip())
        if m:
            file, row, col, code, msg = m.groups()
            severity = "error" if code.startswith(("E", "F")) else "warning"
            diagnostics.append(
                Diagnostic(
                    file=file,
                    line=int(row),
                    col=int(col),
                    severity=severity,
                    code=code,
                    message=msg.strip(),
                )
            )

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")
    summary = (
        f"{errors} errors, {warnings} warnings" if errors or warnings else "no issues"
    )

    return ToolResult(
        tool="ruff",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )


def parse_ruff(stdout: str, exit_code: int = 0) -> ToolResult:
    """Auto-detect JSON vs text format."""
    stripped = stdout.strip()
    if stripped.startswith("["):
        return parse_ruff_json(stdout, exit_code)
    return parse_ruff_text(stdout, exit_code)
