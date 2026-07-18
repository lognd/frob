"""Per-tool runners for the TypeScript/npm check pipeline (tsc/eslint/prettier/vitest).

Private helpers of `frob.check`; `run_check_ts` composes them. A missing
`npx`/`node` never crashes -- it is a typed failing `ToolResult` (T-0142:
vacuous-pass doctrine, a missing tool must be a loud failure, not a silent
skip that vanishes the whole stage from the report).
"""

# frob:waive TEST005 reason="module line coverage 30.4%, debt T-0160"

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.process.parsers.common import Diagnostic, ToolResult, tool_unavailable_result

_TS_TIMEOUT_S = 300


# frob:ticket T-0142
def _missing_tool_result(tool: str, cmd: str) -> ToolResult:
    """A missing `npx`/`node` (T-0142) is a typed failing ToolResult, not a
    silent skip -- vacuous-pass doctrine: a gap must be loud in the summary."""
    return tool_unavailable_result(tool, cmd)


def _run_npx(
    root: Path, args: list[str], tool: str
) -> subprocess.CompletedProcess | None:
    """Run an `npx ...` command in root; returns None if npx is missing."""
    import shutil

    if shutil.which("npx") is None:
        return None
    try:
        return subprocess.run(
            ["npx"] + args,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=_TS_TIMEOUT_S,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None


def _run_tsc(root: Path) -> ToolResult:
    """`tsc --noEmit` type-check."""
    from frob.process.parsers import parse_tsc

    proc = _run_npx(root, ["tsc", "--noEmit"], "tsc")
    if proc is None:
        return _missing_tool_result("tsc", "npx")
    r = parse_tsc(proc.stdout + proc.stderr, exit_code=proc.returncode)
    r.tool = "tsc"
    return r


def _run_eslint(root: Path) -> ToolResult:
    """eslint with JSON output."""
    from frob.process.parsers import parse_eslint

    proc = _run_npx(root, ["eslint", ".", "--format", "json"], "eslint")
    if proc is None:
        return _missing_tool_result("eslint", "npx")
    r = parse_eslint(proc.stdout, exit_code=proc.returncode)
    r.tool = "eslint"
    return r


def _run_prettier(root: Path) -> ToolResult:
    """`prettier --check`, a warning per unformatted file."""
    proc = _run_npx(root, ["prettier", "--check", "."], "prettier")
    if proc is None:
        return _missing_tool_result("prettier", "npx")
    if not proc.returncode:
        return ToolResult(tool="prettier", exit_code=0, summary="all files formatted")
    unformatted = [
        ln.strip()
        for ln in (proc.stdout + proc.stderr).splitlines()
        if ln.strip() and not ln.lstrip().startswith(("[warn]", "Checking"))
    ]
    diags = [
        Diagnostic(file=ln, severity="warning", message="needs formatting")
        for ln in unformatted
    ]
    n = len(diags)
    return ToolResult(
        tool="prettier",
        exit_code=proc.returncode,
        diagnostics=diags,
        summary=f"{n} file{'s' if n != 1 else ''} need formatting",
    )


def _vitest_case(case: dict, suite_name: str):  # noqa: ANN202
    """One vitest assertion result -> a `TestCase`."""
    from frob.process.parsers.common import TestCase

    failures = case.get("failureMessages", [])
    return TestCase(
        suite=suite_name,
        name=case.get("fullName") or case.get("title", ""),
        passed=case.get("status") == "passed",
        skipped=case.get("status") == "pending",
        failure_message="; ".join(failures) if failures else None,
    )


def _parse_vitest_report(stdout: str) -> list:
    """Parse vitest JSON stdout into a list of `TestCase`; `[]` on bad JSON."""
    import json as _json

    tests: list = []
    try:
        report = _json.loads(stdout)
    except (_json.JSONDecodeError, AttributeError):
        # vitest emitted non-JSON (crash, missing config, etc) -- fall back
        # to exit code alone rather than crashing the whole check stage.
        return tests
    for suite in report.get("testResults", []):
        suite_name = suite.get("name", "")
        for case in suite.get("assertionResults", []):
            tests.append(_vitest_case(case, suite_name))
    return tests


def _run_vitest(root: Path) -> ToolResult:
    """`vitest run` with the JSON reporter, mapped to per-test cases."""
    proc = _run_npx(root, ["vitest", "run", "--reporter", "json"], "vitest")
    if proc is None:
        return _missing_tool_result("vitest", "npx")

    tests = _parse_vitest_report(proc.stdout)
    n_failed = sum(1 for t in tests if not t.passed and not t.skipped)
    if tests:
        summary = f"{len(tests) - n_failed}/{len(tests)} tests passed"
    else:
        summary = "tests passed" if not proc.returncode else "tests failed"

    return ToolResult(
        tool="vitest",
        exit_code=proc.returncode,
        tests=tests,
        summary=summary,
    )
