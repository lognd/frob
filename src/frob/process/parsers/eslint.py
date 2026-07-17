"""
eslint output parser.

Consumes `eslint --format json` output: a list of per-file results, each
with a `messages` array (ruleId, severity 1=warn/2=error, line, column,
message).
"""

from __future__ import annotations

import json

from frob.process.parsers.common import Diagnostic, ToolResult


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
        file = entry.get("filePath")
        for msg in entry.get("messages", []):
            diagnostics.append(
                Diagnostic(
                    file=file,
                    line=msg.get("line"),
                    col=msg.get("column"),
                    severity="error" if msg.get("severity") == 2 else "warning",
                    code=msg.get("ruleId"),
                    message=msg.get("message", ""),
                )
            )

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")
    summary = (
        f"{errors} errors, {warnings} warnings" if errors or warnings else "no issues"
    )

    return ToolResult(
        tool="eslint",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )
