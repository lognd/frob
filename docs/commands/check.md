# frob check

Aggregate quality gate. Runs all static analysis tools in sequence, surfaces
errors first, and exits non-zero if any tool reports errors.

## Usage

<!-- frob:describes src/frob/_cli_parsers/_check.py::_add_check_parser -->
```bash
frob check src/                        # Python (auto-detected)
frob check src/ --type python          # force Python mode
frob check src/ --type cpp             # C++/CMake mode
frob check src/ --type rust            # Rust/Cargo mode
frob check src/ --type typescript      # npm/TypeScript mode
frob check src/ --json                 # machine-readable output
frob check --budget 100                # self-select --only chunks to fit 100s (T-1004)
```

`--budget SECONDS` self-selects and orders `--only` stage groups
(`frob.check.available_stages()`) to fit inside `SECONDS`, using a
persisted rolling estimate of how long each group actually took last time
(`.frob/check-budget-timing.json`). It runs the selected subset in one
process, and if anything did not fit, persists the remainder as resume
state (`.frob/check-budget-state.json`) and reports it as a `BUDGET001`
warning naming every deferred group. Re-running the same command
continues from the resume state. See `docs/guides/agent-playbook.md`
section 3b for the full agent recipe.

T-2809: the post-land sweep's own derived budget
(`_derive_post_land_sweep_budget_s`, which also feeds the land-lock wait
ceiling `_resolve_land_lock_wait_budget_s` computes) does NOT read the
plain EMA above directly. It reads a separate bounded per-group window of
raw recent samples (`.frob/check-budget-timing-samples.json`) and uses the
MINIMUM of that window per group, falling back to the EMA for any group
the window has not covered yet. This closes a load feedback loop: the
plain EMA re-records every run including ones made under heavy fleet
contention, so a busy box inflated the estimate, which shrank the land
lock's wait ceiling, which made lands decline and retry, which added more
load. A per-group minimum cannot be inflated by contention (contention
only ever pushes a wall-clock sample up), while a genuine, sustained
slowdown still raises it once enough consecutive runs measure the new
cost.

T-2235: EVERY `--budget` invocation -- not just one that defers work --
also reports a `"budget"` JSON key
(`{"requested_seconds", "executed_groups", "skipped_groups", "complete"}`)
and, whenever `skipped_groups` is non-empty, an unconditional stderr
`WARNING` naming every stage group that did NOT run THIS call, regardless
of `--json`. `skipped_groups` is computed against the FULL
`available_stages()` universe, not against this call's own resume-derived
`deferred` list -- a call that inherits an already-narrow resume state
(e.g. one stage group left over from an earlier invocation) can report
zero `BUDGET001` deferrals while still having skipped most of the
universe, and that is exactly the case `"budget"`'s `skipped_groups`
makes visible: an empty list (present, not absent) means this
invocation truly executed everything; a non-empty list names what it
did not, whether or not that gap is "deferred" for the next call.
`"budget"` is absent entirely on every non-`--budget` call -- the
unbudgeted `--json` shape is unchanged.

## Public API

<!-- frob:describes src/frob/check/__init__.py::CheckResult -->
<!-- frob:describes src/frob/check/__init__.py::CheckResult.total_errors -->
<!-- frob:describes src/frob/check/__init__.py::CheckResult.total_warnings -->
<!-- frob:describes src/frob/check/__init__.py::CheckResult.as_text -->
<!-- frob:describes src/frob/check/__init__.py::CheckResult.as_json -->
<!-- frob:describes src/frob/check/__init__.py::run_check -->
<!-- frob:describes src/frob/check/__init__.py::run_check_cpp -->
<!-- frob:describes src/frob/check/__init__.py::run_check_rust -->
<!-- frob:describes src/frob/check/__init__.py::run_check_ts -->
<!-- frob:describes src/frob/check/__init__.py::detect_project_type -->
<!-- frob:describes src/frob/check/__init__.py::available_stages -->

