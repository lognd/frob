"""Per-tool runners for the TypeScript/npm check pipeline (tsc/eslint/prettier/vitest).

Private helpers of `frob.check`; `run_check_ts` composes them. A missing
`npx`/`node` never crashes -- it is a typed failing `ToolResult` (T-0142:
vacuous-pass doctrine, a missing tool must be a loud failure, not a silent
skip that vanishes the whole stage from the report).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.process._guard import EXEC_KILL_SWITCH_ENV, guarded_subprocess_run
from frob.process.parsers.common import (
    Diagnostic,
    ToolResult,
    tool_disabled_result,
    tool_unavailable_result,
)

_TS_TIMEOUT_S = 300

#: Sentinel `_run_npx` returns instead of a `CompletedProcess` when the
#: exec kill switch (T-0200, `frob.process._guard`) is flipped -- distinct
#: from `None` (missing `npx`/timeout) so every `_run_*` caller can render
#: a disabled-capability message instead of a misleading "tool
#: unavailable" one.
_NPX_DISABLED = object()


# frob:ticket T-0142
def _missing_tool_result(tool: str, cmd: str) -> ToolResult:
    """A missing `npx`/`node` (T-0142) is a typed failing ToolResult, not a
    silent skip -- vacuous-pass doctrine: a gap must be loud in the summary."""
    return tool_unavailable_result(tool, cmd)


# frob:waive ARCH103 reason="T-0977: guarded-subprocess wrapper -- checks the kill \
# switch/tool availability, runs the process, returns a typed result; the availability \
# checks ARE the guard this wrapper exists for (see docstring's T-0142/T-0200 \
# references), not a separable concern"
# frob:waive EXHAUST001 reason="T-1062: leaked Unknown traces to \
# guarded_subprocess_run itself, a cross-module Result-returning wrapper the resolver \
# cannot see through; its own two documented raise paths (missing binary, timeout) are \
# both caught above"
def _run_npx(root: Path, args: list[str], tool: str):  # noqa: ANN201
    """Run an `npx ...` command in root via the exec kill switch (T-0200).
    Returns `None` if npx is missing/times out, `_NPX_DISABLED` if the
    kill switch is flipped, else the finished `CompletedProcess`."""
    import shutil

    if shutil.which("npx") is None:
        return None
    try:
        run_result = guarded_subprocess_run(
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
    if run_result.is_err:
        return _NPX_DISABLED
    return run_result.danger_ok


def _run_tsc(root: Path) -> ToolResult:
    """`tsc --noEmit` type-check."""
    from frob.process.parsers import parse_tsc

    proc = _run_npx(root, ["tsc", "--noEmit"], "tsc")
    if proc is None:
        return _missing_tool_result("tsc", "npx")
    if proc is _NPX_DISABLED:
        return tool_disabled_result("tsc", EXEC_KILL_SWITCH_ENV)
    r = parse_tsc(proc.stdout + proc.stderr, exit_code=proc.returncode)
    r.tool = "tsc"
    return r


def _run_eslint(root: Path) -> ToolResult:
    """eslint with JSON output."""
    from frob.process.parsers import parse_eslint

    proc = _run_npx(root, ["eslint", ".", "--format", "json"], "eslint")
    if proc is None:
        return _missing_tool_result("eslint", "npx")
    if proc is _NPX_DISABLED:
        return tool_disabled_result("eslint", EXEC_KILL_SWITCH_ENV)
    r = parse_eslint(proc.stdout, exit_code=proc.returncode)
    r.tool = "eslint"
    return r


def _run_prettier(root: Path) -> ToolResult:
    """`prettier --check`, a warning per unformatted file."""
    proc = _run_npx(root, ["prettier", "--check", "."], "prettier")
    if proc is None:
        return _missing_tool_result("prettier", "npx")
    if proc is _NPX_DISABLED:
        return tool_disabled_result("prettier", EXEC_KILL_SWITCH_ENV)
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
        for suite in report.get("testResults", []):
            suite_name = suite.get("name", "")
            for case in suite.get("assertionResults", []):
                tests.append(_vitest_case(case, suite_name))
    except Exception:
        # vitest emitted non-JSON or an unexpectedly-shaped report (crash,
        # missing config, etc) -- fall back to exit code alone rather than
        # crashing the whole check stage.
        return tests
    return tests


# frob:ticket T-0404
# frob:tests tests/unit/test_check_tool_unavailable.py::TestVitestUnverifiedZeroExit.test_run_vitest_warns_on_unparseable_zero_exit  # noqa: E501
def _run_vitest(root: Path) -> ToolResult:
    """`vitest run` with the JSON reporter, mapped to per-test cases.

    T-0404 finding 10: non-JSON stdout with a zero exit code used to be
    reported as a bare "tests passed" with no diagnostic at all -- a
    crashed-but-somehow-0 run, or a report vitest emitted in a format this
    parser doesn't understand, looked identical to a real clean pass. Now
    that case attaches a WARNING diagnostic naming the ambiguity, so a
    reviewer can tell "verified 0 failures" apart from "exit code alone,
    unverified" at a glance.
    """
    proc = _run_npx(root, ["vitest", "run", "--reporter", "json"], "vitest")
    if proc is None:
        return _missing_tool_result("vitest", "npx")
    if proc is _NPX_DISABLED:
        return tool_disabled_result("vitest", EXEC_KILL_SWITCH_ENV)

    tests = _parse_vitest_report(proc.stdout)
    n_failed = sum(1 for t in tests if not t.passed and not t.skipped)
    diagnostics: list[Diagnostic] = []
    if tests:
        summary = f"{len(tests) - n_failed}/{len(tests)} tests passed"
    elif not proc.returncode:
        summary = "tests passed (unverified: no parseable vitest JSON report)"
        diagnostics.append(
            Diagnostic(
                file="vitest",
                severity="warning",
                message=(
                    "vitest exited 0 but produced no parseable JSON report; "
                    "this is reported as passing on exit code alone, not "
                    "verified per-test"
                ),
            )
        )
    else:
        summary = "tests failed"

    return ToolResult(
        tool="vitest",
        exit_code=proc.returncode,
        tests=tests,
        diagnostics=diagnostics,
        summary=summary,
    )
