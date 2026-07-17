"""
ruff output parser.

Supports both the default text format and JSON format (--output-format json).
JSON format is preferred for reliability; use `ruff check --output-format json`.
"""

from __future__ import annotations

import json
import re

from frob.process.parsers.common import Diagnostic, ToolResult, summarize_severity

_TEXT_LINE = re.compile(r"^(.*?):(\d+):(\d+):\s+([A-Z]\d+)\s+(.*)$")


# frob:ticket T-0045
def _ruff_json_diagnostic(item: dict) -> Diagnostic:
    """One ruff JSON item into a Diagnostic (E/F codes are errors)."""
    loc = item.get("location", {})
    code = item.get("code", "")
    return Diagnostic(
        file=item.get("filename"),
        line=loc.get("row"),
        col=loc.get("column"),
        severity="error" if code.startswith(("E", "F")) else "warning",
        code=code,
        message=item.get("message", ""),
    )


# frob:doc docs/process.md#public-api
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

    diagnostics = [_ruff_json_diagnostic(item) for item in items]
    summary = summarize_severity(diagnostics, collapse_errorless=True)
    return ToolResult(
        tool="ruff",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )


# frob:doc docs/process.md#public-api
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

    summary = summarize_severity(diagnostics)

    return ToolResult(
        tool="ruff",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )


# frob:doc docs/process.md#public-api
def parse_ruff(stdout: str, exit_code: int = 0) -> ToolResult:
    """Auto-detect JSON vs text format."""
    stripped = stdout.strip()
    if stripped.startswith("["):
        return parse_ruff_json(stdout, exit_code)
    return parse_ruff_text(stdout, exit_code)
