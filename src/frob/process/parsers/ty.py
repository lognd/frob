"""
ty (Astral's type checker) output parser.

ty outputs lines in the format:
  error[<code>] file.py:<line>:<col>: <message>
  warning[<code>] file.py:<line>:<col>: <message>

or with ANSI codes stripped:
  error[incompatible-types] src/foo.py:23:5: Argument of type "str" is not assignable to "int"
"""
from __future__ import annotations

import re

from frob.process.parsers.common import Diagnostic, Severity, ToolResult

_DIAG_LINE = re.compile(
    r"^(error|warning|info|note)\[([^\]]+)\]\s+(.*?):(\d+):(\d+):\s+(.*)$"
)
# Simpler format without bracket code
_DIAG_LINE_SIMPLE = re.compile(
    r"^(error|warning|info|note)\s+(.*?):(\d+):(\d+):\s+(.*)$"
)
_SUMMARY_LINE = re.compile(r"^Found (\d+) error")
# Strip ANSI escape codes
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def parse_ty(stdout: str, exit_code: int = 0) -> ToolResult:
    diagnostics: list[Diagnostic] = []
    summary_override: str | None = None

    for raw_line in stdout.splitlines():
        line = _ANSI.sub("", raw_line).strip()

        m = _DIAG_LINE.match(line)
        if m:
            severity_str, code, file, row, col, msg = m.groups()
            diagnostics.append(Diagnostic(
                file=file,
                line=int(row),
                col=int(col),
                severity=_severity(severity_str),
                code=code,
                message=msg.strip(),
            ))
            continue

        m2 = _DIAG_LINE_SIMPLE.match(line)
        if m2:
            severity_str, file, row, col, msg = m2.groups()
            diagnostics.append(Diagnostic(
                file=file,
                line=int(row),
                col=int(col),
                severity=_severity(severity_str),
                message=msg.strip(),
            ))
            continue

        m3 = _SUMMARY_LINE.match(line)
        if m3:
            summary_override = line

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")

    if summary_override:
        summary = summary_override
    elif errors or warnings:
        summary = f"{errors} errors, {warnings} warnings"
    else:
        summary = "no issues"

    return ToolResult(
        tool="ty",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )


def _severity(s: str) -> Severity:
    if s in ("error", "warning", "note", "info"):
        return s  # type: ignore[return-value]
    return "error"
