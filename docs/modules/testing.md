# frob.testing -- touched-set test execution across languages

One sentence: `frob test` is the single entry point that computes what was
touched (diff vs base), selects every test obligated to those symbols via
the obligation graph, and runs them through per-language runners -- so "run
the right tests" is one command in any repo, any language, any worktree.

This is the executable counterpart of the TEST gate family (docs/modules/gates.md):
the gates prove the bindings exist; `frob test` runs the bound tests.

## Selection algorithm

1. `diff = working_diff(root, base)` -- committed-since-merge-base plus
   staged plus unstaged changes (the agent's whole delta in a worktree).
2. Touched set: hunks resolved to symrefs against the graph snapshot;
   files with no resolvable symbols count as touched files.
3. Direct tests: every `TESTS` edge (any kind) whose tested-source
   endpoint is a touched symbol, its enclosing class, its file, or its
   package. `frob:tests` is written on either endpoint in this codebase --
   above the source symbol, naming its covering test as the target, or
   above the test, naming what it covers as the target (`frob.gates`'
   convention) -- so selection identifies which endpoint is the test by
   whether that endpoint's file is itself a test file (T-0137), rather
   than assuming `target` is always the source. Only the resolved test
   endpoint is ever added to a runner's selection; the other (source)
   endpoint is never passed to a test runner, even if the touched set
   makes it look selected (e.g. a brand-new test file's own methods count
   as "touched," which used to leak the paired source symbol's node id
   into the pytest argv and crash collection).

   <!-- frob:invariant INV-023 -->
4. Contract ripple (T-0398 D-07: bounded multi-hop, up to 4 `uses-contract`
   hops -- widened from a single hop, which missed a caller two or more
   hops removed from a touched leaf): symbols holding a `uses-contract`
   edge to a touched symbol, or transitively to another ripple symbol, are
   treated as touched -- their tests run too.
5. Touched test files always run themselves.
6. Fallback for touched files with zero bindings, per `[testing.select]`
   `fallback`: `package` (default -- run the owning package's suite for
   that language), `suite` (whole language suite), or `warn` (skip and
   emit a warning; the TEST001 gate is what makes this safe to choose).
   Two refinements (T-0398):
   - D-04: a touched file whose extension maps to no known language at all
     (`.toml`/`.json`/`.yaml`/`.md`, config/data) cannot name a
     language-specific package -- `package`/`suite` both degrade to a
     suite-wide run across EVERY language the graph has symbols for,
     instead of silently selecting nothing. `warn` still only logs.
   - D-06: a touched file the graph already tracks (has symbols), but
     whose changed hunk(s) overlapped none of them (a module-level edit --
     an import, a module constant, a top-level side-effecting call), forces
     the `package` fallback even under `fallback="warn"`. A file whose
     touched hunk DID overlap a symbol (just one with no bound test) still
     respects `warn`'s ordinary accepted-risk skip.

`--all` skips selection and runs every configured runner's full suite.

## Runner registry (`frob.toml`, `[[test.runner]]`)

```toml
[[test.runner]]
language = "python"
command = ["uv", "run", "pytest", "-q", "{ids}"]     # {ids} -> node ids
all_command = ["uv", "run", "pytest", "-q"]
cwd = "."

[[test.runner]]
language = "rust"
command = ["cargo", "test", "--lib", "{filters}"]    # {filters} -> name filters
all_command = ["cargo", "test", "--lib"]
cwd = "strata-core"    # one crate per runner entry -- see "Rust runner" below

[[test.runner]]         # T-0128: a second same-language entry, cwd-scoped to
language = "rust"        # its own crate -- see "Rust runner" below for how
command = ["cargo", "test", "--lib", "{filters}"]     # routing between them
all_command = ["cargo", "test", "--lib"]              # works.
cwd = "frob-core"

[[test.runner]]
language = "typescript"
command = ["npx", "vitest", "run", "{files}"]        # {files} -> test files
all_command = ["npx", "vitest", "run"]
cwd = "web"

[[test.runner]]
language = "cpp"
command = ["ctest", "--test-dir", "build", "-R", "{regex}"]
all_command = ["ctest", "--test-dir", "build"]
cwd = "."
```

Placeholders: exactly one of `{ids}` (test node ids), `{files}` (test file
paths), `{filters}` (cargo-style name filters), `{regex}` (alternation of
test names). frob renders the selected tests into the placeholder's shape;
a language with selected tests but no runner is a hard error, not a skip.
For `{filters}` under `language = "rust"`, each selected symref's `path::a.b`
form is first reduced to cargo's own `a::b` filter spelling (the path prefix
means nothing to `cargo test`, and cargo module segments are `::`-joined, not
dot-joined) -- see `_to_rust_filter`. `frob scaffold` templates ship with
runners pre-filled. Every spawn goes through the typed subprocess seam with
an explicit timeout and full logging (lithos procio discipline).

