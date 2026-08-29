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
<!-- frob:describes src/frob/process/parsers/common.py::tool_crash_result -->
<!-- frob:describes src/frob/process/parsers/common.py::tool_parse_failure_result -->
<!-- frob:describes src/frob/process/parsers/common.py::Measurement -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult.measurement -->
<!-- frob:describes src/frob/process/parsers/common.py::ToolResult.measurement_reason -->
<!-- frob:describes src/frob/process/_guard.py::EXEC_KILL_SWITCH_ENV -->
<!-- frob:describes src/frob/process/_guard.py::NET_KILL_SWITCH_ENV -->
<!-- frob:describes src/frob/process/_guard.py::ProcessGuardError -->
<!-- frob:describes src/frob/process/_guard.py::exec_enabled -->
<!-- frob:describes src/frob/process/_guard.py::net_enabled -->
<!-- frob:describes src/frob/process/_guard.py::guarded_subprocess_run -->
<!-- frob:describes src/frob/process/_lock.py::_derived_lock_path -->
<!-- frob:describes src/frob/process/_lock.py::derived_state_lock -->
<!-- frob:describes src/frob/process/_lock.py::DerivedStateLockUnavailable -->

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
    measurement: Measurement       # computed field; "measured" | "not_measured" (T-2391)
    measurement_reason: str        # computed field; why, when measurement=="not_measured"
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
    # `ruff check --output-format json` output into a ToolResult. E/F codes and I001
    # (import-sort, T-2373: promoted from warning once its burn-down hit zero) render
    # as errors; every other ruff code renders as a warning.
def parse_ruff_text(stdout: str, exit_code: int = 0) -> ToolResult
    # Default `ruff check` text output into a ToolResult. Same E/F/I001 -> error,
    # else -> warning severity mapping as `parse_ruff_json` above.
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
def tool_crash_result(tool: str, exc: BaseException) -> ToolResult
    # An unexpected exception (T-1022 EXHAUST001/002) as a failing ToolResult, naming the exception.
def tool_parse_failure_result(tool, detail, *, exit_code=1, summary=None) -> ToolResult
    # Unparsable tool OUTPUT (malformed JSON/XML) as a failing ToolResult carrying a real
    # error Diagnostic (T-2537) -- never exit_code=1 with an empty diagnostic list, which
    # is indistinguishable from a clean run to any caller that only reads `diagnostics`.
```

### Unparsable output is never silence (T-2537)

Every parser whose input can fail to decode -- `parse_ruff_json`,
`parse_eslint`, `parse_junit_xml`, valgrind's XML branch, and cargo's
per-line JSON stream -- routes its failure through
`tool_parse_failure_result` (or, for cargo, appends an equivalent error
`Diagnostic` for the offending line). Before T-2537 those branches
returned a nonzero exit code with `diagnostics=[]`, which is byte-
identical at the `ToolResult` level to a genuinely clean run; a ruff
crash under fleet contention read as "measured, found nothing" and
auto-dropped seven sweep tickets. A genuinely clean run is unchanged:
zero diagnostics, zero exit code. A warning-only nonzero exit (ruff-
format's "N files would be reformatted") is untouched -- it never enters
a parse-failure branch. T-2521's consumer-side guard
(`_incomplete_tool_results`) remains in place as the second layer.

### `measured` vs `not_measured` is a first-class fact, not a guess (T-2391)

`ToolResult.measurement` (`Measurement = Literal["measured", "not_measured"]`)
answers the question a bare `error_count == 0 and warning_count == 0`
check cannot: did this result actually MEASURE something and find it
clean, or did it fail to measure anything at all? Zero errors and zero
warnings are byte-identical either way at the raw-count level -- exactly
the fail-loudly doctrine's dominant bug class this repo keeps re-finding
(T-2537 immediately above is the sibling incident at the parse-failure
layer; this is the same shape one layer up, at the RESULT-classification
layer).

`measurement` is `"not_measured"` iff this `ToolResult` is a `gate:
<FAMILY>` result whose ENTIRE diagnostic set is `Severity.UNRESOLVED`
(T-1664's existing "could not determine an answer" signal, rendered as
`severity="info"`): zero errors, zero warnings, at least one diagnostic,
every diagnostic `"info"`. That is the one shape this repo's gates
already produce in dozens of families (every `*_SCHEMA` config-table
validator, FLAGCOV001, REF001/REF002) where a zero/zero summary is
genuinely ambiguous between "measured, clean" and "could not measure
anything." `"measured"` (the default) covers both a real clean pass AND
every OTHER unmeasured shape this repo has (budget truncation, a
hardcoded-layout gate against a foreign project, a matcher that silently
never fires) -- those need a per-call-site or per-gate signal this
generic, data-only computation cannot invent, and are tracked as
separate follow-up work rather than guessed at here.

It is a COMPUTED field, not a stored one, so every existing caller
across this repo that already builds a `ToolResult` gets it for free,
retroactively, with no migration -- the identical data `frob.check.
_is_unresolved_only_gate` already computed privately just for
`as_text`'s icon is now a first-class part of the model, so `as_json()`
discloses it too. `measurement_reason` is the joined diagnostic messages
that made a `not_measured` result what it is (empty string when
`measurement == "measured"`) -- a `--json` consumer's equivalent of what
`as_text`'s reader could already see just by looking at the rendered
lines.

## pytest-spawn resolution (T-3311)

<!-- frob:describes src/frob/process/_pytest_spawn.py::resolve_pytest_argv -->
<!-- frob:describes src/frob/process/_pytest_spawn.py::pytest_importable -->
<!-- frob:describes src/frob/process/_pytest_spawn.py::PytestSpawnError -->

**Incident:** three call sites in this codebase each built a pytest-spawn
argv their own way. `frob.gates._bug_repro` used `sys.executable, "-m",
"pytest"` -- correct, per T-3268's own adopted fix for `frob.perf._profile`
(spawn under the CALLING process's own interpreter, never a bare `python`/
`python3` PATH lookup). `frob.app.ticket_runner._verify` hardcoded `"uv",
"run", "pytest"`, assuming `uv` is on `PATH` and a `uv`-recognised
`pyproject.toml` sits above `cwd` -- a dependency this repo does not
otherwise require of a caller. `frob.refactor._verify` used a bare
`"pytest"` PATH lookup, resolving to whichever `pytest` happens to be
first on a caller's `PATH` -- in a consumer environment (an agent shell,
a CI runner layering several venvs onto `PATH`) that is frequently NOT
the project's own.

`resolve_pytest_argv(*args, python=None)` is the one resolution helper
all three sites now call: `[python or sys.executable, "-m", "pytest",
*args]`, after `pytest_importable(python)` probes that pytest actually
imports through the resolved interpreter (`<python> -c "import pytest"`,
T-3305's probe-don't-assume principle -- `_python_for_tree` applied it to
`frob` itself; this applies the identical principle to `pytest`).
`Err(PytestSpawnError.NotImportable)` on a failed probe, caught before
the argv is ever handed to a spawner, so the failure is an explicit,
loud, typed value instead of pytest's own opaque "No module named
pytest" surfacing several layers away from where the interpreter was
chosen. `pytest` is `OPTIONAL_FOR_GATE` (T-3276's `ToolCategory`, `frob.
doctor`), not `REQUIRED`: frob itself still runs with it absent, so this
is a `Result` a caller decides how to react to (report a gate
UNMEASURED, skip a verification step, log `NO_VERDICT`) -- never a hard
crash.

`frob.app.ticket_runner._verify._run_pytest_directly` passes `python=
_python_for_tree(root)` (the worktree's OWN interpreter, T-0846/T-3305)
rather than the default `sys.executable`, since it verifies a specific
ticket worktree's node ids, not the calling coordinator process's own
tree. `frob.gates._bug_repro._spawn_designated_test` and `frob.refactor.
_verify.verify_pytest_collect` both use the default (`sys.executable`):
the former spawns from inside an already-checked-out parent-commit
worktree via `cwd=`, the latter verifies the CALLING process's own repo.

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

`guarded_subprocess_run` also defaults a text-mode call's decode codec
(T-2953): `subprocess.run(text=True, ...)`/`universal_newlines=True`
with no explicit `encoding=` falls back to the platform's default
locale codec -- UTF-8 on Linux/macOS, but cp1252 (or another single-
byte Windows code page) on Windows, where a byte a third-party tool
(maturin/cargo/git/ty) can legitimately emit crashes the read with an
uncatchable `UnicodeDecodeError`. `guarded_subprocess_run` now injects
`encoding="utf-8"`/`errors="replace"` whenever text mode is requested
without one, for every current and future caller, without needing a
per-call-site fix.

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
    # Shared (reader) or exclusive (writer) lock on root/.frob/derived.lock:
    # fcntl.flock on POSIX, msvcrt.locking (always exclusive) on Windows
    # (T-2934); raises DerivedStateLockUnavailable if neither exists.
```