```python
# frob/check/__init__.py
class CheckResult(BaseModel)
    # Aggregate outcome of one `frob check` run: every tool's ToolResult,
    # plus the derived error/warning counts and text/JSON renderers.
    path: str
    results: list[ToolResult]
    total_errors: int      # property; sum of error diagnostics across tools
    total_warnings: int    # property; sum of warning diagnostics across tools
    def as_text(self, color: bool = False) -> str
        # Human report: errors, warnings, notes, then a per-tool summary
        # table -- each line's icon is pass/FAIL, or UNRES (T-2891) for a
        # gate:X result that is entirely UNRESOLVED (see "Tool summary:
        # pass / FAIL / UNRES" below); UNRES never changes exit_code.
    def as_json(self) -> str
        # The full structured result as JSON (--json CLI output).

def run_check(root: Path, *, skip_ruff=False, skip_ty=False, ..., only=None,
              ticket=None, base=None) -> CheckResult
    # Python quality gate: ruff, ty, cycle/dup/arch/bind/exports, then gates
    # (docs/modules/gates.md) -- the entry point `frob check` dispatches to for a
    # Python project (or --type python).
def run_check_cpp(root: Path, *, build_dir=None, skip_build=False, ...,
                   valgrind: bool = False) -> CheckResult
    # Quality gate for CMake C/C++ projects: cmake build, clang-tidy,
    # clang-format, ctest -- a failed build short-circuits the test stage.
def run_check_rust(root: Path, *, skip_check=False, skip_clippy=False, ...,
                    valgrind: bool = False) -> CheckResult
    # Quality gate for Rust/Cargo projects: cargo check, clippy, fmt --check,
    # cargo test.
def run_check_ts(root: Path, *, skip_tsc=False, skip_eslint=False, ...,
                  skip_tests: bool = False) -> CheckResult
    # Quality gate for npm/TypeScript projects: tsc, eslint, prettier,
    # vitest; a missing node/npx toolchain is a soft skip per stage.
def detect_project_type(root: Path) -> str
    # Sentinel-file auto-detection: 'rust'|'cpp'|'python'|'typescript'|
    # 'unknown', per the Auto-detection table below.
def available_stages() -> list[str]
    # Sorted `--only` stage-group alias names (T-0627): 'gates-fast',
    # 'gates-native', 'gates-security', 'lint', 'static'. What
    # `frob check --only list` prints.
```

## Python mode

Before any stage runs, two synchronous fail-closed prechecks run once (not
concurrently with any stage): a `DERIVED001` corrupt-derived-artifact check,
and a `NATIVE001` native-staleness check (T-2764) -- `frob.check.
_native_staleness_result` reuses the SAME rebuild-then-recheck logic
`frob.gates.run_gates`'s own gates-stage self-heal already uses (T-1213):
a stale native is rebuilt in place and reported only if it is STILL stale
afterward (no toolchain, auto-rebuild disabled via `FROB_NO_NATIVE_
AUTOREBUILD`/`natives_auto_rebuild = false`, or a genuine build failure).
This closes a real workflow-parity gap with `make check`'s separate
`check_native_staleness_or_exit` pre-step: previously, a `--skip-gates`
run or an `--only` selection that never reached the `gates` stage had NO
staleness guard at all, since the self-heal only ever ran from inside
that one stage.

Runs in order:
1. `ruff check` -- lint errors
2. `ruff format --check` -- format violations
3. `ty check` -- type errors
4. `frob cycle` -- import cycles
5. `frob dup` -- duplicate code blocks
6. `frob arch` -- architectural violations (long functions, god classes)
7. `frob bind` -- pybind11/PyO3 BIND coverage
8. `frob exports` -- missing `__init__.py` exports
9. PyCharm inspection (if auto-located)
10. `gates` -- `frob.gates.run_gates` (docs/modules/gates.md): drift, coverage, scope,
    pre-work, invariant, test, and policy rule violations. A load failure
    (e.g. not a git repo, no `tickets/`) is a soft skip, not a check failure;
    any `ERROR`-severity violation fails the stage like any other tool.

