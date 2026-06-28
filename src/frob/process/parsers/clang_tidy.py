"""
clang-tidy output parser.

clang-tidy emits GCC-style diagnostics with check names in brackets:
  file.cpp:10:5: warning: ... [check-name]
"""

from __future__ import annotations

import re

from frob.process.parsers.common import Diagnostic, ToolResult

_DIAG = re.compile(
    r"^(.*?):(\d+):(\d+):\s+(error|warning|note):\s+(.*?)(?:\s+\[([^\]]+)\])?$"
)
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def parse_clang_tidy(stdout: str, exit_code: int = 0) -> ToolResult:
    diagnostics: list[Diagnostic] = []
    seen: set[tuple] = set()

    for raw in stdout.splitlines():
        line = _ANSI.sub("", raw)
        m = _DIAG.match(line)
        if not m:
            continue
        file, row, col, sev, msg, check = m.groups()
        if sev == "note":
            continue
        key = (file, row, col, check or msg[:40])
        if key in seen:
            continue
        seen.add(key)
        diagnostics.append(
            Diagnostic(
                file=file,
                line=int(row),
                col=int(col),
                severity="error" if sev == "error" else "warning",
                code=check,
                message=msg.strip(),
            )
        )

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = len(diagnostics) - errors
    summary = (
        f"{errors} errors, {warnings} warnings"
        if errors
        else (f"{warnings} warnings" if warnings else "no issues")
    )
    return ToolResult(
        tool="clang-tidy", exit_code=exit_code, diagnostics=diagnostics, summary=summary
    )
