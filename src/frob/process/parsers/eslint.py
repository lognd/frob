"""
eslint output parser.

Consumes `eslint --format json` output: a list of per-file results, each
with a `messages` array (ruleId, severity 1=warn/2=error, line, column,
message).
"""

from __future__ import annotations

import json

from frob.process.parsers.common import Diagnostic, ToolResult, summarize_severity


# frob:ticket T-0045
def _diagnostics_for_entry(entry: dict) -> list[Diagnostic]:
    """Diagnostics for one eslint per-file result object."""
    file = entry.get("filePath")
    out: list[Diagnostic] = []
    for msg in entry.get("messages", []):
        out.append(
            Diagnostic(
                file=file,
                line=msg.get("line"),
                col=msg.get("column"),
                severity="error" if msg.get("severity") == 2 else "warning",
                code=msg.get("ruleId"),
                message=msg.get("message", ""),
            )
        )
    return out


# frob:doc docs/process.md#public-api
def parse_eslint(stdout: str, exit_code: int = 0) -> ToolResult:
    """Parse `eslint --format json` output into a ToolResult."""
    stripped = stdout.strip()
    if not stripped:
        return ToolResult(tool="eslint", exit_code=exit_code, summary="no output")

    try:
        files = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return ToolResult(
            tool="eslint",
            exit_code=exit_code or 1,
            summary=f"malformed JSON: {exc}",
        )

    diagnostics: list[Diagnostic] = []
    for entry in files:
        diagnostics.extend(_diagnostics_for_entry(entry))

    summary = summarize_severity(diagnostics)

    return ToolResult(
        tool="eslint",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )
