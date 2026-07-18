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
4. Contract ripple (one hop): symbols holding a `uses-contract` edge to a
   touched symbol are treated as touched -- their tests run too.
5. Touched test files always run themselves.
6. Fallback for touched files with zero bindings, per `[testing.select]`
   `fallback`: `package` (default -- run the owning package's suite for
   that language), `suite` (whole language suite), or `warn` (skip and
   emit a warning; the TEST001 gate is what makes this safe to choose).

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
def collect_python_tests(root: Path) -> Result[CollectedTests, TestingError]

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