Output order: errors first, then warnings, then notes. Each tool gets a
one-line summary. Fails fast if errors are found.

### Multi-platform typecheck (T-3191)

`ty check --python-platform` defaults to the host running it (`ty check
--help`), so stage 3 above (`frob.check._python._run_ty`) used to
typecheck ONLY the platform `frob check` happened to run on -- a
Windows- or macOS-only diagnostic was structurally unreachable from any
other host, and CI (whichever runner drew that job) was the first place
it could ever surface. CI run 33135896391 measured this directly: 4
Windows-only Typecheck diagnostics (an `os.sysconf` call and a
`ctypes.windll` access, both POSIX/Windows-conditional in `frob.process.
_reap`/`_pid_liveness`) that no prior Linux-hosted `frob check` had ever
seen.

`_run_ty` now runs `ty check` once per platform in `frob.toml`'s `[ty]
target_platforms` (default `["linux", "win32", "darwin"]` --
`frob.check._python._DEFAULT_TY_TARGET_PLATFORMS`, this project's own
full CI OS matrix, `.github/workflows/ci.yml`) and reports the union as
one `tool="ty"` `ToolResult`, each diagnostic's message prefixed
`[platform=<name>]` so a platform-only finding is attributable at a
glance. Measured added cost: ~1.2s per extra platform on this repo (`ty`
is Rust-native) -- ~2.5s total for the two non-host platforms, run on
every `frob check`, not deferred to a land-time/CI-parity-only gate.

A platform-inverted finding -- a `ty: ignore` required on one target and
reported as an unused suppression (itself an error) on another, since a
single static suppression cannot satisfy opposite targets at once -- is
not special-cased by this runner. T-3191's own two sites resolved that
shape by removing the need for any suppression at all: an explicit
`if sys.platform == "win32":` guard around the platform-specific access,
which `ty` narrows per `--python-platform` target the same way
typeshed's own conditional stubs do (see "PID liveness (T-3018)" in
`docs/modules/process.md`).

### Skip flags

<!-- frob:describes src/frob/_cli_parsers/_check.py::_add_check_parser -->
```bash
frob check src/ --skip-ruff
frob check src/ --skip-ty
frob check src/ --skip-cycle
frob check src/ --skip-dup
frob check src/ --skip-arch
frob check src/ --skip-bind
frob check src/ --skip-exports
frob check src/ --skip-gates
```

**T-2320: `--skip-ruff` skips BOTH `ruff check` and `ruff format --check`.**
`--skip-ruff-check`/`--skip-ruff-format` split that bundle so a caller can
skip just one half (either the bundled `--skip-ruff` or the matching split
flag skips a given stage -- they combine with OR, never override each
other):

<!-- frob:describes src/frob/_cli_parsers/_check.py::_add_check_parser -->
```bash
frob check src/ --skip-ruff-check     # skip lint, still run format --check
frob check src/ --skip-ruff-format    # skip format --check, still run lint
```

### Tier-A/B/C deterministic autofix (`--fix`)

<!-- frob:describes src/frob/app/check_runner.py::_apply_tier_a_and_reverify -->
`--fix` applies every registered Tier-A deterministic auto-fix
(`frob.gates._fix_engine.apply_tier_a_fixes`) plus Tier-B's apply-verify-
commit-or-rollback fixes, re-runs the affected gates once in the same
invocation, then emits Tier-C fix-its -- never writes a `frob:waive`
directive, never touches `frob.toml` or ratchet state
(docs/design/check-fix-engine.md).

**T-3326: `--fix`'s blast radius depends on whether `--ticket` is also
given.**

<!-- frob:describes src/frob/app/check_runner.py::_apply_tier_a_and_reverify -->
```bash
frob check --ticket T-1234 --fix   # scoped: only T-1234's declared files
frob check --fix --fix-all         # deliberate repo-wide pass
frob check --fix                   # REFUSES -- neither given
```

- `--ticket <id> --fix` scopes every Tier-A/B fix to that ticket's own
  declared `scope` (reusing the same `filter_fixes_by_scope_and_lease`
  check `frob ticket land`'s own pre-land Tier-A pass has used since
  T-2284) -- a fix a handler would have made outside that scope is
  reverted on disk and reported skipped, never silently applied. This is
  also already true of `frob ticket land`'s own pre-land Tier-A pass; it
  is not a new hazard `--fix` introduces, only one the bare CLI command
  did not share until T-3326.
- A bare `--fix` with **neither** `--ticket` **nor** `--fix-all` now
  **refuses** (exit 1) instead of silently rewriting every file its
  handlers find repo-wide -- the fix for the incident that motivated
  T-3326: an unscoped `--fix`, run to re-baseline one file, rewrote
  roughly 15 unrelated files before a killed run was caught and reverted
  by hand.
- `--fix --fix-all` still runs the full repo-wide pass exactly as before
  T-3326 -- the repo-wide case is gated behind an explicit opt-in, not
  removed.

A killed `--fix` run (any scope) is recoverable, not silent: `apply_tier_a_
fixes` writes an autofix manifest under `.frob/` after every handler
completes, naming every path a completed handler actually rewrote, and
clears it only once the whole pass finishes (T-1348).

### Ruff autofix write mode

<!-- frob:describes src/frob/_cli_parsers/_check.py::_add_check_selection_args -->
`--fix-ruff` (T-2320) runs a genuine `ruff check --fix` + `ruff format`
WRITE pass (`frob.check._python._run_ruff_autofix`) and exits -- distinct
from `--fix`'s narrow Tier-A/B/C deterministic fixers (frob's own
registered, individually-reviewed fix tables, docs/design/check-fix-engine.md),
which never apply a general `ruff --fix` across every fixable rule
category. This is the primitive `format:`/`lint-fix:` Makefile leaves
repoint to (T-2244):

<!-- frob:describes src/frob/_cli_parsers/_check.py::_add_check_selection_args -->
```bash
frob check --fix-ruff    # rewrite files on disk via ruff's own autofix + formatter
```

### Gates integration flags

<!-- frob:describes src/frob/_cli_parsers/_check.py::_add_check_parser -->
```bash
frob check --ticket T-0042             # explicit ticket context for scope/pre-work gates
frob check --base main                 # base ref for the drift/coverage diff (default: main)
frob check --only gates                # run only the gates stage (repeatable; any stage name)
frob check --only ruff --only gates    # run ruff and gates only
frob check --stamp-coverage            # record coverage.xml as the current stamp, then exit
frob check --stamp-baseline            # record current gate violations as the delta baseline, then exit
frob check --only gates --delta        # gates stage reports only violations new since that baseline
frob check --only list                 # print every stage-group name, one per line
frob check --only lint                 # ruff + ty only (~1s on this repo)
frob check --only static               # cycle/dup/arch/bind/exports (~18s)
frob check --only gates-fast           # every thread-pool gate (~37s)
frob check --only gates-native         # archgate/clones/perf/exhaustive_handling (~15s)
frob check --only gates-security       # sys/pii_structural/secrets/dead_symbols/protocol_summary/opaque (~13s)
```

`--only` accepts any stage name (`ruff`, `ty`, `cycle`, `dup`, `arch`, `bind`,
`exports`, `gates`), any individual gate name (`frob.gates._ALL_GATES`,
e.g. `doclink`, `archgate`), or a stage-group alias; when omitted, every
non-skipped stage runs (gates included). `--stamp-coverage` is how `make
coverage` records `.frob/coverage-stamp` after `pytest --cov` runs; TEST006
compares the stamp against the live graph snapshot on later `frob check`
runs.

### Stage groups (`--only <group>`, T-0627)

A full `frob check` (or `--only gates`) on a repo of this size can exceed
the ~120s foreground cap a dispatched agent runs under, auto-backgrounding
the command and stalling the agent on a notification that never arrives.
`--only` accepts five stage-group aliases (`frob.check.available_stages()`,
`frob.check._STAGE_GROUPS`) as budget-sized presets over the same
tool/gate vocabulary, each measured comfortably under a ~90s per-stage
target on this repo:

| group            | members                                                    |
|------------------|-------------------------------------------------------------|
| `lint`           | `ruff`, `ty`                                                 |
| `static`         | `cycle`, `dup`, `arch`, `bind`, `exports`                     |
| `gates-fast`     | every thread-pool gate (drift, coverage, invariant, test, policy, doclink, docanchor, fuzz, release, decisions, tickets, refs, registry, compliance, docblocks, walk_lint, excludehazard, debt, deprecated, render_lint, parse_failures, lang_conformance, lang_project_conformance, scope, prework, fmt, affect_drift, ffi_boundary) |
| `gates-native`   | `archgate`, `clones`, `perf`, `exhaustive_handling` (process-pool CPU-bound gates)   |
| `gates-security` | `sys`, `pii_structural`, `secrets`, `dead_symbols`, `protocol_summary`, `opaque` (the remaining process-pool gates) |

`frob check --only list` discovers the current group names (print one per
line; `--json` wraps them as `{"stages": [...]}`) rather than hardcoding
them, since new groups may be added later. The sanctioned agent loop:

```bash
for s in $(uv run frob check --only list); do
  uv run frob check --only "$s"
done
```

A group name is pure sugar -- `--only lint` expands to exactly `--only
ruff --only ty` before dispatch, so every other flag (`--ticket`, `--json`,
`--delta`, `--base`) composes with a group unchanged, and mixing a group
with individual stage/gate names in one `--only` list is additive.

### `FROB_AGENT` full-check refusal (T-0627)

When the `FROB_AGENT` environment variable (T-0574) is set -- true for
every dispatched worktree agent -- a bare `frob check` with no `--only`
selection (and not `--stamp-coverage`/`--stamp-baseline`, which already
exit early) REFUSES immediately (exit 1) instead of running the full,
cap-exceeding pass and stalling:

```
$ FROB_AGENT=1 frob check
ERROR: frob check: refusing a full/unchunked run under FROB_AGENT (T-0627) --
a full pass on this repo exceeds the ~120s agent foreground cap and
auto-backgrounds, stalling a dispatched sub-agent forever waiting on a
notification that can never arrive. Run the chunked loop instead: ...
```

Any `--only` selection (a stage group or a hand-picked name) bypasses the
refusal -- it already is the chunked, budget-sized invocation the message
steers toward. `FROB_ALLOW_FULL_CHECK=1` opts a specific invocation back
into the full run, for the rare case a human/coordinator genuinely wants
it from a `FROB_AGENT`-flagged shell. `--stamp-baseline` is deliberately
NOT refused (a legitimate one-shot warm-up step, not a repeatable
verification loop) but still runs the full undelta'd gates pass and can
still exceed the cap -- see `docs/guides/agent-playbook.md` section 6.

## Run-scoped memoization

<!-- frob:describes src/frob/check/_memo.py::run_memo_scope -->
<!-- frob:describes src/frob/check/_memo.py::reset_run_memo -->
<!-- frob:describes src/frob/check/_memo.py::run_memo_stats -->
<!-- frob:describes src/frob/check/_memo.py::memoize_per_run -->

T-0423: the heavy PURE analyses (`frob.graph.build_graph`,
`frob.arch.analyze_project`, ...) generalize the T-0414 `frob.lang` parse
cache one level up -- `@memoize_per_run` on the function definition makes a
second call with identical arguments, while a `run_memo_scope()` is active,
a cache hit instead of a recompute, no matter which `frob check` stage
calls it or in what order. This is the general fix for the T-0418 class of
bug (the same expensive computation independently rerun by more than one
stage in one invocation).

```python
# frob/check/_memo.py
def run_memo_scope() -> ContextManager[None]
    # Activates memoize_per_run caching for the `with` block's duration;
    # frob.check._run_check_with_skips opens exactly one per `frob check`
    # invocation. Outside an active scope, decorated functions are a pure
    # passthrough -- no caching, no staleness risk.

def reset_run_memo() -> None
    # Convenience over run_memo_scope() for callers/tests that want an
    # unconditionally-active, unbounded scope rather than a `with` block.

def run_memo_stats() -> tuple[int, int]
    # (hits, misses) since the last reset_run_memo/run_memo_scope entry --
    # the anti-regression instrument, mirroring frob.lang.parse_cache_stats.

def memoize_per_run(func) -> Callable
    # Decorator: while a scope is active, repeat calls with identical
    # arguments reuse the first call's result. Applied to build_graph and
    # analyze_project at their definition site, so every caller (any
    # stage, any gate) benefits automatically without call-site edits.
```

T-1921: `analyze_project` grew a `files_examined` field on its return
value (`ArchResult`, docs/modules/arch.md#public-api) -- the per-site
analysis-coverage substrate's ARCH-family source of truth
(`frob.gates._arch.arch_examined_sites`). This memoization contract is
unaffected: the decorator still keys purely on call arguments, so a
second `analyze_project(root, ...)` call within the same run-memo scope
(e.g. `arch_gate`'s own call, then `arch_examined_sites`' second call
against the identical `root`/config) is a cache hit and returns the SAME
`ArchResult`, `files_examined` included -- not a second tree walk.

Correctness boundary: the memo is keyed on arguments only (no content
hash), so it must NEVER be active outside a real `frob check` run -- a
caller invoking `build_graph` directly (a CLI runner, or a test exercising
real incremental-rebuild behavior across an on-disk content change) sees
the function's ordinary, always-fresh behavior, because no scope is open
around that call.

### Delta baseline (agent workflow)

`frob check` prints every kept violation on every run -- useful for a human
sweep, expensive for an agent driving one ticket to green, which reruns
`frob check` several times per ticket and re-reads the same pile of
pre-existing (ticketed, not new) warnings each time for no new signal.

`--stamp-baseline` records the current gate violation set (rule + file +
message fingerprint, plus a per-file content hash for staleness detection)
to `.frob/baseline`. `--delta` then makes the gates stage report only
violations absent from that stamp:

<!-- frob:describes src/frob/_cli_parsers/_check.py::_add_check_parser -->
```bash
frob check --stamp-baseline            # once, e.g. at the start of a work session
frob check --only gates --delta        # afterwards: only new violations
```

If the baseline is missing, or any file it covers has changed since the
stamp, `--delta` degrades to the full (unfiltered) violation set with a
warning diagnostic explaining why -- a stale baseline silently hiding a
violation that moved back into the "new" set would be a worse failure mode
than no baseline at all. `--delta` is agent-facing and opt-in only: the
human-facing dial (every violation, always) is unchanged unless you pass it.

## Cycle severity

`frob cycle` uses size-based severity for detected import cycles:

| Cycle size | Severity |
|-----------|---------|
| 1-2 nodes | info |
| 3-5 nodes | warning |
| 6+ nodes | error |

Cycles are reported in multi-line format, one symbol per line:

```
=== CYCLE (warning) ===
frob.edit
  -> frob.ast.python
  -> frob.ast.common
  -> frob.edit