## Native extensions (`frob.toml`, `[[native]]`, T-0333)

A test suite that `pytest.importorskip("strata_core")`-gates on a compiled
extension has a hidden dependency the collection cache cannot see on its own:
`collect_python_tests` keys its cache on test-FILE content, but building the
extension changes no test file. So a collection captured while the native was
unbuilt (its tests SKIP, and never enter the node-id set) survived every
rebuild -- reding COV003 on correctly-bound evidence until someone manually
deleted `.frob/pytest-collect.json`.

Declare each such module so collection can track its build state:

```toml
[[native]]
name = "strata_core"   # the python IMPORT name (find_spec), not a path
build_cmd = "make core"
language = "rust"       # optional, informational
```

- **Cache correctness.** The cache key folds in a fingerprint over each
  declared native's *compiled artifacts* (`.so`/`.pyd`/`.dylib`), found via
  `importlib.util.find_spec`. Because it hashes the compiled OUTPUT, it is
  toolchain- and platform-agnostic: it behaves identically for maturin/pyo3
  (Rust) and setuptools/pybind11/scikit-build (C/C++), on Linux, macOS, and
  Windows, x86 or arm. Going unbuilt -> built (absent -> hashed) OR a
  recompile (bytes change) flips the key and forces re-collection
  automatically. A maturin PACKAGE (`name/__init__.py` + `name.abi3.so`) is
  handled by fingerprinting the `.so` alongside the `__init__.py`, not the
  unchanged `__init__.py`.
- **Honest diagnostics.** When a declared native is unbuilt, COV003 names the
  module and its `build_cmd` ("native extension `strata_core` not built; run
  `make core`") instead of blaming the evidence id. The unbuilt natives are
  carried on `CollectedTests.missing_natives`.
- **Escape hatch.** `frob test --collect` drops and rebuilds the collection
  cache, then exits -- rarely needed now that the fingerprint invalidates
  automatically, but the honest remedy for a hand-edited cache.

## Rust runner

**Multiple runners per language (T-0128).** `frob-core` and `strata-core`
are two independent PyO3 crates with no unifying workspace `Cargo.toml`
(deliberately -- a workspace would couple their build/CI/maturin tooling for
no selection-side benefit). `run_selected` therefore allows several
`[[test.runner]]` entries to share `language = "rust"`, one per crate, each
scoped by its own `cwd`. Selected rust symrefs already carry their
root-relative file path (`frob-core/src/dup_kernel.rs::tests.foo`,
`strata-core/src/parse.rs::tests.bar` -- `collect_rust_tests` discovers both
crates generically), so routing an item to the right runner is a prefix
match: an item is owned by the one entry whose `cwd` prefixes its file path
(`cwd = "."` owns everything, preserving the single-runner-per-language
behavior other languages still use). An item owned by zero or more than one
same-language entry is `TestingError.UnroutedItem` -- a hard error, not a
silently-dropped test, matching T-0102's vacuous-pass posture. When a
language's selection is the `ALL_SENTINEL` (suite fallback fired, or
`--all`), every same-language runner's `all_command` runs -- the sentinel
names no specific crate, so all of them run.

`cargo test` for a PyO3 crate (`frob-core`, `strata-core` -- both build with
`extension-module` off, so linking needs libpython) needs two things cargo
cannot infer on its own: `PYO3_PYTHON` pointing at an interpreter meeting the
crate's abi3 floor (`abi3-py311` here, i.e. Python>=3.11), and that
interpreter's shared libpython directory on `LD_LIBRARY_PATH`. Without them
the build fails deep inside `pyo3-build-config` with a message that gives no
hint what's wrong.

