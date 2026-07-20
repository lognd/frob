"""
frob.process -- tool output parsers.

Each parser takes the raw stdout of a tool and returns a ToolResult with
compact as_text() and as_json() methods optimized for agentic consumption.

Usage:
    from frob.process.parsers import parse_pytest, parse_ruff, parse_ty, parse_clang
    result = parse_pytest(stdout, exit_code=1)
    print(result.as_text())   # compact summary + failures only
    print(result.as_json())   # full structured data
"""

from frob.process._guard import (
    EXEC_KILL_SWITCH_ENV,
    NET_KILL_SWITCH_ENV,
    ProcessGuardError,
    exec_enabled,
    guarded_subprocess_run,
    net_enabled,
)
from frob.process.parsers import (
    Diagnostic,
    TestCase,
    ToolResult,
    parse_clang,
    parse_junit_xml,
    parse_pytest,
    parse_ruff,
    parse_ty,
)

__all__ = [
    "parse_clang",
    "parse_junit_xml",
    "parse_pytest",
    "parse_ruff",
    "parse_ty",
    "Diagnostic",
    "TestCase",
    "ToolResult",
    "EXEC_KILL_SWITCH_ENV",
    "NET_KILL_SWITCH_ENV",
    "ProcessGuardError",
    "exec_enabled",
    "guarded_subprocess_run",
    "net_enabled",
]