```

## C++ mode (auto-detected from `CMakeLists.txt`)

Runs in order:
1. CMake configure + build
2. `clang-tidy` on all sources
3. `clang-format --check` on all sources
4. `ctest` (optionally with `valgrind`)

<!-- frob:describes src/frob/check/__init__.py::run_check_cpp -->
```bash
frob check . --type cpp
frob check . --type cpp --valgrind
frob check . --type cpp --build-dir build/
frob check . --type cpp --skip-build --skip-clang-format
```

## Rust mode (auto-detected from `Cargo.toml`)

Runs in order:
1. `cargo check`
2. `cargo clippy`
3. `cargo fmt --check`
4. `cargo test` (optionally with `valgrind`)

<!-- frob:describes src/frob/check/__init__.py::run_check_rust -->
```bash
frob check . --type rust
frob check . --type rust --valgrind
frob check . --type rust --skip-clippy
```

## TypeScript mode (auto-detected from `package.json` + `tsconfig.json`)

Runs in order (each via `npx`):
1. `tsc --noEmit` -- type errors
2. `eslint . --format json` -- lint errors/warnings
3. `prettier --check .` -- format violations
4. `vitest run --reporter json` (optionally skipped) -- unit tests

A missing `npx`/node toolchain is a soft skip with a note on each stage,
never a crash.

<!-- frob:describes src/frob/check/__init__.py::run_check_ts -->
```bash
frob check . --type typescript
frob check . --type typescript --skip-eslint --skip-prettier
frob check . --type typescript --skip-tests
```

### TypeScript skip flags

<!-- frob:describes src/frob/_cli_parsers/_check.py::_add_check_parser -->
```bash
frob check src/ --skip-tsc
frob check src/ --skip-eslint
frob check src/ --skip-prettier
frob check src/ --skip-tests
```

## Auto-detection

| Sentinel file | Detected type |
|--------------|--------------|
| `Cargo.toml` | rust |
| `CMakeLists.txt` | cpp |
| `pyproject.toml` | python |
| `package.json` + `tsconfig.json` | typescript |
| (none) | python (fallback) |

## Output format

Text output groups by severity:

```
=== ERRORS (3) ===
src/frob/edit/__init__.py:42: error [ruff E501] line too long
...

=== WARNINGS (1) ===
src/frob/edit/__init__.py:10: warning [ty] possibly-unbound

=== TOOL SUMMARY ===
ruff check    2 errors
ty            1 warning
cycle         ok
dup           ok
arch          ok
```

JSON output (`--json`) includes the full structured `CheckResult` with per-tool
`ToolResult` entries containing `Diagnostic` objects.

### Tool summary: `pass` / `FAIL` / `UNRES` (T-2891)

The `## Tool summary` table's per-line icon is `pass` (green), `FAIL` (red),
or a third state, `UNRES` (yellow), reserved for one specific shape: a
`gate:<FAMILY>` line whose entire `ToolResult` is
[UNRESOLVED](../modules/gates.md#unresolved-t-1664) -- zero errors, zero warnings, and
every diagnostic UNRESOLVED (T-1664's `Severity.UNRESOLVED`). This is the
opt-in-schema-not-declared shape the `*SCHEMA`/`FLAGCOV` gate families
report when a project's `frob.toml` omits their `known_keys` declaration
(`_docblocks_shared.resolve_dotted_symbol`'s target): the gate genuinely
could not resolve anything, not "resolved and found nothing." Measured
off-repo (T-2891): 12 such gates against a real foreign project each read
`0 errors, 0 warnings, 1 unresolved, 0 waived` and rendered as `pass`,
indistinguishable from a project that had actually declared and passed
those schemas -- exactly the [[catalogued-is-not-enforced]] silent-zero
shape wearing the UNRESOLVED costume. `UNRES` is a *rendering-only* third
state: `exit_code`/`total_errors` and `frob check`'s exit-code contract
are unchanged by it (an UNRESOLVED-only gate still never fails the exit
code, per `#unresolved-t-1664` below) -- a gate mixing UNRESOLVED with any
real error/warning finding still renders its ordinary `pass`/`FAIL` icon,
since that shape genuinely did run a check over part of the repo.

## Use in CI

<!-- frob:describes src/frob/check/__init__.py::run_check -->
```bash
frob check src/ && echo "all clear"
# Exits 0 only if zero errors across all tools.
```
