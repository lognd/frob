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
6. Fallback for touched files with zero bindings, per `SelectConfig.
   fallback` (`--fallback` CLI knob, not a `frob.toml` table):
   `package` (default -- run the owning package's suite for
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
  automatically. A maturin PACKAGE (<!-- frob:waive DOC006 reason="name is a placeholder for the package's actual name, not a literal path" -->`name/__init__.py` + `name.abi3.so`) is
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
root-relative file path
<!-- frob:waive DOC006 reason="illustrative example paths/test names (tests.foo, tests.bar are placeholders), not real pointers -- frob-core has no dup_kernel.rs and strata-core/src/parse.rs was later split into strata-core/src/parse/ (T-1099)" -->
(`frob-core/src/dup_kernel.rs::tests.foo`,
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

T-1067: `frob.gitio.excerpt` (stdout/stderr blob -> last-N-lines truncation)
was made public and this module's own private duplicate of the same
function deleted -- `_run_one_language_selection`'s spawn-outcome path
(and `gitio._run_git`'s own failure logging) both import the one shared
copy now. No behavior change (same truncation rule, same default line
count).

T-1161: `collect_python_tests` now additionally records a human-readable
detail (spawned argv, exit code, `excerpt`-truncated stderr) whenever its
OUTER `pytest --collect-only` fails, readable via the new
`python_collection_failure_detail()`. The `Result[CollectedTests,
TestingError]` return contract itself is unchanged -- this is a SEPARATE,
additive module-level read, not a new failure shape -- so every existing
caller's `.is_err` handling keeps working exactly as before.
`frob.gates.coverage_gate`'s COV003 wiring is the first (and, for now,
only) consumer: it reads this detail right after seeing
`collect_python_tests(...).is_err` so a total pytest-collection failure
reports as ONE honest finding instead of degrading into a flood of
per-evidence COV003s (the 2026-07-28 incident: a corrupted `.venv/bin/
pytest` shim -- see `docs/guides/install.md#venv-shim-shebang-scan-t-1161`
-- broke `uv run pytest` outright, and 6219 archived evidence ids
each independently "failed to resolve" with no hint at the shared root
cause).

<!-- frob:describes src/frob/gitio.py::repo_root -->
<!-- frob:describes src/frob/gitio.py::working_diff -->
<!-- frob:describes src/frob/gitio.py::current_branch -->
<!-- frob:describes src/frob/gitio.py::run_argv -->
<!-- frob:describes src/frob/gitio.py::spawn_recorder -->
<!-- frob:describes src/frob/gitio.py::SpawnRecorder -->
<!-- frob:describes src/frob/gitio.py::excerpt -->
<!-- frob:describes src/frob/testing/_select.py::extension_language -->
<!-- frob:describes src/frob/testing/_select.py::select_tests -->
<!-- frob:describes src/frob/testing/_select.py::ALL_SENTINEL -->
<!-- frob:describes src/frob/testing/_runners.py::run_selected -->
<!-- frob:describes src/frob/testing/_runners.py::load_runners -->
<!-- frob:describes src/frob/testing/_collect.py::collect_python_tests -->
<!-- frob:describes src/frob/testing/_collect_rust.py::collect_rust_tests -->
<!-- frob:describes src/frob/testing/_collect.py::drop_collection_cache -->
<!-- frob:describes src/frob/testing/_collect.py::python_collection_failure_detail -->
<!-- frob:describes src/frob/testing/_runners.py::load_natives -->
<!-- frob:describes src/frob/strata/_native_test.py::run_native_sys_audit -->
<!-- frob:describes src/frob/strata/_native_test.py::NativeAuditOutcome -->
<!-- frob:describes src/frob/testing/_incremental_coverage.py::python_coverage_targets -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::run_coverage_wait -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::coverage_lock_path -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::CoverageWaitOutcome -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::CoverageWaitError -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::tree_digest -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::shared_state_dir -->
<!-- frob:describes src/frob/testing/_coverage_wait.py::SharedCoverageResult -->
<!-- frob:describes src/frob/testing/_coverage_cache.py::load_file_cache -->
<!-- frob:describes src/frob/testing/_coverage_cache.py::fill_from_cache -->
<!-- frob:describes src/frob/testing/_coverage_cache.py::update_file_cache -->
<!-- frob:describes src/frob/testing/_coverage_refresh.py::native_coverage_refresh -->
<!-- frob:describes src/frob/testing/_coverage_refresh.py::CoverageRefreshError -->

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

@contextmanager
def spawn_recorder() -> Iterator[SpawnRecorder]
    # Test-only: every run_argv spawn made while the block is active is
    # tallied onto the yielded SpawnRecorder. A single ContextVar.get()
    # per run_argv call outside this block -- zero-cost and behavior-
    # neutral when not active.

class SpawnRecorder:
    def record(self, argv: tuple[str, ...]) -> None
    def counts(self) -> Mapping[tuple[str, ...], int]
    def duplicates(self, budgets: Mapping[tuple[str, ...], int] | None = None,
                    *, default_budget: int = 1) -> dict[tuple[str, ...], int]
        # argv -> count for every argv spawned MORE than its budget
        # (default 1, i.e. "at most once"); {} means every spawn stayed
        # within budget.

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

# frob/testing/_coverage_wait.py (T-0322, cross-worktree layer T-1095)
def run_coverage_wait(root: Path, *, command: tuple[str, ...] | None = None
                      ) -> Result[CoverageWaitOutcome, CoverageWaitError]
    # Blocks in the foreground under a single-flight file lock
    # (.frob/coverage.lock) until the coverage stamp is fresh, running
    # `command` if it is not already -- the definitive-result alternative
    # to backgrounding `make coverage` and stalling on a notification a
    # dispatched sub-agent can never receive.
    #
    # T-1095: before the per-worktree lock/run above, checks a CROSS-
    # worktree layer first -- a shared, content-addressed cache keyed by
    # tree_digest(snapshot) under shared_state_dir(root). A cache hit (any
    # OTHER worktree of the same clone whose tracked source hashed
    # identically already settled this digest) adopts that result and
    # returns immediately with ZERO subprocess spawned; a miss acquires a
    # shared per-digest lock (serializing every worktree sharing the
    # digest onto ONE real run, not one per worktree), runs `command`, and
    # records the outcome for every other worktree sharing that digest to
    # find. Worktrees whose tracked content DIFFERS resolve to different
    # digests and so never contend or share a result with each other.
def coverage_lock_path(root: Path) -> Path
    # The single-flight lock path (.frob/coverage.lock) run_coverage_wait
    # guards concurrent callers WITHIN one worktree with (the ORIGINAL,
    # per-worktree layer; unchanged by T-1095's outer, cross-worktree one).
def tree_digest(snapshot: GraphSnapshot) -> str
    # T-1095: sha256 hex over `snapshot.file_hashes`' tracked *.py/*.rs/
    # *.ts/*.tsx entries, sorted by path -- identical tracked source (any
    # worktree, any path) produces the identical digest; any differing
    # file produces a different one.
def shared_state_dir(root: Path) -> Path
    # T-1095: <git-common-dir>/frob-coverage-shared/ -- ONE location per
    # CLONE (via frob.gitio.git_common_dir), not per worktree, so every
    # worktree of the same clone resolves to the same shared directory
    # regardless of its own path. Falls back to
    # <root>/.frob/frob-coverage-shared (worktree-local) when `root` is
    # not inside a git repository at all.

class CoverageWaitOutcome(BaseModel):    # frozen fields, not a frozen model
    ran: bool           # False: an already-fresh stamp (local OR shared) was
                         # found, nothing ran.
    duration_s: float   # 0.0 when ran is False and the hit was purely local;
                         # the ORIGINAL run's duration when adopted from the
                         # T-1095 shared cache.

class CoverageWaitError(ErrorSet):
    RunFailed = "the coverage subprocess exited non-zero"
    SnapshotUnavailable = "the obligation graph snapshot could not be built"

class SharedCoverageResult(BaseModel):    # T-1095
    ok: bool                    # whether the settled run succeeded.
    ran: bool                   # always True for a freshly-recorded entry.
    duration_s: float           # the ORIGINAL run's wall time.
    file_hashes: dict[str, str] # the settling worktree's tracked file hashes,
                                # so a later cache-hit caller can adopt them
                                # into its OWN local .frob/coverage-stamp.

# frob/testing/_coverage_cache.py (T-1517)
def load_file_cache(root: Path) -> dict[str, dict[str, object]]
    # The persisted path -> {content_hash, line_pct} cache at
    # .frob/coverage-file-cache.json, or {} if missing/unreadable -- a
    # missing cache is a cold start, not an error.
def fill_from_cache(data: CoverageData, *, file_hashes: Mapping[str, str],
                    cache: Mapping[str, dict[str, object]]) -> CoverageData
    # Backfills data.module_line for every file data itself did not
    # measure this run, from cache, but ONLY when the file's current
    # content hash still matches the cached entry's content_hash --
    # fresh data always wins, a changed file is never backfilled from a
    # stale cache entry.
def update_file_cache(root: Path, data: CoverageData, *,
                      file_hashes: Mapping[str, str]) -> dict[str, dict[str, object]]
    # Persists data's measured (path, content_hash) -> line_pct pairs
    # into the cache, merged with (not replacing) whatever was already
    # there -- a touched-set run's narrower coverage.xml never evicts an
    # unrelated file's still-valid cached percentage.

# frob/testing/_coverage_refresh.py (T-1516)
def native_coverage_refresh(root: Path, snapshot: GraphSnapshot, *,
                            base: str = "HEAD", full: bool = False,
                            cov_target: str = "src/frob"
                            ) -> Result[Unit, CoverageRefreshError]
    # The frob-native, cross-platform (Linux/macOS/Windows) replacement
    # for `make coverage`/`make coverage-fast`'s shell recipe: decides
    # cold-start-full vs. touched-set-incremental vs. nothing-to-do
    # (reusing python_coverage_targets), spawns pytest/coverage via
    # subprocess directly, and always ends with
    # frob.gates._coverage.stamp_coverage -- one Python entry point, no
    # Makefile/shell dependency. Deliberately does NOT port the Makefile
    # recipe's xdist-crash serial-rerun recovery or its configurable
    # rerun-deadline knobs (disclosed, not silently dropped) -- a caller
    # that needs that resilience still has it via `make coverage` (T-1526:
    # `make coverage-fast` is now a thin wrapper delegating to this
    # function's own `frob coverage` CLI entrypoint, so it no longer has
    # xdist-crash-recovery of its own; only `make coverage`'s full-suite
    # target keeps that shell-side resilience).

class CoverageRefreshError(ErrorSet):
    PytestFailed = "the pytest subprocess exited non-zero"
    CoverageXmlFailed = "`coverage xml` could not produce coverage.xml"
    StampFailed = "the post-run stamp_coverage call failed"
```

### Coverage as managed derived state (T-1516/T-1517)

Coverage data (`coverage.xml`, `.frob/coverage-stamp`,
`frob-coverage.lock.json`) is treated as managed derived state, the same
posture `frob.graph`'s own cache already applies to parsed-artifact data:
never hand-maintained, always reproducible from tracked source plus a
content-hash-keyed cache, and refreshed through ONE Python entry point
(`native_coverage_refresh`) rather than a shell recipe a caller has to
know to invoke. `frob.testing._coverage_cache`'s per-file cache
(`.frob/coverage-file-cache.json`) is the persistence layer underneath it:
a file whose content hash has not changed since its last real measurement
is never re-instrumented even indirectly, closing the gap `python_
coverage_targets`'s test-selection narrowing alone left open (a touched-
set run's own `coverage.xml` only ever contains data for files it
actually re-executed; the cache is what lets `stamp_coverage` still
report every OTHER unchanged file's real percentage instead of silently
dropping it). `native_coverage_refresh` is the orchestration layer on
top: given a `GraphSnapshot`, it decides whether a refresh is needed at
all and, if so, drives the actual `pytest`/`coverage` subprocess calls
before handing off to `stamp_coverage` -- callers (`run_coverage_wait`'s
`command=None` default path, T-1516) no longer need a Makefile target to
get a fresh, correctly-scoped stamp.

### T-1126: daemon-owned coverage lease (`frob_lease_acquire`/`frob_lease_release`)

`run_coverage_wait`'s OUTER single-flight lock (the one guarding THIS
worktree, distinct from T-1095's cross-worktree layer above) now prefers
the T-1097 daemon lease RPC over the original `_coverage_lock` file lock,
converging coverage arbitration onto the daemon when one is reachable for
`root` -- one owner, not two independent single-flight mechanisms that
happen to agree by convention. `frob.testing._coverage_wait._worktree_
lock` is the seam: it calls `frob.app._daemon_proxy.try_daemon_lease(root,
"coverage")`, which opens a PERSISTENT JSON-RPC connection (unlike `query
()`/`send_request`'s connect-send-recv-close-per-call shape) and sends
`frob_lease_acquire`. A daemon hit holds the lease across the whole
coverage run on that one connection; `release_daemon_lease` sends an
explicit `frob_lease_release` before closing it, but the connection
closing ALONE is also sufficient -- T-1097's server-side `finally` block
frees every lease a disconnecting connection still held, so a crashed
caller's lease is never stuck. `try_daemon_lease`'s `Err` (no daemon
reachable, `FROB_NO_DAEMON=1`, or the lease request itself errored) falls
back to `_coverage_lock` exactly as before this ticket -- the file lock
is the daemonless fallback, not replaced. T-1095's cross-worktree shared-
state layer (`shared_state_dir`/`tree_digest`) is untouched either way: a
daemon serves one worktree's own socket, not every worktree of the clone,
so it is not a substitute for that cross-CLONE primitive.

```python
# frob/app/_daemon_proxy.py (T-1126)
class _LeaseConnection:
    # A persistent raw JSON-RPC connection to root's daemon, used only for
    # holding a lease across a long-running operation -- promoted from
    # tests/test_serve_leases.py's own `_RawClient` test scaffold.
    def call(self, method: str, params: dict | None = None) -> dict
        # Send one request line, read one response line back.
    def close(self) -> None
        # Closing alone triggers the server's connection-liveness release.

def try_daemon_lease(root: Path, resource: str, *, capacity: int = 1,
                      timeout_s: float | None = None
                      ) -> Result[_LeaseConnection, ProxyReason]
    # Ok(conn): lease held on conn: caller does its work, then calls
    # release_daemon_lease(conn, resource) (or just lets conn drop).
    # Err(ProxyReason): no daemon reachable or the request errored --
    # caller falls back to its own (e.g. file-lock) arbitration.

def release_daemon_lease(conn: _LeaseConnection, resource: str) -> None
    # Best-effort explicit release, then closes conn either way.
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

## Spawn recorder (T-0776)

`tests/system/test_spawn_budget.py` is the exact-count complement to the
static loop-invariant-effect detector (`frob.perf`): rather than pattern-
matching code shape, it wraps a hot CLI entry point in
`frob.gitio.spawn_recorder()` and asserts no identical `git` argv was
spawned more than its declared budget (default 1) in one invocation. This
is heuristic-free -- it would have caught the T-0773 rev-parse-per-ticket-
row incident the day it regressed, and does not depend on recognizing any
particular code pattern.

<!-- frob:describes src/frob/gitio.py::spawn_recorder -->
```python
from frob.gitio import spawn_recorder

with spawn_recorder() as recorder:
    _list(root, cfg)          # or any code path that goes through run_argv

duplicated = recorder.duplicates()   # {} if every argv stayed within budget
assert duplicated == {}
```

Budgets live next to the tests, not in `frob.toml` -- passing a mapping to
`duplicates(budgets={...})` overrides the default-1 budget per exact argv
tuple, so a test that needs a path to spawn something N times on purpose
declares that N inline instead of the check gaining a config surface. The
recorder only sees spawns that go through `frob.gitio.run_argv` (the
package's one process-with-timeout seam, see "Public API" above) -- every
git spawn in the codebase already routes through it, so no site needs
updating to become visible to the recorder.

`test_ticket_list_spawns_each_argv_at_most_once` and
`test_ticket_doable_spawns_each_argv_at_most_once` are `xfail(strict=True)`
and tagged `frob:ticket T-0773`: both hit the same unmemoized
`git_common_dir` re-derivation the T-0773 rev-parse incident describes, so
they stay documented debt (not silently green, not silently red) until
T-0773 lands its memoization -- at which point the unexpected pass becomes
a hard failure demanding the marker's removal. `test_ticket_show_...` and
`test_exclude_hazard_gate_...` are plain, non-xfail budget locks: those two
paths already meet a 1-spawn-per-argv budget today, so a future regression
there is an immediate hard failure, not a documented one.

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
    NativeAuditFailed = "The native strata sys-audit invocation for a touched .strata selection could not load or evaluate the design model"
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
DEFAULT_REGRESSION_TAIL_K = 5   # default width of the recent-tail-window rule

def is_hard_regression(entry: StabilityEntry, *,
                       tail_k: int = DEFAULT_REGRESSION_TAIL_K) -> bool
    # HARD-REGRESSION RULE (T-0636, widened T-0679): history has at least 3
    # recorded runs, and EITHER the entire bounded history is all-fail OR
    # the most recent tail_k runs are all-fail (tail_k floored at 3, same as
    # the whole-window minimum). The tail rule exists because the
    # whole-window rule alone missed a real case: one stale pass anywhere
    # in the bounded HISTORY_WINDOW defeats all-fail detection for up to
    # HISTORY_WINDOW - 1 further runs even after the test has clearly gone
    # permanently red. Distinct from is_flaky's all-fail exclusion: is_flaky
    # says an all-fail history is "not flaky", but nothing said what a
    # currently-QUARANTINED test in that state means -- this is that
    # signal, one run higher than the flake minimum so the run right after
    # quarantine doesn't misfire.
def hard_regression_alarms(entries: Mapping[str, StabilityEntry], *,
                           tail_k: int = DEFAULT_REGRESSION_TAIL_K
                           ) -> tuple[str, ...]
    # HARD-REGRESSION ALARM: node ids currently quarantined whose history
    # has regressed to is_hard_regression (tail_k forwarded) -- the alarm
    # quarantine_alarms structurally cannot raise (see above). Pure, no
    # root/ticket lookup needed: the regression is visible from history
    # alone.
def evaluate_gate(ok: bool, failing_node_ids: frozenset[str],
                  entries: Mapping[str, StabilityEntry], *,
                  tail_k: int = DEFAULT_REGRESSION_TAIL_K) -> bool
    # Pure. If ok already True, unchanged. If False, promoted back to True
    # only when EVERY failing node id is currently quarantined AND not a
    # hard regression (is_hard_regression, tail_k forwarded) -- a
    # quarantined test that has regressed to all-fail (whole-window or
    # recent-tail-window) no longer gets promoted back to green just
    # because a quarantine_ticket is still set (T-0636/T-0679). One
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
    TicketUnresolvable   = "The named ticket id is absent from the queue"
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
- *Recent-tail-window widening* (T-0679): the T-0636 whole-window rule
  alone checks whether the ENTIRE bounded `HISTORY_WINDOW` history is
  all-fail, so a single stale pass anywhere in that window (e.g. from
  before quarantine, or a one-off flake that never repeated) defeats
  detection for up to `HISTORY_WINDOW - 1` subsequent all-fail runs even
  though the test has clearly gone permanently red since. `is_hard_regression`
  now also flags a test whose most recent `tail_k` runs (default
  `DEFAULT_REGRESSION_TAIL_K = 5`, floored at the same 3-run minimum as the
  whole-window rule) are all-fail, independent of what came earlier in the
  window. `hard_regression_alarms` and `evaluate_gate` both forward an
  optional `tail_k` to `is_hard_regression` so a caller can widen or narrow
  the window; the default keeps prior whole-window behavior as a strict
  subset (an all-fail whole window is always also an all-fail tail).

**Known limitation** (T-0575 cut): `capture_python_outcomes` zips `node_ids`
against a junit-xml report's `<testcase>` elements by run order rather than
re-deriving each node id from junit's own `classname`/`name` naming (which
is pytest's dotted module path, not this codebase's `path::Class::method`
symref convention) -- correct as long as pytest preserves argv order in its
junit output, which it does today.

**CLI wiring** (T-0635, closes T-0575's other disclosed cut):
`src/frob/app/test_runner.py`'s `_track_python_stability_and_gate` runs
after every `run_selected` call and, for a concrete python selection
(`report.selected["python"]`, skipped when it is empty or the
`ALL_SENTINEL` whole-suite marker -- neither names per-test node ids to
track against), captures a second, independent pytest invocation via
`capture_python_outcomes` over exactly those node ids, records it
(`record_outcomes`), and applies `evaluate_gate` to just the python portion
of the run's outcome (isolated from any other language's outcomes, which
this gate never touches, so a real non-python failure is never masked).
Any `quarantine_alarms`/`hard_regression_alarms` hit is logged as a
warning on the same run. `frob.testing.__init__` now re-exports
`is_hard_regression`/`hard_regression_alarms`/`DEFAULT_REGRESSION_TAIL_K`
alongside the rest of this module's public API, closing the re-export gap
T-0636's Done report left open. Running pytest a second time (rather than
reusing the primary run's own per-test results, which `RunnerOutcome`
does not carry) is a known cost of this v1 wiring, not a hidden one --
`RunnerOutcome` stays a whole-runner-invocation record; teaching it to
carry per-test results is a larger `_models.py`/`_runners.py` change left
for a future ticket if the double-invocation cost becomes a real problem.

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
  collision post-merge as `DuplicateId` (the gate fails loudly), and
  `frob ticket renumber` (`src/frob/_cli_parsers/_ticket/_progress.py`)
  is the shipped remedy.

## Design decisions

- **One git seam (`frob.gitio`)**, shared by gates and testing. The gates
  design's <!-- frob:waive DOC006 reason="historical reference to a proposed/superseded module path that never landed under this name" -->`gates/diff.py` is superseded by this module -- two diff
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