Mirrors `frob.tickets._store.ledger_lock` (T-0458): same per-thread
re-entrancy bookkeeping, applied to `.frob`'s derived state instead of the
ticket ledger. T-2934 replaced the old unconditional, logged-but-silent
no-op on a platform without `fcntl` with two real backends: `msvcrt.
locking` on Windows (always EXCLUSIVE regardless of the requested mode --
`msvcrt` has no shared/read-lock primitive at all, a documented
conservative-concurrency tradeoff), and a loud `DerivedStateLockUnavailable`
refusal on any platform with neither primitive -- see `frob.gates.
_walk_lint`'s PLATFORM001 rule (docs/modules/gates.md#platform001-posix-
only-primitive-degrades-silently-t-2919), which found this exact site.

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

`_process_held_counts` (and therefore `_process_already_holds`,
T-0918/T-0933's no-op guard) is PROCESS-LOCAL: a `ProcessPoolExecutor`
worker forked/spawned from a parent that already holds `derived_state_lock`
starts with an empty registry of its own and cannot see the parent's hold
-- so a worker running `derived_state_write_lock` for the same root used to
issue a real, blocking `flock(LOCK_EX)` against the parent's own `LOCK_SH`
on a different open file description and deadlock forever (T-0982,
lslocks-confirmed: `dup_gate` in a pool worker vs. `frob check`'s main
process holding the run-wide SHARED lock -- the cross-process sibling of
T-0918's same-process case). T-0982 fixes this with an explicit,
pool-owner-supplied signal rather than trying to infer cross-process state:
`frob.gates._open_process_pool` snapshots its own
`held_registry_keys()` (every canonical key this process currently holds,
in any mode) into the env var `frob.process._lock._INHERITED_LOCK_KEYS_ENV`
BEFORE constructing the `ProcessPoolExecutor` -- env vars set before pool
construction are inherited by every worker it spawns (forkserver helper or
spawn). A worker's own `derived_state_write_lock` call checks
`_worker_inherits_hold(root)`, which reads that marker back: if the
worker's root matches a key the parent stamped, the worker trusts the
parent's guarantee and takes NO real OS lock of its own -- the same bypass
rule `_process_already_holds` already applies for a same-process nested
call, just carried across the fork/spawn boundary by an explicit signal
instead of shared memory. An INDEPENDENT process's pool worker (whose
parent never held `derived_state_lock` for that root) never sees its key in
the marker, so it falls through to a real, fully cross-process-exclusive
`flock(LOCK_EX)` exactly as before this fix.

## Forkserver reaping (T-2443)

`frob.process._reap` closes a measured leak: `frob check`'s gate-running
`ProcessPoolExecutor` (`frob.gates._open_process_pool`, `forkserver` start
method) tears itself down correctly on every NORMAL return/exception path,
but Python's DEFAULT `SIGTERM` disposition terminates the interpreter
immediately with no exception raised and no `finally` block run -- and this
fleet routinely wraps `frob check` in `timeout 540 ...`, which sends exactly
that signal. The worker processes `ProcessPoolExecutor` spawned survive
that kill untouched, and because each worker holds its own duplicate of the
forkserver helper's "alive" pipe write-end (stdlib
`multiprocessing.forkserver.ForkServer.connect_to_new_process` hands
`self._forkserver_alive_fd` to every child it creates), the helper's own
EOF-triggered shutdown only fires once EVERY holder of that fd -- the
parent AND every worker it ever spawned -- has exited. A live-fleet
measurement found 94 forkserver processes reparented to `/init`, 100% with
no live ancestor, holding 17.3GB of swap.

Two functions close this, both process-pool-construction-agnostic (neither
touches `frob.gates._open_process_pool`/`_run_combined_jobs` at all):

- `reap_active_multiprocessing_children` terminates (then, if needed,
  kills) every `multiprocessing.active_children()` process this
  interpreter still tracks -- a shared primitive generalized from
  `frob.serve._socketd._reap_multiprocessing_children`'s own T-1378
  daemon-shutdown precedent. `install_sigterm_reaper` (called once, from
  `frob.__main__.main`, before any subcommand dispatch) installs a
  `SIGTERM` handler that calls this, then chains to whatever handler was
  previously registered (or the platform default) -- so a killed `frob
  check`'s workers get reaped, their `alive`-pipe duplicates close, and
  the forkserver helper self-terminates exactly as it would on an
  unkilled, normal exit.
- `reap_orphaned_forkservers` is the defensive half: a `/proc` sweep
  (`_is_orphaned_forkserver` matches `multiprocessing.forkserver`'s own
  cmdline text plus `ppid == 1`) for forkserver helpers already reparented
  to init and older than `DEFAULT_ORPHAN_AGE_FLOOR_S` (300s), `SIGTERM`'d
  proactively. Called once at `frob check` startup (best-effort, never
  fatal to the real command) so a machine that already accumulated leaked
  forkservers keeps getting cleaned up going forward.

`scripts/fleet_status.py`'s `orphaned_forkserver_count` mirrors the same
cmdline+ppid detection in plain form (that script's own "no `frob` import"
contract) and surfaces the live count in `_print_land_status`'s report,
next to the existing swap-pressure guidance line.

T-2849: both functions above are best-effort/after-the-fact -- neither
runs on a `SIGKILL`ed launcher (uncatchable, no Python code runs at all),
which measured as the DOMINANT leak source in practice (~150 orphans
reaped by hand in one session, once reaching 16.7GB swap and stalling
every land for 45 minutes). `frob.gates._open_process_pool` now also
arms a structural, kernel-level fix that closes the leak at its root
instead of cleaning up after it:

- `arm_parent_death_signal` arms `PR_SET_PDEATHSIG` (Linux `prctl(2)`,
  via `ctypes`) on the calling process, so the kernel delivers the given
  signal the instant that process's DIRECT OS parent dies, by any means
  including `SIGKILL` -- including a self-kill fallback for the narrow
  fork/prctl race window where the parent exits between the two calls.
  T-2936: `sig` defaults to `None`, resolved to `signal.SIGKILL` only
  AFTER the function's own `sys.platform != "linux"` guard passes -- the
  pre-T-2936 signature (`sig: int = signal.SIGKILL`) bound that default
  at MODULE LOAD (a default argument is evaluated once, when the `def`
  statement itself runs), crashing the IMPORT of `frob.process._reap`
  -- and therefore every module that imports it -- on Windows
  (`signal.SIGKILL` does not exist there) with an `AttributeError`,
  before this function's own platform guard ever ran once. Measured for
  real via T-2917's windows-latest CI job: `frob --help` itself crashed
  in 54s, at `uv run frob natives build`'s own import of this module.
  T-2944: the `sys.platform != "linux"` guard's own body now logs a
  WARNING before returning `False`, so the degrade is loud from this
  function itself (not only from its caller,
  `_arm_forkserver_helper_pdeathsig_if_requested`, which already warned)
  -- closing a gap PLATFORM001's static scan flagged: a silent guard is
  invisible to it even when a caller elsewhere happens to log.
