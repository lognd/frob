"""
tsc (TypeScript compiler) output parser.

`tsc --noEmit` emits one diagnostic per line:
  file.ts(10,5): error TS2322: Type 'string' is not assignable to type 'number'.
"""

from __future__ import annotations

import re

from frob.process.parsers.common import Diagnostic, ToolResult

_DIAG = re.compile(r"^(.*?)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.*)$")
_SUMMARY_LINE = re.compile(r"^Found (\d+) error")


def parse_tsc(stdout: str, exit_code: int = 0) -> ToolResult:
    """Parse `tsc --noEmit` output into a ToolResult."""
    diagnostics: list[Diagnostic] = []
    summary_override: str | None = None

    for raw in stdout.splitlines():
        line = raw.strip()
        m = _DIAG.match(line)
        if m:
            file, row, col, sev, code, msg = m.groups()
            diagnostics.append(
                Diagnostic(
                    file=file,
                    line=int(row),
                    col=int(col),
                    severity="error" if sev == "error" else "warning",
                    code=code,
                    message=msg.strip(),
                )
            )
            continue
        ms = _SUMMARY_LINE.match(line)
        if ms:
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
        tool="tsc",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )
