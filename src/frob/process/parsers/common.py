"""
Shared types for all tool output parsers.

Each parser consumes the raw stdout/stderr of a tool and returns a
ToolResult that can be rendered as compact text (for agentic consumption)
or JSON (for programmatic use).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Severity = Literal["error", "warning", "note", "info"]


class Diagnostic(BaseModel):
    """A single actionable item from a tool: a linter warning, type error, etc."""

    file: str | None = None
    line: int | None = None
    col: int | None = None
    severity: Severity = "error"
    code: str | None = None  # e.g. "F401", "E501", "error[incompatible-type]"
    message: str = ""

    def as_text(self) -> str:
        loc = ""
        if self.file:
            loc = self.file
            if self.line is not None:
                loc += f":{self.line}"
                if self.col is not None:
                    loc += f":{self.col}"
            loc += "  "
        code_str = f"{self.code}  " if self.code else ""
        return f"{loc}{code_str}{self.message}"


class TestCase(BaseModel):
    """A single test case result."""

    __test__: bool = False

    suite: str = ""
    name: str
    passed: bool
    skipped: bool = False
    duration: float | None = None
    failure_message: str | None = None
    failure_text: str | None = None


class ToolResult(BaseModel):
    """
    Parsed output of a single tool invocation.
    Designed for compact agentic consumption.
    """

    tool: str
    exit_code: int = 0
    diagnostics: list[Diagnostic] = []
    tests: list[TestCase] = []
    summary: str = ""

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "warning")

    @property
    def failed_tests(self) -> list[TestCase]:
        return [t for t in self.tests if not t.passed and not t.skipped]

    def as_text(self, verbose: bool = False) -> str:
        """
        Compact text representation optimized for Claude to read.
        Failures always shown; passing items hidden unless verbose=True.
        """
        parts: list[str] = [f"[{self.tool}]  {self.summary}"]

        # Diagnostics (errors first, then warnings)
        errors = [d for d in self.diagnostics if d.severity == "error"]
        warnings = [d for d in self.diagnostics if d.severity == "warning"]
        notes = [d for d in self.diagnostics if d.severity not in ("error", "warning")]

        for d in errors:
            parts.append(f"  error   {d.as_text()}")
        for d in warnings:
            parts.append(f"  warn    {d.as_text()}")
        if verbose:
            for d in notes:
                parts.append(f"  note    {d.as_text()}")

        # Test cases
        for t in self.failed_tests:
            loc = f"{t.suite}.{t.name}" if t.suite else t.name
            msg = f": {t.failure_message}" if t.failure_message else ""
            parts.append(f"  FAIL    {loc}{msg}")
            if verbose and t.failure_text:
                for line in (t.failure_text or "").splitlines()[:5]:
                    parts.append(f"          {line}")

        if verbose:
            for t in self.tests:
                if t.passed:
                    parts.append(
                        f"  pass    {t.suite}.{t.name}"
                        if t.suite
                        else f"  pass    {t.name}"
                    )

        return "\n".join(parts)

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)