- The trap this closes: a `forkserver`-spawned WORKER's real OS parent is
  the persistent forkserver HELPER process, not the `frob check`
  launcher (workers are raw `fork()`ed from the helper, never `exec`ed,
  so they even inherit the helper's own `/proc/pid/cmdline`). Arming
  `PR_SET_PDEATHSIG` only on workers would track the helper's death, not
  the launcher's, and would not close the leak. The fix instead arms
  BOTH hops: `_open_process_pool` stamps `frob.process._reap.
  FORKSERVER_ARM_PDEATHSIG_ENV` into the environment before constructing
  the pool, so the freshly-started forkserver HELPER (named in `_open_
  process_pool`'s own `_FORKSERVER_PRELOAD`, imported once at helper
  startup) arms itself against the launcher, its real OS parent
  (`_arm_forkserver_helper_pdeathsig_if_requested`); the pool's
  `initializer` arms every WORKER against the helper, ITS real OS
  parent. Launcher death by any means now cascades: helper dies, then
  every worker dies in turn -- no `finally`/`atexit` involved anywhere
  in the chain.
- Verified with real fork/exec processes, both directions: a `SIGKILL`ed
  launcher now leaves zero forkserver/worker survivors (previously left
  both, reparented to init); a genuinely running pool's helper/workers
  are never touched while the launcher stays alive.

T-2880: T-2849's own before/after `getppid()` diff (see `arm_parent_death_
signal` above) only detects a parent that dies DURING the arm call -- it
was blind to a parent that already died BEFORE the function was even
entered (the real race: `fork()` returns in the child, the real parent
dies, then the child gets around to calling `arm_parent_death_signal` --
by then both the before and after `getppid()` reads already agree on the
new parent, pid 1/init, so the diff check finds nothing wrong and the
process arms `PR_SET_PDEATHSIG` against init, which never dies, so the
signal never fires). Live measurement after T-2849 landed showed the leak
continuing at roughly the pre-fix rate (27 new orphans in 49 minutes),
which is what this race produces: any worker/helper unlucky enough to
lose its real parent in the fork-to-arm window leaks exactly as before.
The fix: after arming, also check whether the CURRENT parent is pid 1
outright (not only whether it CHANGED) -- neither a forkserver helper's
real parent (the launcher) nor a worker's real parent (the helper) is
ever legitimately pid 1 in this codebase's process tree (no subreaper is
installed anywhere), so `getppid() == 1` at this point is unambiguous:
self-deliver the signal immediately rather than run on as an unreapable
orphan.

This does not replace `reap_active_multiprocessing_children`/`reap_
orphaned_forkservers` above -- those remain the defense-in-depth sweep
for leaks predating this fix or reached some other way; T-2818's
ancestry-walk oracle they build on
(`scripts/fleet_status.py::_forkserver_root_is_live_check`) is
unchanged and still the one place "is this forkserver orphaned" is
decided.

<!-- frob:doc docs/modules/process.md#pid-liveness-t-3018 -->
## PID liveness (T-3018)

`frob.process._pid_liveness.pid_alive(pid)` is the ONE safe cross-platform
liveness probe for "is this pid still running", extracted from
`frob.mutate._journal` (T-3003 fixed it there first) after `frob.tickets.
_land`'s `_probe_land_lock_pid_liveness` was found still using the unsafe
POSIX-shaped shape T-3003 had already fixed once (T-3018).

On POSIX, `os.kill(pid, 0)` is genuinely side-effect-free (signal `0`
sends nothing). On Windows it is NOT: CPython's `os.kill` opens the
target with `PROCESS_ALL_ACCESS` and calls `TerminateProcess(handle,
sig)`, so `sig=0` still terminates whatever process currently holds that
pid. Combined with Windows' fast PID reuse, a probe run just after a
process exits can find its pid already reassigned to an unrelated LIVE
process and kill it. `pid_alive` therefore never calls `os.kill` when a
Windows backend is available: it opens a query-only
`PROCESS_QUERY_LIMITED_INFORMATION` handle and reads `GetExitCodeProcess`/
`STILL_ACTIVE`, which cannot terminate anything.

Callers own their own interpretation of "no such pid" vs. "cannot tell"
-- `pid_alive` returns a plain `bool` (alive or not); a caller needing a
three-state confirmed-dead/ambiguous/alive split (e.g. `_land.py`'s land-
lock-holder reclaim logic, which must never auto-reclaim on an ambiguous
probe) still draws that distinction itself around `pid_alive`'s POSIX-
specific exception shape, the same way it always did.

`_kernel32` (module-level, resolved once) used to be a bare
`ctypes.windll.kernel32` wrapped in `try/except AttributeError` -- a
RUNTIME guard, invisible to a static type checker. `windll` is declared
in typeshed's `ctypes/__init__.pyi` only under `if sys.platform ==
"win32":`, so a `ty check --python-platform win32` target genuinely needs
a suppression there and a Linux target genuinely does not -- T-3191
measured this as a matched-opposite-error no single `ty: ignore` can
satisfy (required on one target, reported as an unused suppression, an
error in its own right, on the other). `_kernel32` is now resolved behind
an explicit `if sys.platform == "win32":` guard instead, which `ty`
narrows per `--python-platform` target exactly like typeshed's own stub
does -- the branch is checked with `windll` available on a win32 target
and treated as unreachable (never checked at all) on every other target.
No `ty: ignore` is needed in either direction. See "Multi-platform
typecheck (T-3191)" in `docs/commands/check.md` for how `frob check`
now reaches this diagnostic shape from a non-Windows host at all.

<!-- frob:doc docs/modules/process.md#concurrent-check-advisory-t-2473 -->
## Concurrent check advisory (T-2473)

RELATED BUT DISTINCT from the forkserver leak above: T-2443 fixed dead
workers holding memory after their parent died; this is about LIVE,
legitimate `frob check` processes -- normal fleet activity -- exceeding
the machine's capacity when too many run at once. Measured at six
implementer agents: 12 concurrent `frob check` processes at 0.5-1.1GB
each, swap climbing 2.1GB -> 7.8GB, load 15.7 -> 21.0, and completed
lands per hour going DOWN (9 -> 6) as agent count went UP -- overflow
into swap slows every check, which lengthens the window in which they
overlap, a self-reinforcing degradation with no equivalent to `frob
ticket land`'s own `land.lock` serialization.

The chosen fix is ADVISORY, not an enforced limit: a hard concurrency
cap risks turning a busy fleet into a queue of stalled agents if the
cap is chosen badly, and this repo consistently prefers surfacing over
commanding. Two read-only, best-effort pieces, both matching a live
`frob check` process by its `frob`/`check` argv token pair (as
SEPARATE tokens -- never a substring, which would also fire on <!-- frob:waive DOC006 reason="illustrative hypothetical false-positive example, not a real subcommand claim -- frob ticket evidence --check-repro is the real flag" -->`frob ticket check-repro` or a path containing "check"):

- `count_running_checks` (`frob.process._reap`) -- called from `frob.
  __main__`'s own `_report_concurrent_check_advisory_best_effort`, at
  the same startup seam as T-2443's forkserver reap, right before a
  `check` subcommand dispatches. Counts every OTHER live `frob check`
  process (excludes its own pid, so a single check on an idle machine
  reads 0 others -- the must-not-stall acceptance's own "no added
  latency, no new failure mode" requirement). Logs at INFO when others
  ARE running (so it shows in a normal log-level run without `-v`),
  WARNING at 4 or more (this host's own measured degradation point),
  and silently skips logging at 0 -- an idle machine's check gets no
  extra log noise. Best-effort and NEVER fatal: any exception (an
  unreadable `/proc` entry) is caught, logged at DEBUG, and swallowed,
  exactly like the forkserver reaper immediately before it. Returns
  `None` (unknown) on an unreadable `/proc`, mirroring `orphaned_
  forkserver_count`'s own contract.
- `scripts/fleet_status.py`'s `concurrent_check_count` -- the
  coordinator-facing counterpart: every live check on the host (no
  self-exclusion, since `fleet_status.py` itself is never a `frob
  check` process), surfaced as a `CONCURRENT CHECKS: N` line in
  `_print_land_status`'s standing report, the number a coordinator
  needs to decide whether to dispatch another agent -- previously
  invisible short of a manual `ps` scan.

Neither piece blocks, queues, or refuses a check -- there is currently
no case where a check is "deferred" under this fix, so the fail-loudly
"a deferred check must be visible" requirement is satisfied vacuously:
nothing is silently skipped because nothing is skipped at all. A future
enforced-limit direction, if one is chosen later, would need its own
visible-deferral mechanism at that point.

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
