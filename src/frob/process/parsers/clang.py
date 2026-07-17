"""
Clang/GCC diagnostic parser.

Parses the standard GCC-format diagnostic output:
  file.cpp:line:col: error: message
  file.cpp:line:col: warning: message [-Wflag]

Also handles clang's note lines and "In function 'X':" context lines.
"""

from __future__ import annotations

import re
from typing import cast

from frob.process.parsers.common import Diagnostic, Severity, ToolResult

_DIAG_LINE = re.compile(
    r"^(.*?):(\d+):(\d+):\s+(error|warning|note|fatal error):\s+(.*)$"
)
_CONTEXT_LINE = re.compile(r"^(?:In function|In member function|At top level)")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


# frob:doc docs/process.md#public-api
def parse_clang(stdout: str, exit_code: int = 0, tool: str = "clang") -> ToolResult:
    diagnostics: list[Diagnostic] = []

    for raw_line in stdout.splitlines():
        line = _ANSI.sub("", raw_line)
        m = _DIAG_LINE.match(line)
        if not m:
            continue
        file, row, col, sev_str, msg = m.groups()
        # Strip trailing flag annotations like [-Wunused-variable]
        msg = re.sub(r"\s+\[-W[^\]]+\]$", "", msg).strip()
        sev_str = sev_str.replace("fatal error", "error")
        diagnostics.append(
            Diagnostic(
                file=file,
                line=int(row),
                col=int(col),
                severity=_severity(sev_str),
                message=msg,
            )
        )

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")

    if errors or warnings:
        summary = f"{errors} errors, {warnings} warnings"
    else:
        summary = "ok" if exit_code == 0 else "build failed (no diagnostics captured)"

    return ToolResult(
        tool=tool,
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )


def _severity(s: str) -> Severity:
    if s in ("error", "warning", "note", "info"):
        return cast(Severity, s)
    return "error"
