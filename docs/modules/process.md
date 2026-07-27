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
<!-- frob:describes src/frob/process/parsers/common.py::tool_unavailable_result -->
<!-- frob:describes src/frob/process/parsers/common.py::tool_disabled_result -->
<!-- frob:describes src/frob/process/_guard.py::EXEC_KILL_SWITCH_ENV -->
<!-- frob:describes src/frob/process/_guard.py::NET_KILL_SWITCH_ENV -->
<!-- frob:describes src/frob/process/_guard.py::ProcessGuardError -->
<!-- frob:describes src/frob/process/_guard.py::exec_enabled -->
<!-- frob:describes src/frob/process/_guard.py::net_enabled -->
<!-- frob:describes src/frob/process/_guard.py::guarded_subprocess_run -->
<!-- frob:describes src/frob/process/_lock.py::_derived_lock_path -->
<!-- frob:describes src/frob/process/_lock.py::derived_state_lock -->

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
def tool_unavailable_result(tool: str, binary: str) -> ToolResult
    # A missing tool binary as a failing ToolResult (T-0142 vacuous-pass doctrine).
def tool_disabled_result(tool: str, flag_env: str) -> ToolResult
    # An exec-kill-switch refusal as a failing ToolResult (T-0200), naming the env var.
```

## Kill switch (T-0200)

`frob.process._guard` is the real, checked-in kill-switch/feature-flag
mechanism behind `design/frob.strata`'s `checker` node `attr
flag=frob_check_exec_kill_switch;` declaration -- an env-var-gated wrapper
around `subprocess.run` that every `frob.check` tool runner
(`_python.py`/`_native.py`/`_ts.py`) calls instead of `subprocess.run`
directly, so an operator can disable process spawning live, with no
redeploy.

```python
# frob/process/_guard.py -- exec/net kill switches
EXEC_KILL_SWITCH_ENV = "FROB_DISABLE_EXEC"
NET_KILL_SWITCH_ENV = "FROB_DISABLE_NET"   # mechanism built; no real net call site wired yet (T-0200 scope)

class ProcessGuardError(ErrorSet):
    ExecDisabled  # exec capability disabled via kill switch

def exec_enabled() -> bool
    # False exactly when FROB_DISABLE_EXEC is set truthy ("1"/"true"/"yes"/"on").
def net_enabled() -> bool
    # False exactly when FROB_DISABLE_NET is set truthy.
def guarded_subprocess_run(args, **kwargs) -> Result[subprocess.CompletedProcess, ProcessGuardError]
    # subprocess.run(args, **kwargs), gated by exec_enabled(); Err(ExecDisabled) without spawning when disabled.
```

Set `FROB_DISABLE_EXEC=1` in the environment to stop every `frob check`
tool-runner subprocess (ruff/ty/cmake/cargo/clang-tidy/clang-format/ctest/
npx-driven tsc/eslint/prettier/vitest) without a redeploy or code change;
unset it (or leave it unset) to re-enable.

<!-- frob:invariant INV-019 -->

## Derived-state lock (T-0859)

`frob.process._lock.derived_state_lock` is a cross-process shared/exclusive
`flock` over a checkout's `.frob/derived.lock`, closing the TOCTOU window
T-0603's single in-process integrity precheck left open: a SECOND `frob`
process rewriting or corrupting `.frob`'s derived artifacts between this
process's precheck and a later stage's read. Every `frob.check` entry point
(`run_check`, `run_check_cpp`, `run_check_rust`, `run_check_ts`) holds the
SHARED form for its entire run -- precheck through the last stage's read.
Any process that rebuilds or rewrites a derived artifact under `.frob` is
expected to hold the EXCLUSIVE form while it writes; wiring the exclusive
side into every current writer is tracked as a follow-on, not shipped by
this module (see this ticket's Done report for what still needs it).

```python
# frob/process/_lock.py -- cross-process reader/writer lock over .frob
def derived_state_lock(root: Path, *, exclusive: bool) -> ContextManager[None]
    # Shared (reader) or exclusive (writer) flock on root/.frob/derived.lock;
    # no-op with a WARNING log on a platform without fcntl.
```

Mirrors `frob.tickets._store.ledger_lock` (T-0458): same fcntl-posix-only
primitive, same documented no-op fallback, same per-thread re-entrancy
bookkeeping -- applied to `.frob`'s derived state instead of the ticket
ledger.

`derived_state_write_lock` (T-0918) is the reentrancy-aware writer entry
point `frob.dup.find_clones`/`frob.graph.build_graph` call: it consults a
PROCESS-wide (not just thread-local) registry, `_process_held_counts`,
before deciding whether to take a real second `flock` or no-op because
some thread in this same process already holds `derived_state_lock` for
the same root. That registry is keyed on a CANONICAL (`Path.resolve()`d)
form of the root (T-0933) specifically so two call sites that reach the
same on-disk checkout through different spellings -- e.g. `frob.check`'s
outer shared lock receiving an unresolved/relative root while
`build_graph` resolves its own copy before calling
`derived_state_write_lock` -- agree on whether the process already holds
the lock. Before this fix the registry was keyed on the literal (non-
canonicalized) path string, so a resolved-vs-unresolved spelling mismatch
made the no-op guard read `False` when it should have read `True`, and
the writer attempted a genuine second `flock(LOCK_EX)` against its own
process's outstanding `LOCK_SH` -- a same-process self-deadlock
(`frob check --only scope`/`--only prework` hung in every worktree until
fixed). The actual `os.open`/`flock` path is unaffected by this -- `flock`
is inode-scoped, so different spellings of the same file already
serialized correctly at the OS level; only the in-process dict lookup was
spelling-sensitive.

## Dependencies

Pure stdlib + `pydantic` for the shared models; no dependency on `frob.check`
or `frob.gitio` -- parsers are pure functions over already-captured
stdout/stderr text, never spawn processes themselves. `frob.process._lock`
is the one exception: it wraps stdlib `os`/`fcntl` directly (no subprocess
involved) to serialize `frob.check` against other `frob` processes.

## Integration points

`frob.check` (docs/commands/check.md) is the sole consumer: each `_run_*` helper
shells out to a tool and hands its captured output to the matching
`parse_*` function, folding the resulting `ToolResult` into `CheckResult`.