Both the rust runner (`run_selected`) and rust test collection
(`collect_rust_tests`) resolve this env the same way before ever spawning
`cargo`:

1. Prefer an existing `PYO3_PYTHON` env var; otherwise probe
   `python3.13`, `python3.12`, `python3.11`, then plain `python3` (in that
   order) and keep the first one whose reported version is >= 3.11.
2. Ask that interpreter for `sysconfig.get_config_var("LIBDIR")` and prepend
   it to `LD_LIBRARY_PATH` for the subprocess only (`_env_overlay` patches
   `os.environ` for the duration of the call and restores it after --
   `frob.gitio.run_argv` has no `env=` parameter by design, so this is the
   one place a spawn's environment gets adjusted).
3. If no interpreter clears the floor, or its libpython directory cannot be
   resolved, both call sites return `Err(TestingError.CargoEnvUnavailable)`
   **before** spawning `cargo` at all -- never a silent skip, never an
   empty-but-successful test run (T-0102's vacuous-pass principle applies to
   the runner exactly as it does to the gates).

## Strata runner (native, T-0242)

`.strata` design files select under `language = "strata"` like any other
touched file, but they never need a `[[test.runner]]` entry: no subprocess
is spawned at all. `frob sys audit` has no per-item ids to place behind a
`{ids}`/`{files}`/`{filters}`/`{regex}` placeholder -- it always evaluates
the whole merged design model's exhaustiveness -- so a language runner
that took the only pre-T-0242 route (registering `frob sys audit` as a
`[[test.runner]]` command) had to invent a dummy placeholder token just to
satisfy `_validate_placeholder`'s "exactly one" rule (the malmberg pilot P3
workaround, 2026-07-18).

`_run_one_language_selection` special-cases `language == "strata"` before
it ever looks a runner up in `runners_by_lang`: it calls
`frob.strata.run_native_sys_audit(root)` in process (the same
`load_design_ids` -> `merge_models` -> `evaluate_exhaustiveness` ->
`check_self_conformance` composition `frob sys audit` itself runs, module
docstring of `frob/strata/_native_test.py`) and folds the resulting
`NativeAuditOutcome` into a single `RunnerOutcome` (`argv=("<native>",
"frob", "sys", "audit")`, marking where it came from since no real argv was
spawned; `exit_code` 0 iff `proved`, else 1; `stdout_tail` carries the
gap/proved summary). This is zero-config: touching a `.strata` file under
`frob test` invokes the audit whether or not the repo's `frob.toml`
declares anything for `strata` at all -- T-0149's per-repo `[[test.runner]]`
path still works for any OTHER command a repo wants, but is no longer
required for this one.

## Public API

<!-- frob:describes src/frob/gitio.py::repo_root -->
<!-- frob:describes src/frob/gitio.py::working_diff -->
<!-- frob:describes src/frob/gitio.py::current_branch -->
<!-- frob:describes src/frob/gitio.py::run_argv -->
<!-- frob:describes src/frob/testing/_select.py::extension_language -->
<!-- frob:describes src/frob/testing/_select.py::select_tests -->
<!-- frob:describes src/frob/testing/_select.py::ALL_SENTINEL -->
<!-- frob:describes src/frob/testing/_runners.py::run_selected -->
<!-- frob:describes src/frob/testing/_runners.py::load_runners -->
<!-- frob:describes src/frob/testing/_collect.py::collect_python_tests -->
<!-- frob:describes src/frob/testing/_collect.py::collect_rust_tests -->
<!-- frob:describes src/frob/testing/_collect.py::drop_collection_cache -->
<!-- frob:describes src/frob/testing/_runners.py::load_natives -->
<!-- frob:describes src/frob/strata/_native_test.py::run_native_sys_audit -->
<!-- frob:describes src/frob/strata/_native_test.py::NativeAuditOutcome -->
<!-- frob:describes src/frob/testing/_incremental_coverage.py::python_coverage_targets -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::run_coverage_wait -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::coverage_lock_path -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::CoverageWaitOutcome -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::CoverageWaitError -->

