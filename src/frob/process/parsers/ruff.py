"""
ruff output parser.

Supports both the default text format and JSON format (--output-format json).
JSON format is preferred for reliability; use `ruff check --output-format json`.
"""

from __future__ import annotations

import json
import re

from frob.process.parsers.common import (
    Diagnostic,
    ToolResult,
    summarize_severity,
    tool_no_output_result,
    tool_parse_failure_result,
)

_TEXT_LINE = re.compile(r"^(.*?):(\d+):(\d+):\s+([A-Z]\d+)\s+(.*)$")


# frob:ticket T-0045
# frob:ticket T-2373
# frob:enforces CHK-GATE-I001
# frob:enforces CHK-GATE-F401
def _is_ruff_error_code(code: str) -> bool:
    """True for a ruff `code` that must render as an error diagnostic:
    E/F codes always were; T-2373 promotes I001 (import-sort) from
    warning to error now that its burn-down is at zero findings
    repo-wide -- leaving it advisory would let the debt silently
    reaccumulate."""
    return code.startswith(("E", "F")) or code == "I001"


def _ruff_json_diagnostic(item: dict) -> Diagnostic:
    """One ruff JSON item into a Diagnostic (E/F codes, plus I001, are
    errors -- see `_is_ruff_error_code`)."""
    loc = item.get("location", {})
    code = item.get("code", "")
    return Diagnostic(
        file=item.get("filename"),
        line=loc.get("row"),
        col=loc.get("column"),
        severity="error" if _is_ruff_error_code(code) else "warning",
        code=code,
        message=item.get("message", ""),
    )


# frob:ticket T-2537
# frob:ticket T-4308
# frob:doc docs/modules/process.md#public-api
# frob:waive AFFECT001 reason="T-4308 adds one new branch (empty-stdout detection) \
# ahead of the existing malformed-JSON path -- docs/modules/process.md's own text \
# already documents this function only at the 'unparsable output is loud' level of \
# detail this new branch sits alongside, and that doc file's public-api section is \
# currently under closure obligations this diff cannot satisfy without pulling in an \
# unrelated, large cross-ticket doc-scope conflict; the new branch's own inline \
# comment and tool_no_output_result's docstring carry the rationale"
def parse_ruff_json(stdout: str, exit_code: int = 0) -> ToolResult:
    """Parse `ruff check --output-format json` output."""
    try:
        items = json.loads(stdout)
    except json.JSONDecodeError as exc:
        # T-4308: EMPTY stdout means ruff never ran at all (e.g. `uv run
        # --project <target> ruff ...` failed to spawn the binary inside
        # <target>'s own environment) -- report that condition by name
        # (`tool_no_output_result`) rather than as "malformed JSON", which
        # sends a reader auditing this parser for a bug that isn't here.
        if not stdout.strip():
            return tool_no_output_result("ruff", exit_code=exit_code)
        # T-2537: a failed parse MUST carry an error diagnostic -- an empty
        # diagnostic list on a nonzero exit is indistinguishable from a
        # clean run to every caller that only reads `diagnostics`.
        return tool_parse_failure_result(
            "ruff", f"malformed JSON: {exc}", summary=f"malformed JSON: {exc}"
        )

    diagnostics = [_ruff_json_diagnostic(item) for item in items]
    summary = summarize_severity(diagnostics, collapse_errorless=True)
    return ToolResult(
        tool="ruff",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )


# frob:doc docs/modules/process.md#public-api
def parse_ruff_text(stdout: str, exit_code: int = 0) -> ToolResult:
    """Parse default `ruff check` text output."""
    diagnostics: list[Diagnostic] = []
    for line in stdout.splitlines():
        m = _TEXT_LINE.match(line.strip())
        if m:
            file, row, col, code, msg = m.groups()
            severity = "error" if _is_ruff_error_code(code) else "warning"
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


# frob:doc docs/modules/process.md#public-api
def parse_ruff(stdout: str, exit_code: int = 0) -> ToolResult:
    """Auto-detect JSON vs text format."""
    stripped = stdout.strip()
    if stripped.startswith("["):
        return parse_ruff_json(stdout, exit_code)
    return parse_ruff_text(stdout, exit_code)
