"""
Shared types for all tool output parsers.

Each parser consumes the raw stdout/stderr of a tool and returns a
ToolResult that can be rendered as compact text (for agentic consumption)
or JSON (for programmatic use).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, computed_field

#: T-2391: the three states a `ToolResult` can actually be in, replacing
#: the ambiguous "a list of findings, whose emptiness means... something"
#: shape the fail-loudly doctrine names as this repo's single dominant
#: bug class. `ToolResult.measurement` (below) derives this from data
#: already present on every `ToolResult` today -- no per-gate migration
#: required for the cases it covers (see `ToolResult.measurement`'s own
#: docstring for exactly which cases those are, and which are NOT yet
#: covered and were filed as follow-up tickets instead of guessed at).
# frob:doc docs/modules/process.md#public-api
# frob:ticket T-3206
Measurement = Literal["measured", "not_measured"]

# frob:doc docs/modules/process.md#public-api
Severity = Literal["error", "warning", "note", "info"]


# frob:ticket T-0045
def _count_severities(diagnostics: list[Diagnostic]) -> tuple[int, int]:
    """`(error_count, warning_count)` over `diagnostics` in a single pass."""
    errors = 0
    warnings = 0
    for d in diagnostics:
        if d.severity == "error":
            errors += 1
        elif d.severity == "warning":
            warnings += 1
    return errors, warnings


# frob:doc docs/modules/process.md#public-api
# frob:ticket T-0045
def summarize_severity(
    diagnostics: list[Diagnostic],
    *,
    empty: str = "no issues",
    collapse_errorless: bool = False,
) -> str:
    """One-line `N errors, M warnings` summary shared by every tool parser.

    `empty` is returned when there are no diagnostics at all. When
    `collapse_errorless` is set and there are no errors, only the warning
    count is shown (the format ruff-json/clang-tidy/cargo use); otherwise
    both counts always appear.
    """
    errors, warnings = _count_severities(diagnostics)
    if not errors and not warnings:
        return empty
    if collapse_errorless and not errors:
        return f"{warnings} warnings"
    return f"{errors} errors, {warnings} warnings"


# frob:doc docs/modules/process.md#public-api
class Diagnostic(BaseModel):
    """A single actionable item from a tool: a linter warning, type error, etc."""

    file: str | None = None
    line: int | None = None
    col: int | None = None
    severity: Severity = "error"
    code: str | None = None  # e.g. "F401", "E501", "error[incompatible-type]"
    message: str = ""

    # frob:ticket T-0588
    # frob:tests tests/unit/test_process.py::test_ruff_as_text
    def as_text(self) -> str:
        # frob:doc docs/modules/process.md#public-api
        """One-line `file:line:col  CODE  message` rendering."""
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


# frob:doc docs/modules/process.md#public-api
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


# frob:doc docs/modules/process.md#public-api
# frob:ticket T-3206
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
        # frob:doc docs/modules/process.md#public-api
        """Whether the tool invocation itself exited zero."""
        return self.exit_code == 0

    @property
    def error_count(self) -> int:
        # frob:doc docs/modules/process.md#public-api
        """Number of error-severity diagnostics."""
        return sum(1 for d in self.diagnostics if d.severity == "error")

    @property
    def warning_count(self) -> int:
        # frob:doc docs/modules/process.md#public-api
        """Number of warning-severity diagnostics."""
        return sum(1 for d in self.diagnostics if d.severity == "warning")

    @property
    def failed_tests(self) -> list[TestCase]:
        # frob:doc docs/modules/process.md#public-api
        """Test cases that neither passed nor were skipped."""
        return [t for t in self.tests if not t.passed and not t.skipped]

    # frob:ticket T-2391
    # frob:doc docs/modules/process.md#public-api
    # frob:ticket T-3206
    # frob:tests tests/unit/test_process.py::TestToolResultMeasurement.test_measured_when_zero_diagnostics  # noqa: E501
    # frob:tests tests/unit/test_process.py::TestToolResultMeasurement.test_measured_when_a_real_error_is_present  # noqa: E501
    # frob:tests tests/unit/test_process.py::TestToolResultMeasurement.test_not_measured_when_every_diagnostic_is_unresolved_info  # noqa: E501
    # frob:tests tests/unit/test_process.py::TestToolResultMeasurement.test_measured_when_unresolved_mixes_with_a_real_warning  # noqa: E501
    @computed_field  # type: ignore[prop-decorator]
    @property
    def measurement(self) -> Measurement:
        """T-2391 fail-loudly doctrine: `"not_measured"` iff this
        `ToolResult` is a `gate:<FAMILY>` result whose ENTIRE content is
        `Severity.UNRESOLVED` (T-1664's existing "could not determine an
        answer" signal, rendered by `frob.check._python` as
        `severity="info"`) -- zero errors, zero warnings, at least one
        diagnostic, every diagnostic `"info"`. That is the one
        `ToolResult` shape this repo already produces in dozens of gate
        families (every `*_SCHEMA` config-table validator, FLAGCOV001,
        REF001/REF002) whose zero-error/zero-warning summary is
        genuinely ambiguous between "measured, clean" and "could not
        measure anything" -- `"measured"` (the default) covers both a
        real clean pass AND every OTHER unmeasured shape this repo has
        (budget truncation, a hardcoded-layout gate against a foreign
        project, a matcher that silently never fires): those need a
        per-call-site or per-gate signal this generic, data-only
        computation cannot invent, and were filed as T-2391 follow-up
        tickets rather than guessed at here. A computed field (not a
        stored one) so every EXISTING caller across this repo that
        already builds a `ToolResult` gets this for free, retroactively,
        with no migration -- the identical data `frob.check.
        _is_unresolved_only_gate` already computed privately just for
        `as_text`'s icon, now a first-class part of the model so
        `as_json()` discloses it too (T-2891 left exactly this JSON gap
        open; see this repo's own doc comment there)."""
        if (
            self.tool.startswith("gate:")
            and self.error_count == 0
            and self.warning_count == 0
            and bool(self.diagnostics)
            and all(d.severity == "info" for d in self.diagnostics)
        ):
            return "not_measured"
        return "measured"

    # frob:ticket T-2391
    # frob:doc docs/modules/process.md#public-api
    # frob:ticket T-3206
    # frob:tests tests/unit/test_process.py::TestToolResultMeasurement.test_not_measured_when_every_diagnostic_is_unresolved_info  # noqa: E501
    @computed_field  # type: ignore[prop-decorator]
    @property
    def measurement_reason(self) -> str:
        """Non-empty iff `measurement == "not_measured"`: the joined
        messages of every diagnostic that made this result
        `not_measured` -- so a `--json` consumer never has to re-derive
        "why" from `diagnostics` by hand the way `as_text`'s reader
        already could just by looking at the rendered lines."""
        if self.measurement != "not_measured":
            return ""
        return "; ".join(d.message for d in self.diagnostics)

    def _partition_diagnostics(
        self,
    ) -> tuple[list[Diagnostic], list[Diagnostic], list[Diagnostic]]:
        """Split diagnostics into (errors, warnings, notes) in one pass."""
        errors: list[Diagnostic] = []
        warnings: list[Diagnostic] = []
        notes: list[Diagnostic] = []
        for d in self.diagnostics:
            if d.severity == "error":
                errors.append(d)
            elif d.severity == "warning":
                warnings.append(d)
            else:
                notes.append(d)
        return errors, warnings, notes

    def _render_diagnostics(self, verbose: bool) -> list[str]:
        """Rendered diagnostic lines: errors, then warnings, then notes."""
        errors, warnings, notes = self._partition_diagnostics()
        lines = [f"  error   {d.as_text()}" for d in errors]
        lines += [f"  warn    {d.as_text()}" for d in warnings]
        if verbose:
            lines += [f"  note    {d.as_text()}" for d in notes]
        return lines

    def _render_tests(self, verbose: bool) -> list[str]:
        """Rendered test lines: failures (with optional traceback), then passes."""
        lines: list[str] = []
        for t in self.failed_tests:
            loc = f"{t.suite}.{t.name}" if t.suite else t.name
            msg = f": {t.failure_message}" if t.failure_message else ""
            lines.append(f"  FAIL    {loc}{msg}")
            if verbose and t.failure_text:
                lines += [
                    f"          {line}"
                    for line in (t.failure_text or "").splitlines()[:5]
                ]
        if verbose:
            lines += [
                f"  pass    {t.suite}.{t.name}" if t.suite else f"  pass    {t.name}"
                for t in self.tests
                if t.passed
            ]
        return lines

    # frob:ticket T-0588
    # frob:tests tests/unit/test_process.py::test_pytest_as_text_shows_failures
    def as_text(self, verbose: bool = False) -> str:
        # frob:doc docs/modules/process.md#public-api
        """
        Compact text representation optimized for Claude to read.
        Failures always shown; passing items hidden unless verbose=True.
        """
        parts: list[str] = [f"[{self.tool}]  {self.summary}"]
        parts += self._render_diagnostics(verbose)
        parts += self._render_tests(verbose)
        return "\n".join(parts)

    # frob:ticket T-0588
    # frob:tests tests/unit/test_process.py::test_pytest_as_json
    def as_json(self) -> str:
        # frob:doc docs/modules/process.md#public-api
        """The full structured result as JSON."""
        return self.model_dump_json(indent=2)


# frob:doc docs/modules/process.md#public-api
# frob:ticket T-0142
def tool_unavailable_result(tool: str, binary: str) -> ToolResult:
    """A missing `binary` on PATH is a FAILING `ToolResult`, never a silent
    skip (vacuous-pass doctrine, T-0142): every `_run_*` check-stage helper
    that spawns `binary` and catches `FileNotFoundError` should return this
    instead of `None`/raising, so the gap is loud in `frob check` output
    rather than an invisible missing stage."""
    return ToolResult(
        tool=tool,
        exit_code=1,
        diagnostics=[
            Diagnostic(
                severity="error",
                message=(
                    f"tool unavailable: {binary} -- install it or use make install-tool"
                ),
            )
        ],
        summary=f"tool unavailable: {binary}",
    )


# frob:doc docs/modules/process.md#public-api
# frob:ticket T-0200
def tool_disabled_result(tool: str, flag_env: str) -> ToolResult:
    """A `ProcessGuardError.ExecDisabled` refusal (`frob.process._guard.
    guarded_subprocess_run`) is a FAILING `ToolResult` naming the exact env
    var an operator flipped, mirroring `tool_unavailable_result`'s
    loud-not-silent doctrine (T-0142) for the kill-switch case (T-0200):
    a disabled tool stage is a visible failure in `frob check` output, not
    a silently skipped stage."""
    return ToolResult(
        tool=tool,
        exit_code=1,
        diagnostics=[
            Diagnostic(
                severity="error",
                message=(
                    f"exec capability disabled via {flag_env} -- unset it "
                    "to re-enable this check stage"
                ),
            )
        ],
        summary=f"exec disabled via {flag_env}",
    )


# frob:doc docs/modules/process.md#public-api
def tool_crash_result(tool: str, exc: BaseException) -> ToolResult:
    """An unexpected exception while running or parsing `tool`'s output is a
    FAILING `ToolResult` naming the exception, mirroring
    `tool_unavailable_result`'s loud-not-silent doctrine (T-0142): a
    check-stage helper that hits a genuinely unresolvable/unexpected error
    (a malformed tool report, an unreadable artifact) should report it as a
    visible failing stage instead of letting the exception cross the
    `frob check` gate boundary uncaught (EXHAUST001/EXHAUST002, T-1022)."""
    return ToolResult(
        tool=tool,
        exit_code=1,
        diagnostics=[
            Diagnostic(
                severity="error",
                message=f"{tool} crashed: {type(exc).__name__}: {exc}",
            )
        ],
        summary=f"{tool} crashed: {type(exc).__name__}",
    )


# frob:doc docs/modules/process.md#public-api
# frob:ticket T-2537
# frob:tests \
# tests/unit/test_parser_failure_diagnostics.py::TestParseFailureResult.test_attaches_e\
# rror_diagnostic
def tool_parse_failure_result(
    tool: str, detail: str, *, exit_code: int = 1, summary: str | None = None
) -> ToolResult:
    """Unparsable tool OUTPUT (malformed/truncated JSON or XML) is a FAILING
    `ToolResult` carrying a real error `Diagnostic`, never an empty
    diagnostic list -- the producer-side half of T-2521's fix.

    A parser that returned `exit_code=1, diagnostics=[]` on malformed input
    was byte-identical, to any caller that only reads `diagnostics`, to a
    genuinely clean run; that silence auto-dropped seven sweep tickets and
    ~66 live finding identities. This mirrors `tool_crash_result` /
    `tool_disabled_result`'s loud-not-silent doctrine (T-0142) for the
    "the tool ran but its output could not be parsed" case, so every
    parser reports the same shape. `exit_code` is overridable only so a
    parser can preserve a more specific nonzero code it already knows;
    it is never zero-able -- a value of 0 is coerced to 1, because a run
    whose output could not be parsed was not a passing run.
    """
    return ToolResult(
        tool=tool,
        exit_code=exit_code or 1,
        diagnostics=[
            Diagnostic(
                severity="error",
                message=f"{tool} output could not be parsed: {detail}",
            )
        ],
        summary=summary if summary is not None else detail,
    )
