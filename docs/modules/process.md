# frob.process -- tool output parsers

One sentence: every static-analysis/test-runner tool `frob check` and `frob
test` shell out to has a raw stdout/stderr format of its own; `frob.process`
normalizes all of them into one shared `ToolResult`/`Diagnostic`/`TestCase`
shape so `frob check`'s renderer, JSON output, and the gates never special-
case a tool by name.

## Public API

<!-- frob:describes src/frob/process/parsers/junit.py::parse_junit_xml -->
<!-- frob:describes src/frob/process/parsers/pytest.py::parse_pytest -->
<!-- frob:describes src/frob/process/parsers/ruff.py::parse_ruff_json -->
<!-- frob:describes src/frob/process/parsers/ruff.py::parse_ruff_text -->
<!-- frob:describes src/frob/process/parsers/ruff.py::parse_ruff -->
<!-- frob:describes src/frob/process/parsers/valgrind.py::parse_valgrind -->
<!-- frob:describes src/frob/process/parsers/eslint.py::parse_eslint -->
<!-- frob:describes src/frob/process/parsers/clang.py::parse_clang -->
<!-- frob:describes src/frob/process/parsers/tsc.py::parse_tsc -->
<!-- frob:describes src/frob/process/parsers/cargo.py::parse_cargo -->
<!-- frob:describes src/frob/process/parsers/clang_tidy.py::parse_clang_tidy -->
<!-- frob:describes src/frob/process/parsers/ty.py::parse_ty -->
<!-- frob:describes src/frob/process/parsers/common.py::Diagnostic -->
<!-- frob:describes src/frob/process/parsers/common.py::Diagnostic.as_text -->
<!-- frob:describes src/frob/process/parsers/common.py::TestCase -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult.passed -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult.error_count -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult.warning_count -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult.failed_tests -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult.as_text -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult.as_json -->

```python
# frob/process/parsers/common.py -- the shared result shapes every parser below produces
class Diagnostic(BaseModel)
    # A single actionable item from a tool: a linter warning, type error, etc.
    file: str | None
    line: int | None
    col: int | None
    severity: Severity            # "error" | "warning" | "note" | "info"
    code: str | None
    message: str
    def as_text(self) -> str
        # One-line `file:line:col  CODE  message` rendering.

class TestCase(BaseModel)
    # A single test case result (from JUnit XML or pytest terminal output).
    suite: str
    name: str
    passed: bool
    skipped: bool
    duration: float | None
    failure_message: str | None
    failure_text: str | None

class ToolResult(BaseModel)
    # Parsed output of a single tool invocation; the shape every parse_* below returns.
    tool: str
    exit_code: int
    diagnostics: list[Diagnostic]
    tests: list[TestCase]
    summary: str
    passed: bool                  # property; exit_code == 0
    error_count: int              # property; count of error diagnostics
    warning_count: int            # property; count of warning diagnostics
    failed_tests: list[TestCase]  # property; tests that neither passed nor skipped
    def as_text(self, verbose: bool = False) -> str
        # Compact text for agentic consumption; failures always shown.
    def as_json(self) -> str
        # The full structured result as JSON.

# frob/process/parsers/*.py -- one parse_* per tool, all returning ToolResult
def parse_junit_xml(content: str, tool: str = "junit") -> ToolResult
    # JUnit XML (pytest --junit-xml, gtest, Catch2, CTest) into a ToolResult.
def parse_pytest(stdout: str, exit_code: int = 0) -> ToolResult
    # pytest terminal output (no plugins required) into a ToolResult.
def parse_ruff_json(stdout: str, exit_code: int = 0) -> ToolResult
    # `ruff check --output-format json` output into a ToolResult.
def parse_ruff_text(stdout: str, exit_code: int = 0) -> ToolResult
    # Default `ruff check` text output into a ToolResult.
def parse_ruff(stdout: str, exit_code: int = 0) -> ToolResult
    # Auto-detects JSON vs text ruff output and dispatches to the right parser.
def parse_valgrind(stdout: str, exit_code: int = 0) -> ToolResult
    # Valgrind memcheck output (text or --xml=yes) into a ToolResult.
def parse_eslint(stdout: str, exit_code: int = 0) -> ToolResult
    # `eslint --format json` output into a ToolResult.
def parse_clang(stdout: str, exit_code: int = 0, tool: str = "clang") -> ToolResult
    # clang/gcc compiler diagnostic text into a ToolResult.
def parse_tsc(stdout: str, exit_code: int = 0) -> ToolResult
    # `tsc` compiler diagnostic text into a ToolResult.
def parse_cargo(stdout: str, exit_code: int = 0, tool: str = "cargo") -> ToolResult
    # `cargo` output (--message-format json or plain text) into a ToolResult.
def parse_clang_tidy(stdout: str, exit_code: int = 0) -> ToolResult
    # clang-tidy diagnostic text into a ToolResult.
def parse_ty(stdout: str, exit_code: int = 0) -> ToolResult
    # `ty check` diagnostic text (ANSI or plain) into a ToolResult.
```

## Dependencies

Pure stdlib + `pydantic` for the shared models; no dependency on `frob.check`
or `frob.gitio` -- parsers are pure functions over already-captured
stdout/stderr text, never spawn processes themselves.

## Integration points

`frob.check` (docs/commands/check.md) is the sole consumer: each `_run_*` helper
shells out to a tool and hands its captured output to the matching
`parse_*` function, folding the resulting `ToolResult` into `CheckResult`.