```python
# frob/gitio.py -- the ONE git subprocess seam (shared with frob.gates)
def repo_root(start: Path) -> Result[Path, GitError]
    # git rev-parse --show-toplevel; works identically inside a linked
    # worktree (.git file indirection is git's problem, not ours).
def working_diff(root: Path, base: str) -> Result[Diff, GitError]
    # merge-base(HEAD, base) .. worktree, including uncommitted changes.
def current_branch(root: Path) -> Result[str, GitError]
def run_argv(argv: Sequence[str], *, cwd: Path | None = None,
             timeout_s: float = 30.0) -> Result[ProcResult, GitError]
    # The one process-with-timeout primitive in the package. frob.testing
    # imports THIS function for its own runner/pytest spawns instead of
    # keeping a second copy -- frob.gitio must not import frob.testing, so
    # the shared helper lives in gitio and testing depends on it, not the
    # reverse.

# frob/testing/__init__.py
def extension_language(path: str) -> str | None
    # Documented duplicate of frob.lang's extension -> language-label
    # table (same posture as frob.graph's own copy); a public
    # extension-listing API on frob.lang was judged out of scope.
def select_tests(snapshot: GraphSnapshot, diff: Diff,
                 cfg: SelectConfig) -> SelectionReport
    # Pure; implements the selection algorithm above.
def run_selected(selection: SelectionReport, runners: tuple[RunnerSpec, ...],
                 root: Path) -> Result[TestRunReport, TestingError]
    # Groups by language, renders placeholders, spawns runners, merges
    # per-runner outcomes; runner exit codes are data in the report.
    # T-0128: a language may resolve to several runners (e.g. two rust
    # crates); each selected item is routed to the one runner whose cwd
    # owns its file (Err UnroutedItem if zero or more than one match).
def load_runners(root: Path) -> Result[tuple[RunnerSpec, ...], TestingError]
def load_natives(root: Path) -> Result[tuple[NativeSpec, ...], TestingError]
    # frob.toml [[native]] entries (T-0333): compiled extension modules the
    # suite importorskip-gates on, so collection can fingerprint their build
    # state and COV003 can name the real build remedy.
def collect_python_tests(root: Path) -> Result[CollectedTests, TestingError]
def drop_collection_cache(root: Path) -> bool
    # `frob test --collect`: delete the pytest collection cache so the next
    # collection re-runs from scratch (T-0333 escape hatch).

ALL_SENTINEL = "*"
    # The all-suite marker in a language's selected-tests tuple; run_selected
    # renders the runner's all_command instead of the per-file command.
    # pytest --collect-only cache (moved here from the gates design; the
    # TEST gates import it from frob.testing).
def collect_rust_tests(root: Path) -> Result[CollectedTests, TestingError]
    # `cargo test --lib -- --list` cache, one entry per discovered
    # Cargo.toml; Err (not an empty Ok) when the PyO3 env cannot be
    # resolved -- see "Rust runner" above. Merged with collect_python_tests
    # by frob.gates._load_tests into one CollectedTests for COV003.

# frob/testing/_incremental_coverage.py (T-0484)
def python_coverage_targets(root: Path, snapshot: GraphSnapshot,
                            base: str) -> tuple[str, ...]
    # The touched set's selected python pytest targets against base, via
    # select_tests -- feeds `make coverage-fast`'s touched-set-only,
    # --cov-append coverage run instead of a full-suite re-run per change.
    # () on a diff/selection failure or an empty selection; never raises.

# frob/testing/_coverage_wait.py (T-0322)
def run_coverage_wait(root: Path, *, command: tuple[str, ...] = ("make", "coverage-fast")
                      ) -> Result[CoverageWaitOutcome, CoverageWaitError]
    # Blocks in the foreground under a single-flight file lock
    # (.frob/coverage.lock) until the coverage stamp is fresh, running
    # `command` if it is not already -- the definitive-result alternative
    # to backgrounding `make coverage` and stalling on a notification a
    # dispatched sub-agent can never receive.
def coverage_lock_path(root: Path) -> Path
    # The single-flight lock path (.frob/coverage.lock) run_coverage_wait
    # guards concurrent callers with.

class CoverageWaitOutcome(BaseModel):    # frozen fields, not a frozen model
    ran: bool           # False: an already-fresh stamp was found, nothing ran.
    duration_s: float   # 0.0 when ran is False.

class CoverageWaitError(ErrorSet):
    RunFailed = "the coverage subprocess exited non-zero"
    SnapshotUnavailable = "the obligation graph snapshot could not be built"
```

**Deviation**: `frob.testing`'s `suite` fallback mode is threaded through the
same `selected: Mapping[str, tuple[str, ...]]` field `SelectionReport`
already has, rather than a new field -- a language whose fallback fired in
`suite` mode gets a single sentinel string (`"*"`, exported as
`frob.testing._select.ALL_SENTINEL`) inserted into its selected tuple;
`run_selected` recognizes the sentinel and renders `all_command` for that
language instead of placeholder-substituting `command`. This keeps
`SelectionReport` exactly as specified while still letting `select_tests`
stay pure (the decision is fully resolved by the time `run_selected` reads
it, with no separate side-channel of "languages needing --all").

## Data models

```python
class RunnerSpec(BaseModel):     # frozen; one [[test.runner]] entry
    language: str
    command: tuple[str, ...]
    all_command: tuple[str, ...]
    cwd: str = "."
    timeout_s: float = 900.0

class NativeSpec(BaseModel):     # frozen; one [[native]] entry (T-0333)
    name: str                     # python import name (find_spec), not a path
    build_cmd: str                # e.g. "make core"
    language: str = ""            # optional, informational

class SelectConfig(BaseModel):    # frozen; selection knobs
    fallback: str = "package"     # unbound-file policy: package|suite|warn

class SelectionReport(BaseModel)  # frozen
    touched: tuple[str, ...]              # symrefs and bare files
    selected: Mapping[str, tuple[str, ...]]   # language -> test ids/files
    ripple: tuple[str, ...]               # symbols pulled in via uses-contract
    unbound: tuple[str, ...]              # touched files with no bindings
    fallback: str

class RunnerOutcome(BaseModel)    # frozen
    language: str
    argv: tuple[str, ...]
    exit_code: int
    duration_s: float
    stdout_tail: str              # bounded excerpt, lithos-style
    stderr_tail: str

class TestRunReport(BaseModel)    # frozen
    selection: SelectionReport
    outcomes: tuple[RunnerOutcome, ...]
    ok: bool                      # every runner exited zero

class CollectedTests(BaseModel):  # frozen; collect_python_tests + collect_rust_tests
    node_ids: frozenset[str]      # every pytest node id and cargo test symref
    missing_natives: tuple[NativeSpec, ...] = ()   # declared-but-unbuilt (T-0333)

class Hunk(BaseModel):            # frozen; one gitio.py touched-line range
    file: str
    span: tuple[int, int]

class Diff(BaseModel):            # frozen; gitio.py working-tree delta
    base: str
    hunks: tuple[Hunk, ...]

class ProcResult(BaseModel):      # frozen; gitio.py's one spawn result shape
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
```

## Error types

```python
class GitError(ErrorSet):
    NotARepo    = "Path is not inside a git repository or worktree"
    GitFailed   = "git subprocess failed"

class TestingError(ErrorSet):
    NoRunner       = "A language has selected tests but no [[test.runner]]"
    BadRunnerSpec  = "Runner entry failed validation or has no placeholder"
    SpawnFailed    = "Runner process could not be started or timed out"
    CollectFailed  = "pytest --collect-only failed"
    CargoEnvUnavailable = "cargo test needs a Python>=3.11 dev environment frob could not find"
    UnroutedItem   = "A selected item's file matched zero or >1 same-language [[test.runner]] cwd"
```

## Flake quarantine (T-0575)

A flaky test blocks every parallel agent working through `frob test`: a
single intermittent failure looks the same as a real regression, and an
agent either wrongly reverts good work chasing it, or starts ignoring red
runs altogether. `frob.testing._stability` gives per-test pass/fail history
a static flake rule, and a quarantine mechanism that always carries a real
ticket id -- never a silent skip-list.

<!-- frob:describes src/frob/testing/_stability.py::load_stability -->
<!-- frob:describes src/frob/testing/_stability.py::record_outcomes -->
<!-- frob:describes src/frob/testing/_stability.py::is_flaky -->
<!-- frob:describes src/frob/testing/_stability.py::flaky_node_ids -->
<!-- frob:describes src/frob/testing/_stability.py::quarantined_node_ids -->
<!-- frob:describes src/frob/testing/_stability.py::quarantine -->
<!-- frob:describes src/frob/testing/_stability.py::lift_quarantine -->
<!-- frob:describes src/frob/testing/_stability.py::quarantine_alarms -->
<!-- frob:describes src/frob/testing/_stability.py::is_hard_regression -->
<!-- frob:describes src/frob/testing/_stability.py::hard_regression_alarms -->
<!-- frob:describes src/frob/testing/_stability.py::evaluate_gate -->
<!-- frob:describes src/frob/testing/_stability.py::capture_python_outcomes -->
<!-- frob:describes src/frob/testing/_stability.py::track_python_stability -->

```python
# frob/testing/_stability.py
class StabilityEntry(BaseModel):   # frozen; one test's stability record
    node_id: str
    history: tuple[str, ...] = ()          # "P"/"F", most-recent-last, bounded
    quarantine_ticket: str | None = None
    quarantined_at: str | None = None

HISTORY_WINDOW = 20   # only the last N runs count toward flake detection/storage

def load_stability(root: Path) -> dict[str, StabilityEntry]
    # Every recorded entry, keyed by node id; {} if .frob/test-stability.json
    # is absent/unreadable -- no history yet is not an error.
def record_outcomes(root: Path, outcomes: Mapping[str, bool]
                    ) -> Result[dict[str, StabilityEntry], FlakeError]
    # Append one pass/fail per node id onto its window-bounded history and
    # persist; quarantine fields carry forward untouched.
def is_flaky(entry: StabilityEntry) -> bool
    # THE FLAKE RULE: history contains BOTH a pass and a fail. All-pass and
    # all-fail are NOT flaky (an all-fail test is a real regression, not a
    # flake). Fewer than 2 recorded runs is never flaky.
def flaky_node_ids(entries: Mapping[str, StabilityEntry]) -> frozenset[str]
def quarantined_node_ids(entries: Mapping[str, StabilityEntry]) -> frozenset[str]
def quarantine(root: Path, node_id: str, *, ticket_id: str | None = None
              ) -> Result[str, FlakeError]
    # Quarantine node_id: still runs, still reported, does not fail the
    # gate. NEVER a silent skip-list -- ticket_id must resolve to a real,
    # still-open ticket (Err TicketUnresolvable otherwise); if omitted, a
    # bug ticket is auto-filed via frob.tickets.new_ticket (the public
    # ticket-creation API -- this module never touches frob.tickets
    # internals). Returns the ticket id now owning the quarantine.
def lift_quarantine(root: Path, node_id: str) -> Result[Unit, FlakeError]
    # Clears quarantine fields, keeps history. Err UnknownTest if node_id
    # has no recorded entry.
def quarantine_alarms(root: Path, entries: Mapping[str, StabilityEntry]
                      ) -> tuple[str, ...]
    # EXPIRY ALARM: node ids whose quarantine ticket has closed (DONE or
    # DROPPED) -- or no longer resolves at all -- while the test is STILL
    # flaky. The flake was never actually fixed; a quarantine must not
    # silently outlive its own ticket's closure. Does NOT cover a
    # regressed-to-all-fail quarantine (see is_hard_regression below) --
    # that test is by definition no longer flaky, so it can never trip this
    # alarm's is_flaky filter.
def is_hard_regression(entry: StabilityEntry) -> bool
    # HARD-REGRESSION RULE (T-0636): history has at least 3 recorded runs
    # and EVERY one is a fail. Distinct from is_flaky's all-fail exclusion:
    # is_flaky says an all-fail history is "not flaky", but nothing said
    # what a currently-QUARANTINED test in that state means -- this is that
    # signal, one run higher than the flake minimum so the run right after
    # quarantine doesn't misfire.
def hard_regression_alarms(entries: Mapping[str, StabilityEntry]
                           ) -> tuple[str, ...]
    # HARD-REGRESSION ALARM: node ids currently quarantined whose history
    # has regressed to is_hard_regression -- the alarm quarantine_alarms
    # structurally cannot raise (see above). Pure, no root/ticket lookup
    # needed: the regression is visible from history alone.
def evaluate_gate(ok: bool, failing_node_ids: frozenset[str],
                  entries: Mapping[str, StabilityEntry]) -> bool
    # Pure. If ok already True, unchanged. If False, promoted back to True
    # only when EVERY failing node id is currently quarantined AND not a
    # hard regression (is_hard_regression) -- a quarantined test that has
    # regressed to all-fail no longer gets promoted back to green just
    # because a quarantine_ticket is still set (T-0636). One
    # non-quarantined or hard-regressed failure keeps the run failed.
def capture_python_outcomes(root: Path, node_ids: tuple[str, ...], *,
                            cwd: str = ".") -> Result[dict[str, bool], FlakeError]
    # Runs node_ids directly via `uv run pytest --junit-xml`, bypassing any
    # configured [[test.runner]] template (which has no report-path
    # placeholder), and parses per-test pass/fail from the report.
def track_python_stability(root: Path, node_ids: tuple[str, ...], *,
                           cwd: str = ".") -> Result[dict[str, StabilityEntry], FlakeError]
    # capture_python_outcomes + record_outcomes in one call.

class FlakeError(ErrorSet):
    WriteFailed          = "Could not persist .frob/test-stability.json"
    ReadFailed           = "Could not read/parse .frob/test-stability.json"
    UnknownTest          = "The node id has no recorded stability history"
    TicketUnresolvable   = "The named ticket id does not exist in the queue"
    TicketCreateFailed   = "Auto-filing a quarantine ticket via frob.tickets failed"
    CaptureSpawnFailed   = "pytest could not be spawned for per-test stability capture"
    CaptureReadFailed    = "The junit-xml report from a stability capture run was unreadable"
```

**Storage shape**: `.frob/test-stability.json`, `{"tests": {<node_id>:
{node_id, history, quarantine_ticket, quarantined_at}}}` -- per-worktree
derived state, same posture as the pytest-collection cache and the
coverage stamp (never shared across checkouts).

**Flake detection rule**: a test is flaky iff its bounded history (last
`HISTORY_WINDOW` runs) contains both a pass and a fail. This deliberately
does NOT flag a consistently all-failing test -- that is a real
regression, and must stay a hard gate failure, not quarantine-eligible.

**Quarantine semantics**:
- *Enter*: `quarantine(root, node_id, ticket_id=...)` -- always ties to a
  real, resolvable, still-open ticket (auto-filed via the public
  `frob.tickets.new_ticket` API when omitted). A quarantined test still
  runs and still reports; `evaluate_gate` is what actually keeps the gate
  green around it.
- *Exit*: `lift_quarantine(root, node_id)` -- explicit only; going stable
  again does NOT auto-lift a quarantine (a human/agent decision closes the
  loop, matching the ticket it's tied to).
- *Expiry/alarm*: `quarantine_alarms` flags any quarantine whose ticket has
  closed (or gone unresolvable) while the test is still flaky -- the
  signal that a quarantine ticket was closed without actually fixing the
  flake.
- *Hard-regression/alarm* (T-0636): a quarantined test's history can
  regress to all-fail -- by `is_flaky`'s own rule that means it has
  STOPPED being flaky, so it silently falls out of `quarantine_alarms`'s
  filter and, before this fix, `evaluate_gate` kept promoting it to green
  on quarantine status alone forever: a live quarantine masking a genuine,
  permanent regression with neither gate failure nor alarm. Two separate
  changes close this:
  - `evaluate_gate` now excludes any quarantined node id that
    `is_hard_regression` flags from the "excused" set, so a hard-regressed
    quarantined test keeps the gate red even though `quarantine_ticket` is
    still set.
  - `hard_regression_alarms` is a new, separate alarm (deliberately not
    merged into `quarantine_alarms`, since the two call for different
    responses -- re-triage a ticket that closed too early, vs. a fix that
    was never applied at all) that flags any currently-quarantined node id
    whose history is now `is_hard_regression`, independent of the ticket's
    own open/closed state.

**Known limitation** (T-0575 cut, filed as a follow-up): `capture_python_outcomes`
zips `node_ids` against a junit-xml report's `<testcase>` elements by run
order rather than re-deriving each node id from junit's own
`classname`/`name` naming (which is pytest's dotted module path, not this
codebase's `path::Class::method` symref convention) -- correct as long as
pytest preserves argv order in its junit output, which it does today.
Wiring `frob test`'s CLI (`src/frob/app/test_runner.py`, out of this
ticket's scope) to call `track_python_stability`/`evaluate_gate`
automatically on every run is left to a follow-up ticket; the same follow-up
also needs to surface `hard_regression_alarms` (T-0636) in that reporting
path and re-export `is_hard_regression`/`hard_regression_alarms` from
`frob.testing.__init__`, both currently out of this module's own scope.

## Git worktrees

The worktree workflow (one agent per worktree on its own branch) is a
first-class target, not an afterthought:

- **Root discovery**: every git call goes through `frob.gitio` using
  `git -C <root>`; `repo_root` resolves via `rev-parse --show-toplevel`,
  which is worktree-correct. frob never touches `.git` internals directly.
- **Per-worktree derived state**: `.frob/` (graph cache, coverage stamp,
  pytest-collection cache, cargo-collection cache) lives at each worktree's
  own root and is never shared -- caches are cheap to rebuild incrementally
  and sharing them across checkouts of different commits would poison
  incremental hashing.
- **Base semantics**: `frob test` (and the scope gate) diff against
  `merge-base(HEAD, base)`, so in an agent worktree the touched set is
  exactly that agent's delta -- the common point the user asked for: the
  same command means "test my changes" in the main checkout and in any
  worktree.
- **Tracked truth merges like code**: tickets, invariants, frob.lock, and
  annotations are ordinary tracked files, so worktree branches carry their
  own view and merge through git. Known seam: two worktrees can allocate
  the same sequential ticket id (T-0043 twice); `load_queue` detects the
  collision post-merge as `DuplicateId` (the gate fails loudly), and a
  `frob ticket renumber` remedy is tracked as ticket T-0162.

## Design decisions

- **One git seam (`frob.gitio`)**, shared by gates and testing. The gates
  design's `gates/diff.py` is superseded by this module -- two diff
  implementations would desync (docs/modules/gates.md updated accordingly).
- **Selection is graph-driven, not coverage-driven.** Coverage maps tell
  you what code a test ran last time; the graph tells you what a test is
  FOR. Declared bindings survive refactors and work identically across
  languages that have no coverage tooling wired up.
- **Fallback defaults to `package`, not `skip`.** An unbound touched file
  must still get tested conservatively; TEST001 shrinks the unbound set
  over time until fallback never fires.
- **Runner exit codes are report data, not process errors.** A failing
  test is a normal outcome the caller renders; only spawn/config problems
  are Err (the lithos run_argv/run_tool split).
- **`frob check` stays static; `frob test` executes.** check verifies the
  bindings exist (TEST gates); test runs them. The pair is the workflow:
  check tells you that you owe tests, test runs the ones you have.

## Dependencies

- `frob.graph` (snapshot, TESTS/uses-contract edges), `frob.gitio`,
  `frob.lang` (language of a file), `pydantic`, `typani`; git and the
  configured runners via subprocess.

## Integration points

- CLI: `frob test [--all] [--base REF] [--lang L ...] [--fallback MODE]`.
- `frob.gates`: imports `working_diff`/`Diff` from `frob.gitio` and
  `collect_python_tests`/`collect_rust_tests` from `frob.testing`, merged in
  `_load_tests` into one `CollectedTests` COV003 resolves evidence against.
- Agents: implementer runs `frob test` before writing a done-report;
  `skills/next` treats a red `frob test` as a blocker on close.
- CI: `frob test --all` plus `make coverage` for the stamp.
- T-0538: `make coverage`/`make coverage-fast` both depend on `$(STAMP)`
  (`uv sync`), which reconciles the venv against only the declared
  dependency set and silently REMOVES the editable `strata_core`/
  `frob_core` natives `make core` installed (they are local maturin path
  packages, not a declared dependency `uv sync` knows to keep). Both
  Makefile targets now run `make core` (restore the natives) followed by
  `frob doctor` (fail on one clear line if a native is still missing --
  e.g. no Rust toolchain) BEFORE pytest ever collects, instead of letting
  the clobber surface as an oblique mid-suite
  `ModuleNotFoundError: strata_core` and a pile of downstream `frob check`
  fallout (SYS004/COV003/DRIFT).
