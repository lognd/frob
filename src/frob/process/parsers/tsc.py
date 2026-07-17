"""
tsc (TypeScript compiler) output parser.

`tsc --noEmit` emits one diagnostic per line:
  file.ts(10,5): error TS2322: Type 'string' is not assignable to type 'number'.
"""

from __future__ import annotations

import re

from frob.process.parsers.common import Diagnostic, ToolResult, summarize_severity

_DIAG = re.compile(r"^(.*?)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.*)$")
_SUMMARY_LINE = re.compile(r"^Found (\d+) error")


# frob:ticket T-0045
def _tsc_diagnostic(m: re.Match) -> Diagnostic:
    """One `tsc` diagnostic-line match into a Diagnostic."""
    file, row, col, sev, code, msg = m.groups()
    return Diagnostic(
        file=file,
        line=int(row),
        col=int(col),
        severity="error" if sev == "error" else "warning",
        code=code,
        message=msg.strip(),
    )


# frob:doc docs/process.md#public-api
def parse_tsc(stdout: str, exit_code: int = 0) -> ToolResult:
    """Parse `tsc --noEmit` output into a ToolResult."""
    diagnostics: list[Diagnostic] = []
    summary_override: str | None = None

    for raw in stdout.splitlines():
        line = raw.strip()
        m = _DIAG.match(line)
        if m:
            diagnostics.append(_tsc_diagnostic(m))
            continue
        if _SUMMARY_LINE.match(line):
            summary_override = line

    summary = summary_override or summarize_severity(diagnostics)

    return ToolResult(
        tool="tsc",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )
