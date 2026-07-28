<!-- frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug); file is docs/** in intent" -->

# Installing frob (T-0133)

frob ships as one pure-Python package (`frob`) plus two optional Rust/PyO3
native extensions built with maturin: `frob-core` (smart-dup's R3+ rungs --
tree-edit-distance and beyond) and `strata-core` (the real parser for
`.strata` design files, used by `frob.lang`, `frob.graph`, `frob check`,
`frob outline`, `frob xref`, and friends). Neither extension is a hard
dependency of `frob` -- every code path that needs one degrades to a typed
`Result.Err` (never a crash, never an exception) when it is missing. This is
the contract T-0133 hardens: a bare `uv tool install frob` must always work.

## Bare install (no natives)

```bash
uv tool install frob
```

Gets you: the full CLI, tickets, gates, doc-drift checking, xref, outline,
graph build, and Python/TypeScript/Rust/C/C++ parsing -- everything except
the two features above. `.strata` files are still *listed* by
`supported_extensions()` (the graph still sees they exist -- they are not
silently invisible to coverage or xref) but each one fails to parse with
`LangError.NativeParserUnavailable`, logged once at debug level per file,
not warning-spam. `frob-core`-only dup rungs (R3+) turn off; R1/R2 and every
other `frob.dup` rung are pure Python and still run.

`ruff` and `ty` (the tools `frob check`'s Python-language stage shells out
to) are real `[project]` dependencies (T-0142), so a bare install is fully
functional for Python repos out of the box -- no separate `pip install
ruff ty` step needed. Should any check-stage tool still be missing from
`PATH` (a non-Python stage's `cargo`/`clang-tidy`/`npx`, or a `ruff`/`ty`
shadowed by a broken shim), the corresponding stage reports a typed
failing `ToolResult` ("tool unavailable: `<name>` -- install it or use
`make install-tool`") instead of crashing -- a missing tool is always a
loud, visible failure in the `frob check` summary, never a silent skip.

## Full install (with natives)

Native extensions have no published wheels (no PyPI project -- they are
local maturin path packages under `frob-core/` and `strata-core/` in this
repo, not standalone publishable artifacts yet; see "why not a pip extra"
below). To get them into a `uv tool install`'d environment, build from
source and install them as `--with` deps of the same tool venv:

```bash
git clone https://github.com/lognd/frob
cd frob
make install-tool
```

`make install-tool` runs:

```bash
uv tool install --force --reinstall . --with ./strata-core --with ./frob-core
```

Requires a Rust toolchain (`cargo`) on `PATH` -- `uv` invokes maturin's
PEP 517 build backend for each local path dependency, which needs `cargo`
to compile the extension. If `cargo` is absent, this fails loudly (unlike
`make core`'s best-effort skip for the dev venv) since the whole point of
running this target is to get the natives.

## Editable dev install

```bash
pip install -e .        # or: make install
make core                # builds+installs frob-core and strata-core in-place
```

`make core` is best-effort: it skips (with a warning, not a failure) when
`cargo` is not on `PATH`, since most `frob.dup`/`frob.lang` functionality
does not need it.

## `uv sync` evicts the natives -- why every entrypoint self-heals (T-0340)

`strata_core`/`frob_core` are maturin-develop editable installs, not
`uv.lock`-tracked dependencies of this project (see "Why not `pip install
'frob[strata]'`?" below for why they cannot be declared that way). `uv
sync` reconciles the venv against ONLY the declared dependency set, so it
silently REMOVES both natives whenever it runs, even though `make core`
just installed them -- `uv lock`, `uv sync`, a `uv build` triggered by a
version-bump stamp, and some `uv run` invocations after a `pyproject.toml`
edit all trigger this. Before this ticket, only a remembered manual `make
core` restored them, and forgetting it surfaced as an oblique
`ModuleNotFoundError: strata_core`/`frob_core` or `NativeExtensionUnavailable`
mid test-collection or mid `frob check` -- looking like a real regression
(SYS004, phantom COV003 findings) rather than an environment artifact.

The fix lives in the `Makefile`, not in application code: `core` is a
`.PHONY` target (`core: $(STAMP)`), so listing it as a prerequisite of any
other target makes `make` re-run `core`'s `maturin develop` step every
single invocation of that target -- unconditionally, before the target's
own recipe body runs. Every target whose recipe actually needs the
natives at runtime (`check`, `all`, `test`, `test-fast`, `test-unit`,
`test-integration`, `test-system`, `install`, `coverage`, `coverage-fast`)
now depends on `core` instead of the bare `$(STAMP)` sync-stamp target, so
a prior `uv sync` eviction is always repaired first. This is cheap: a
`maturin develop` re-run is a true no-op rebuild (~0.5s once cargo's
target directory is warm; measured 14.6s only on a genuinely fresh
worktree with no prior cargo build cache at all) -- so the natives-always-
present invariant costs a fraction of a second per invocation in the
common case, not a repeated full compile. `frob doctor` (see below) still
exists as the fast standalone diagnostic when you want to check natives
without running a full target.

Formats/lint-only targets (`format`, `lint-fix`) that never import the
natives were deliberately left depending on the bare `$(STAMP)` sync stamp
-- they do not need the fix and there is no benefit to paying even the
~0.5s warm-cache cost there.

## Shared cargo target cache across worktrees (T-0732)

`core`'s `CARGO_TARGET_DIR` is pinned to `$(git rev-parse
--git-common-dir)/frob-cargo-target-cache` -- the ONE `.git` directory every
worktree of a clone shares, so every worktree of the same clone computes
the identical cache path with no per-clone hash or registration step, and
a different clone (a different `.git`) naturally gets a different cache
with no collision. The cache lives inside `.git` deliberately: it is
git-invisible build output that no working-tree `git status`/`git add -A`
in any worktree ever sees, unlike a cache path under a worktree's own tree
(which would pollute exactly that one worktree's status and need an
out-of-scope `.gitignore` entry). This is a different hazard class from
the `.git/info/exclude` warning in `docs/guides/agent-playbook.md` section
1c: that hazard is a shared EXCLUDE RULE silently shadowing tracked
source for every worktree forever; this is a shared CACHE DIRECTORY of
untracked build artifacts that only cargo itself ever reads or writes --
nothing tracked is affected, and deleting the directory is always safe
(cargo repopulates it from scratch, same as any target dir).

Concurrency: no frob-side locking was added. Cargo already serializes
concurrent builds against the same target directory via its own
fingerprint-directory file lock (observed directly: a second `make core`
started in a sibling worktree while the first was still compiling printed
`Blocking waiting for file lock on artifact directory` / `... on package
cache` and simply waited its turn -- both builds finished cleanly, neither
build's output was corrupted). This is documented cargo behavior, not a
new mechanism this ticket had to build or now has to maintain.

Measured (this repo, aarch64 dev host, both native crates via `make
core`, timed with `time`):

| scenario | wall time |
|---|---|
| fresh worktree, empty shared cache (from-scratch cargo build of every dependency crate plus both path crates) | 30.4s |
| fresh worktree, shared cache already warm from a sibling worktree (only `frob-core`/`strata-core` themselves recompile against their own worktree-local absolute path; every dependency crate is reused unchanged from the cache) | 11.4s |
| same worktree, second `make core` invocation with nothing changed (steady-state re-run, T-0340's existing no-op case) | 1.1s |

The from-scratch case drops from ~30s to ~11s for every worktree after the
first (a ~2.7x cut, matching the reduction in what actually has to
compile: only the two path crates themselves, not their dependency trees).
It does not reach the sub-10s target for a genuinely fresh worktree,
because `frob-core`/`strata-core` are built at each worktree's own
absolute path (e.g. `/path/to/worktree/frob-core`) -- cargo keys build
artifacts by absolute source path, so the two path crates themselves
cannot be shared across worktrees the way their dependency trees are; only
symlinking worktree source into one shared location would close that
remaining gap, and that is a much larger, riskier change (worktrees are
supposed to be independent checkouts) not attempted here. Reusing the
dependency tree is still the overwhelming majority of the original
cold-build cost and is captured by this change with no such risk.

Not built (disclosed, filed as a follow-up rather than attempted here):
part (2) of T-0732 -- a <!-- frob:waive DOC006 reason="proposal syntax for a not-yet-built pool-size flag, the next sentence discloses it was never implemented" -->`frob scaffold pool N` pre-warmed worktree pool
(pool of worktrees with natives already built and `main` already merged,
leased out to agents, refreshed in the background after lands). This
mechanism reduces make-core cost to near zero by never running it live at
lease time at all, which is a materially different and larger piece of
work (a leasing/refresh daemon, not a Makefile variable) than the shared-
cache mechanism above; see the ticket filed in T-0732's Done report
(`tickets.md`) for the tracked scope.

## Why not `pip install "frob[strata]"`?

`[project.optional-dependencies]` extras resolve through the same index
`pip`/`uv` would install `frob` from -- they need a real published
distribution (a wheel on PyPI, or at minimum a VCS/path URL baked into the
extra itself, which breaks the moment the extra is installed outside this
repo's checkout). `frob-core` and `strata-core` are not published anywhere;
declaring them as an extra with a local relative path (`frob-core @
file://./frob-core`) only resolves when installing from a checkout at that
exact relative location, which silently breaks for anyone who does
`pip install frob` from PyPI. `--with <path>` on `uv tool install` sidesteps
this because the path is supplied at install time by whoever is running the
command, from whatever checkout they have on disk -- it is a valid install
mechanism today, not a placeholder for something better.

Publishing `frob-core`/`strata-core` as real wheels to PyPI (one abi3 wheel
per supported platform via `maturin build --release`, then a normal
`[project.optional-dependencies]` extra pinned to the published version) is
the correct long-term fix and is explicitly out of scope for T-0133 -- filed
as follow-up work, not attempted here.

## CI contract

`.github/workflows/ci.yml` has a dedicated job that installs the bare wheel
(no natives) into a clean venv and runs `frob --help` plus `frob check`
against a tiny fixture repo, to catch any future import-time regression of
the standalone binary before it ships (the T-0077 hard-import bug T-0133
fixes was exactly this: `import strata_core` at module scope in
`frob.lang._walk_strata`, uncaught until someone ran the standalone tool
outside a dev checkout).

## Loud failure when `.strata` is used without natives (T-0316)

A repo that has never opted into `design/**` (no `.strata` files) is
completely unaffected by a missing `strata_core` -- `frob.gates.sys_gate`
never even imports `frob.strata` for such a repo (T-0135's opt-in check
runs first). But a repo that DOES have `.strata` files under its
`[strata].design_dir` and is missing the native extension must never look
like a clean pass. Two surfaces enforce this:

- `frob check`: `sys_gate` reports the load failure as its own `SYS004`
  ERROR-severity `Violation` naming the file and the exact
  `NativeExtensionUnavailable` message (`src/frob/gates/__init__.py`'s
  `_sys004`) -- this fails the `gates` tool and the overall `frob check`
  exit code, it does not silently degrade to a 0-violation pass.
- `frob sys audit` / `frob sys plan` / `frob sys doc`: `_load_audit_model`
  (and its `plan`/`doc` siblings in `src/frob/app/sys_runner.py`) log the
  same typed error per failing design file and `sys.exit(1)` -- they never
  print a report and exit 0 on a load failure.

Both paths are covered end-to-end (a real subprocess `python -m frob ...`
invocation, not just a monkeypatched unit test) by
`tests/system/test_cli_native_missing.py`, which shadows the real
`strata_core` extension via `PYTHONPATH` with
`tests/fixtures/fake_no_native/strata_core.py` (a module whose only body is
`raise ImportError(...)`) to reproduce exactly what a natives-less `uv tool
install frob` sees. It asserts: (1) a repo with `.strata` under `design/`
exits nonzero from both `frob check` and `frob sys audit` and names
`SYS004`/`NativeExtensionUnavailable` in the output; (2) a repo with no
`design/` dir at all exits 0 unaffected -- the T-0135 opt-in guarantee, not
just the loud-failure one.

## Detecting a stripped native install (the "reinstall wiped my wheel"
gotcha)

`uv tool install --force --reinstall . --with ./strata-core --with
./frob-core` (`make install-tool`) is a one-shot install: the `--with`
local-path deps are resolved and installed alongside `frob` into that tool
venv AT THAT MOMENT. A later plain `uv tool upgrade frob` or `uv tool
install --force --reinstall frob` (no `--with` flags) reinstalls only the
pure-Python `frob` distribution into the same venv and does NOT re-add the
`--with` extras -- it silently strips `strata_core`/`frob_core` back out,
regressing to the bare-install posture with no warning at install time.
This is the exact failure mode the T-0316 FROBLEMS report describes
("bit mid-campaign when a reinstall wiped the manually-added wheel").

Until `frob-core`/`strata-core` are published as real wheels (see "Why not
`pip install \"frob[strata]\"`?" above -- still out of scope, tracked as a
follow-up ticket), there is no install-time guard against this: `uv tool
upgrade`/`uv tool install --force --reinstall` on a bare `frob` spec is a
valid way to ask for exactly that (upgrade `frob`, natives excluded), so
frob cannot distinguish "the user wants natives gone" from "the user forgot
`--with`" at install time. The check that CAN and does catch it is the
loud-failure guarantee above: the next `frob check`/`frob sys audit` run
against a repo with `.strata` files fails immediately with a named
`SYS004`/`NativeExtensionUnavailable`, rather than silently going quiet --
treat that failure as the signal to re-run `make install-tool`, not a
regression to chase in application code.

## `frob doctor`: native-extension diagnosis (T-0319)

To check natives are present without waiting to hit the `SYS004`/dup gate
above, run:

<!-- frob:describes src/frob/__main__.py::_add_doctor_parser -->
```bash
frob doctor
```

This imports `frob_core` and `strata_core` and reports each one's
availability (and version, when the module exposes one). When either is
missing it prints the exact remediation -- `make core` (build in-place) or
`make install-tool` (reinstall the CLI with natives bundled) -- and exits
1, so it is scriptable as a preflight check (e.g. in CI or a postinstall
hook), not just a human-readable report. `frob doctor --json` emits the
same `DoctorReport` as machine-readable JSON. This supersedes the manual

```bash
python3 -c "import strata_core, frob_core" \
  && echo "natives present" || echo "natives MISSING -- run: make install-tool"
```

check as the first-class CLI surface for the same diagnosis (T-0317).

## Derived-state integrity manifest (T-0570)

<!-- frob:describes src/frob/doctor.py::verify_derived_state -->

`frob doctor` also fingerprints every derived artifact `frob` writes and
reports which ones are present but corrupt, BEFORE any gate consumes them.
Three real incidents motivated this: a stale fixture `dup.db` silently
flipping detector results (T-0517), `make coverage` clobbering the native
build mid-run and producing 44 phantom `frob check` errors, and a coverage
stamp lagging the source it claims to describe. Each used to surface only
as a pile of confusing downstream `frob check`/`frob dup` findings, with no
single line saying "the derived state itself is stale" -- `frob doctor` is
the first thing an agent runs, so this is the doctor-first choke point that
catches it before the confusing findings follow.

`DERIVED_ARTIFACTS` (`src/frob/doctor.py`) names every artifact checked:

| name | path | format |
|---|---|---|
| `graph-cache` | `.frob/cache.db` | sqlite |
| `dup-cache` | `.frob/dup.db` | sqlite |
| `vet-cache` | `.frob/vet.db` | sqlite |
| `coverage-stamp` | `.frob/coverage-stamp` | json |
| `baseline` | `.frob/baseline` | json |
| `coverage-lock` | `frob-coverage.lock.json` | json |

An artifact absent from disk (nothing written yet) reports healthy -- this
manifest only flags corruption, not staleness-by-absence. A `sqlite`-kind
artifact is validated by its file-format magic header; a `json`-kind
artifact by `json.loads`. Each present artifact also gets a sha256
`fingerprint` of its raw bytes in the report, for a caller that wants to
diff two runs' derived state directly rather than just the healthy/
unhealthy verdict.

T-0879: the fingerprint-read + manifest-write span inside `run_diagnosis`
(`verify_derived_state` through the manifest write) holds
`frob.process._lock.derived_state_lock(root, exclusive=True)` for its
whole duration -- `frob doctor` is a `.frob`-derived-state WRITER in the
same sense `frob mutate` is, and always runs standalone (never nested
inside an already-locked `frob check` run), so this cannot self-deadlock
against a `frob check` reader's SHARED lock in the same process. See
`docs/modules/process.md`'s "Derived-state lock (T-0859)" section for the
shared/exclusive contract this closes the writer side of.

`frob doctor --json`'s `derived_state` array carries one entry per
artifact (`name`, `path`, `present`, `healthy`, `fingerprint`, `detail`);
the text report's overall `healthy`/`remediation` fields fold in any
corrupt entry alongside the native-extension check above, naming the exact
`rm -f <path>` for each offender.

T-0570 originally scoped this to `src/frob/doctor.py` reporting only,
noting that wiring an actual BLOCK into `frob check`'s gates (so a
corrupt cache cannot even be consulted, not just flagged) was out of
scope. **That follow-up has since landed as T-0603**: `frob check`'s
`run_check`/`run_check_cpp`/`run_check_rust`/`run_check_ts` entry points
now each call `frob.check._derived_state_integrity_result` once,
synchronously, before dispatching any stage, and fail the whole check run
closed (a single `derived-state-integrity` ERROR result, code
`DERIVED001`) if any derived artifact is present-but-corrupt -- see
`docs/modules/gates.md#derived001-t-0603-derived-state-integrity-precheck`
for the enforcement side.

### Cross-run content drift (T-0604)

<!-- frob:describes src/frob/doctor.py::_detect_derived_state_drift -->

T-0570's fingerprint check above is per-run: it catches an artifact that
is malformed RIGHT NOW, but says nothing about an artifact that is still
validly formatted yet was silently REWRITTEN out-of-band since the last
`frob doctor` run (a stale tool or a foreign process touching a cache
between two invocations). T-0604 closes that gap: `run_diagnosis`
persists a `{artifact name: fingerprint}` manifest under
`.frob/derived-state-manifest.json` after every run, and compares this
run's fingerprints against the manifest the PREVIOUS run left behind
(`_detect_derived_state_drift`). Any artifact present in both, with a
fingerprint mismatch, is reported as a `DerivedArtifactDrift` entry
(`name`, `path`, `previous_fingerprint`, `current_fingerprint`) in the
new `DoctorReport.drift` list -- surfaced automatically via `frob doctor
--json` alongside `derived_state`, no CLI rendering changes needed. An
artifact missing from the prior manifest (first-ever run, or a newly
added `DERIVED_ARTIFACTS` entry) or absent this run (deleted since, e.g.
`frob clean`) never reports drift -- only a present-in-both,
fingerprint-mismatched pair does.

Drift is deliberately **informational only**: unlike T-0603's
corrupt-artifact block above, it does NOT feed into
`DoctorReport.healthy`/`remediation`. `frob`'s own tools legitimately
rewrite these same caches between two `frob doctor` invocations during
ordinary use -- running `frob check` updates `.frob/cache.db`, `frob dup`
updates `.frob/dup.db`, and so on -- so treating every such expected
rewrite as a hard failure would make a session's second `frob doctor`
call cry wolf on completely normal churn. Callers that want the raw
signal (an audit trail, "did anything touch my caches while I wasn't
looking") read `DoctorReport.drift` or call
`_detect_derived_state_drift` directly.

## `frob mutate` backup journal: needs-restore state (T-0857)

<!-- frob:describes src/frob/doctor.py::_mutate_journal_remediation -->

`frob doctor` also reports every stale `frob mutate` backup journal found
under `.frob/mutate-backup/` (`frob.mutate._journal.list_stale_journals`,
`DoctorReport.mutate_journals`). A journal is written before `frob mutate`
overwrites a target with a mutant and normally removed once the original
is restored; a journal still present means a PRIOR mutation run crashed
(a `SIGKILL`, an OOM kill, the T-0755 fork-bomb scenario) before it could
restore its target -- the real source file it names may currently be
sitting on disk in mutant form.

Unlike drift (previous section), this DOES fold into the overall
`healthy`/`remediation` verdict -- a stale journal names a live source-
file problem, not disposable cache churn:

```bash
frob doctor
# ... mutate-backup journal(s) needing restore: src/pkg/m.py -- re-run
# `frob mutate <target>` (its startup check restores automatically) or
# restore by hand from the journal file
```

`frob doctor --json`'s `mutate_journals` array carries one entry per
stale journal (`target`, `journal_path`). `frob doctor` itself never
restores anything -- it is a diagnostic, not a repair tool. The fix is
either re-running `frob mutate` against the same target (its own startup
check, `restore_stale_journals`, performs the actual restore before doing
anything else) or restoring by hand from the named journal file (JSON,
base64-encoded raw bytes plus a sha256 fingerprint). See
`docs/modules/mutate.md#crash-safe-backup-journal-t-0857` for the full
journal design.

**Known residual (PID reuse without `/proc`):** "stale" is PID-reuse-aware
on Linux -- a journal also records the writer's `/proc/<pid>/stat`
starttime, so a crashed writer whose PID number later gets recycled by an
unrelated process is still correctly detected as stale rather than
reporting "alive" forever (see
`docs/modules/mutate.md#pid-reuse-why-is-the-writer-alive-is-not-enough-t-0857-reviewer-fix`).
Wherever `/proc` cannot be read at all (non-Linux, a sandboxed
environment), staleness falls back to PID-only liveness and this
detection does not apply: **if `frob doctor` stays clean but a target
keeps refusing with `JournalCollision`, inspect
`.frob/mutate-backup/<hash>.json` by hand -- the recorded PID may have
been reused.**

## Scaffold managed-block conformance (T-0736)

<!-- frob:describes src/frob/scaffold/_managed.py::scaffold_conformance_status -->

`frob doctor` also reports whether the CURRENT repo is missing or behind
on frob's managed boilerplate blocks (`docs/commands/scaffold.md#managed-
blocks-t-0736`): the Makefile `core:` shim, standard `.gitignore`
entries, and the T-0431/T-0577 worktree-lease git hooks. This is opt-in
on `frob.toml` existing under the repo root -- a bare directory (a
`tmp_path` in a test, a repo that has never adopted frob at all) has
nothing to be behind ON, so it reports an empty `scaffold_blocks` list
and never drags the overall verdict down for it.

For a `frob.toml`-bearing repo, any block that is missing entirely, or
present but drifted from what `frob scaffold apply` would install right
now (a digest mismatch, the same "regenerate fresh, compare byte-
identical" check `DEPLOY001` uses for deploy scripts), folds into an
unhealthy verdict naming the single remedy:

```bash
frob scaffold apply
```

`frob doctor --json`'s `scaffold_blocks` array carries one entry per
managed block/hook (`block_id`, `target`, `kind` -- `"text"` or `"hook"`
-- `present`, `stale`, `expected_digest`, `actual_digest`). A hook file
that exists but is NOT recognizably frob's own (no frob install-comment
marker) is reported present and not-stale -- `frob doctor` never claims a
repo's genuine custom hook of the same name is drift.

Per-sibling rollout across the estate (bootstrapping every other repo the
same way this one was) is tracked via adoption tickets filed at land time
through the fleet route, not enumerated here.
