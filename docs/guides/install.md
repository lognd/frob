# Installing frob (T-0133, T-3845)

frob ships as one pure-Python package (`frob`) plus two Rust/PyO3 native
extensions built with maturin: `frob-core` (smart-dup's R3+ rungs --
tree-edit-distance and beyond) and `strata-core` (the real parser for
`.strata` design files, used by `frob.lang`, `frob.graph`, `frob check`,
`frob outline`, `frob xref`, and friends). As of T-3845, both are published
to PyPI (`.github/workflows/release.yml` builds each as an abi3-py311 wheel
across five platform targets and publishes them ahead of `frob` itself) and
are DEFAULT `[project]` dependencies of `frob`, hard-pinned to frob's own
version (`frob-core==<v>`, `strata-core==<v>` -- see the T-3845 comment on
`pyproject.toml`'s `dependencies` for why an exact pin is safe given the
release workflow's real publish-order/abort behavior). A plain install now
gets both:

```bash
uv tool install frob
```

Neither extension is a HARD RUNTIME requirement, though -- this is still the
T-0133 contract, unchanged by T-3845: every code path that needs one
degrades to a typed `Result.Err` (never a crash, never an exception) when it
is missing. A source install on a platform with no published wheel (or any
environment where the compiled extensions are stripped after install) still
installs and runs frob in pure-Python mode; see "Degrading without the
natives" below.

## Standard install (natives included)

```bash
uv tool install frob
```

Gets you the full CLI, tickets, gates, doc-drift checking, xref, outline,
graph build, Python/TypeScript/Rust/C/C++ parsing, the accelerated
`frob-core` dup rungs (R3+), and full `.strata` parsing via `strata-core` --
no separate step. `ruff` and `ty` (the tools `frob check`'s Python-language
stage shells out to) are also real `[project]` dependencies (T-0142), so a
bare install is fully functional for Python repos out of the box. Should any
check-stage tool still be missing from `PATH` (a non-Python stage's
`cargo`/`clang-tidy`/`npx`, or a `ruff`/`ty` shadowed by a broken shim), the
corresponding stage reports a typed failing `ToolResult` ("tool unavailable:
`<name>` -- install it") instead of crashing -- a missing tool is always a
loud, visible failure in the `frob check` summary, never a silent skip.

## Degrading without the natives

If your platform has no published wheel for `frob-core`/`strata-core` (pip
then falls back to each crate's sdist and needs a Rust toolchain to build
it, or the build fails outright), or your environment deliberately strips
the compiled extensions after install, frob keeps working: `.strata` files
are still *listed* by `supported_extensions()` (the graph still sees they
exist -- they are not silently invisible to coverage or xref) but each one
fails to parse with `LangError.NativeParserUnavailable`, logged once at
debug level per file, not warning-spam. `frob-core`-only dup rungs (R3+)
turn off; R1/R2 and every other `frob.dup` rung are pure Python and still
run. `frob doctor` reports the gap and its remediation (see below); a repo
that actually uses `.strata` files gets a loud, non-degrading failure
instead of a silent pass -- see "Loud failure when `.strata` is used without
natives" below, unchanged by T-3845.

## Editable dev install

Editable dev work in this repo (not an end-user install) builds the
extensions in place with `cargo` on `PATH`:

```bash
pip install -e .        # or: make install
make core                # builds+installs frob-core and strata-core in-place
```

`make core` is best-effort: it skips (with a warning, not a failure) when
`cargo` is not on `PATH`, since most `frob.dup`/`frob.lang` functionality
does not need it.

## `uv sync` and the natives, post-T-3845

Before T-3845, `strata_core`/`frob_core` were maturin-develop editable
installs, not `uv.lock`-tracked dependencies of this project, so `uv sync`
reconciled the venv against a declared dependency set that did not mention
them and silently REMOVED both natives whenever it ran -- `uv lock`, `uv
sync`, a `uv build` triggered by a version-bump stamp, and some `uv run`
invocations after a `pyproject.toml` edit all triggered this.

T-3845 makes `frob-core`/`strata-core` real default dependencies (see
`pyproject.toml`'s `[tool.uv.sources]`, which points this checkout's own
resolution at the local `frob-core/`/`strata-core/` path crates rather than
the published index versions). Verified 2026-09-05: a plain `uv sync` in
this worktree no longer evicts the natives -- they are now part of the
declared, lock-tracked dependency set, so `uv sync` installs/keeps them
like any other dependency instead of removing an out-of-band install.
The `Makefile`'s `core`-as-prerequisite self-heal machinery described below
is therefore likely no longer load-bearing for this specific eviction
failure mode; changing the `Makefile` is out of this ticket's scope, so it
is left as-is and a follow-up is filed to re-verify and simplify it
(T-3850). The history below is kept for context on why the machinery
exists at all.

Before this ticket, only a remembered manual `make
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

## History: why `frob-core`/`strata-core` were not a plain extra (resolved, T-3845)

Before T-3845, `frob-core`/`strata-core` had no published wheels, so they
could not be a normal `[project.optional-dependencies]` extra: an extra
resolves through the same index `pip`/`uv` install `frob` from, and a local
relative path (`frob-core @ file://./frob-core`) only resolves when
installing from a checkout at that exact relative location -- it silently
breaks for anyone who does `pip install frob` from PyPI. The install path
of that era was `uv tool install --force --reinstall . --with ./strata-core
--with ./frob-core` (`--with` supplies the path at install time, from
whatever checkout the installer has on disk).

`.github/workflows/release.yml` now builds and publishes both crates as
real abi3-py311 wheels ahead of `frob` itself, so as of T-3845 they are
plain default `[project]` dependencies, hard-pinned (`frob-core==<v>`,
`strata-core==<v>`) -- see the top of this document and the T-3845 comment
on `pyproject.toml`. The `native` extra also still exists, listing the same
two pins, purely so `pip install "frob[native]"` keeps resolving for any
script or doc that already names it, and so
`frob.gates._version_coupling`'s VERSION001 check (which reads that extra
for its exact-pin invariant) and `frob doctor`'s remediation message (which
names `frob[native]`) both keep working unchanged; it adds nothing a plain
install does not already provide.

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

## History: the "reinstall wiped my wheel" gotcha (resolved, T-3845)

Before T-3845, `uv tool install --force --reinstall . --with ./strata-core
--with ./frob-core` (`make install-tool`) was a one-shot install: the
`--with` local-path deps were resolved and installed alongside `frob` into
that tool venv AT THAT MOMENT. A later plain `uv tool upgrade frob` or `uv
tool install --force --reinstall frob` (no `--with` flags) reinstalled only
the pure-Python `frob` distribution into the same venv and did NOT re-add
the `--with` extras -- it silently stripped `strata_core`/`frob_core` back
out, regressing to the bare-install posture with no warning at install
time. This is the exact failure mode the T-0316 FROBLEMS report describes
("bit mid-campaign when a reinstall wiped the manually-added wheel").

T-3845 removes the underlying cause: `frob-core`/`strata-core` are now
plain default `[project]` dependencies (real published wheels, hard-pinned
to frob's version), so `uv tool upgrade frob` / `uv tool install --force
--reinstall frob` resolves and reinstalls them like any other dependency of
`frob` -- there is no longer a separate `--with` step to forget. The loud
non-degrading failure described above (`SYS004`/`NativeExtensionUnavailable`
on a repo that actually uses `.strata`) still exists as defense in depth for
a platform genuinely missing a wheel, but the specific "reinstall silently
dropped a manually-added extension" gotcha no longer applies to a standard
install.

## `frob doctor`: native-extension diagnosis (T-0319)

Also available as `frob ops doctor` (T-1569) -- same flags, same code.

To check natives are present without waiting to hit the `SYS004`/dup gate
above, run:

<!-- frob:describes src/frob/_cli_parsers/_misc.py::_add_doctor_parser -->
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

<!-- frob:describes src/frob/derived_state.py::verify_derived_state -->

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

T-2407: `verify_derived_state`, `DerivedArtifactStatus`, and
`DERIVED_ARTIFACTS` now live in `src/frob/derived_state.py`, not
`src/frob/doctor.py` -- moved out under `core` so that `frob.check`'s
own direct use of this fingerprint pass (below) is not an `X -> cli`
import (`frob.doctor` is this repo's `cli`-node home for the `frob
doctor` subcommand, and had no argparse surface of its own tying this
check to it). `frob.doctor` imports both back and keeps its own
drift-manifest tracking (`_detect_derived_state_drift` et al) locally,
unchanged.

`DERIVED_ARTIFACTS` (`src/frob/derived_state.py`) names every artifact
checked:

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

<!-- frob:waive DOC004 reason="illustrative frob doctor output example -- demonstrates the remediation verdict format with stand-in paths, not a bound, executable command sequence" -->
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

## Malformed ticket edge scan (T-1132)

<!-- frob:describes src/frob/doctor.py::scan_malformed_ticket_edges -->
<!-- frob:describes src/frob/doctor.py::MalformedTicketEdge -->

`frob doctor` also scans `tickets.md`/`tickets-archive.md` for an existing
malformed `blocked_by`/`parent` entry -- an empty string, or anything not
shaped like a real `T-####`/`T-draft-<hex>` ticket id
(`DoctorReport.malformed_ticket_edges`). This is the READ-side complement
to write-time validation (`TicketSpec`'s field validators for `frob ticket
new`, and `frob ticket block`'s own `--by` check): T-0380 is the incident
motivating both halves -- an empty-string `blocked_by` entry sat alongside
three real (done) blockers, and `doable()`'s open-blocker check treated the
empty entry as an unresolvable id, so the ticket sat silently undoable for
days with nothing surfacing WHY.

Like a stale mutate-backup journal (previous section), a finding here DOES
fold into the overall `healthy`/`remediation` verdict:

<!-- frob:waive DOC004 reason="illustrative frob doctor output example -- demonstrates the malformed-edge remediation format with a historical specimen, not a bound, executable command sequence" -->
```bash
frob doctor
# ... malformed ticket edge(s) found: T-0380.blocked_by='' -- fix by hand
# in tickets.md/tickets-archive.md (empty-string or non-T-#### blocked_by/
# parent entries are refused going forward at write time, but an existing
# one is not auto-repaired)
```

`frob doctor` never repairs a malformed edge itself -- it only reports;
fixing an already-malformed ledger row is a manual `tickets.md`/
`tickets-archive.md` edit (there is exactly one such row this scan would
ever ideally find, since new writes are refused going forward). The scan
deliberately reads RAW frontmatter dicts (`frob.tickets._store.
iter_raw_ledger_frontmatter`), never the strict `Ticket` loader `load_all`
uses -- `Ticket.model_validate` does NOT reject a malformed edge (see that
model's own docstring in `docs/modules/tickets-data-storage.md#data-models`), specifically
so this scan can find one WITHOUT every OTHER `frob` command built on
`load_all` being at risk of a single bad edge hard-failing the entire
shared (1000+-ticket) ledger's load.

## Stale ticket lease scan (T-1131)

<!-- frob:describes src/frob/doctor.py::scan_stale_ticket_leases -->

`frob doctor` also reports any ticket stuck `IN_PROGRESS` with no live
cross-worktree lease (`DoctorReport.stale_ticket_leases`, a tuple of ticket
ids) -- the T-1050 incident: an agent `frob ticket fail`-logged a
superseded ticket, removed its worktree, and the ticket sat `IN_PROGRESS`
pointing at a now-nonexistent path until a coordinator noticed and
hand-dropped it. `frob ticket fail` itself now requeues automatically
(T-1131, see `docs/modules/tickets.md#public-api`'s `record_failure`/
`_fail` note) -- this scan is the safety net for every OTHER way a ticket
can end up stuck this way (a lease-stamp ledger sync, a crashed agent that
never ran `fail` at all, `docs/modules/tickets-lifecycle.md#frob-ticket-reconcile-t-0476`'s
own "stale hold" anomaly class).

Reuses `frob.tickets._reconcile.reconcile(root, apply=False)` -- the SAME
dry-run detection `frob ticket reconcile`/`frob ticket requeue <id>`
perform -- rather than reimplementing lease-staleness logic a second time.
Like a stale mutate-backup journal, a finding here DOES fold into the
overall `healthy`/`remediation` verdict:

<!-- frob:describes src/frob/doctor.py::scan_stale_ticket_leases -->
```bash
frob doctor
# ... ticket(s) stuck in-progress with no live lease: T-1050 -- run
# `frob ticket requeue <id>` for each (or `frob ticket reconcile --apply`
# to requeue all of them at once)
```

`frob doctor` never requeues anything itself -- it only reports; the fix
is `frob ticket requeue <id>` (one ticket) or `frob ticket reconcile
--apply` (every stale hold at once, see
`docs/modules/tickets-lifecycle.md#frob-ticket-reconcile-t-0476` for the full reconcile design).

## Scaffold managed-block conformance (T-0736)

<!-- frob:describes src/frob/scaffold/_managed.py::scaffold_conformance_status -->

`frob doctor` also reports whether the CURRENT repo is missing or behind
on frob's managed boilerplate blocks
(`docs/commands/scaffold.md#managed-blocks-t-0736`): the Makefile `core:` shim, standard `.gitignore`
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

<!-- frob:describes src/frob/scaffold/_managed.py::scaffold_conformance_status -->
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

## Venv shim shebang scan (T-1161)

<!-- frob:describes src/frob/doctor.py::scan_venv_shims -->

`frob doctor` also scans `.venv/bin/` for entrypoint scripts (`pytest`,
`frob`, etc.) whose `#!` shebang line points at a python interpreter
OUTSIDE this checkout's own venv (`DoctorReport.venv_shims`, a list of
`VenvShimDrift`). This is the 2026-07-28 incident: a `uv` operation run
from the wrong cwd (a sibling worktree) rewrote the ROOT venv's `pytest`
shim shebang in place to point at that OTHER worktree's own
`.venv/bin/python`; nothing failed at the time, but once that worktree was
later removed, every `uv run pytest` in the root checkout broke with a
dangling interpreter path -- and `collect_python_tests` (see
`docs/modules/testing.md#public-api`) had no way to say WHY, only that
collection failed, which cascaded into a flood of misattributed
COV003s (see the next section) instead of naming the one real cause.

The scan compares each shim's recorded shebang path (resolved) against
this checkout's own resolved `.venv/bin` directory -- catching a shim
pointed at a STILL-EXISTING but wrong venv too, not only one whose target
has since vanished. A finding folds into the overall `healthy`/
`remediation` verdict, same class as a stale mutate-backup journal or
malformed ticket edge:

<!-- frob:describes src/frob/doctor.py::scan_venv_shims -->
```bash
frob doctor
# ... venv shim(s) shebang outside this venv: pytest (-> /other/worktree/
# .venv/bin/python) -- run `uv sync --reinstall-package pytest` (repeat
# per affected package name if the script name does not match its
# distribution) or `make install-tool` to rebuild the whole venv
```

`frob doctor --json`'s `venv_shims` array carries one entry per drifted
shim (`script`, `shebang_path`, `expected_venv_bin`). A tree with no
`.venv/bin/` at all (not yet set up) contributes zero findings, not an
error -- an ordinary not-yet-set-up state, not drift.

## Live land-process report (T-1515)

<!-- frob:describes src/frob/doctor.py::scan_live_land_processes -->
<!-- frob:describes src/frob/doctor.py::LiveLandProcess -->
<!-- frob:describes src/frob/tickets/_land.py::LandLockTimeout -->

The 2026-08-04 incident (T-1495): an orphaned background `frob ticket
land` driver from a dead conversation was still serially landing a
roster while a NEW coordinator session also wrote to the same `root` --
the advisory `flock`-based `land.lock` correctly serialized the two
writers against each other, but neither session's `land()` call could
tell that the OTHER holder was a foreign, possibly-defunct driver rather
than its own prior invocation still finishing up, so a fresh call just
queued silently forever behind it.

Two changes close this: `land.lock`'s content now records the holding
process's pid, a session id, and an ISO-8601 UTC start timestamp
(written on every successful acquisition); and acquisition itself is no
longer an unbounded blocking `flock` -- a fresh `land()` call polls a
non-blocking attempt, logs (once) who it is waiting on the first time it
has to wait at all, and refuses (`Err(LandError.LandLockTimeout)`)
rather than queuing forever if the lock is still held after a bounded
timeout (10 minutes by default).

`frob doctor` reports the SAME lock-file content as a first-class
`DoctorReport.live_land_process` field (a `LiveLandProcess`, or `None`
if no lock file exists), with a POSIX liveness probe (`os.kill(pid, 0)`)
against the recorded pid:

<!-- frob:describes src/frob/doctor.py::scan_live_land_processes -->
```bash
frob doctor
# ... land.lock is held by pid 12345 (session pid-12345, started
# 2026-08-04T12:00:00+00:00) -- a `frob ticket land` is (or may be)
# mid-run against this repo right now
```

A LIVE holder is informational only -- a genuinely in-flight `land()`
call is normal, not unhealthy, so it does not affect `DoctorReport.
healthy`/`remediation`. This is exactly the "one command instead of a
human having to `ps`/`lsof` the lock file" T-1515 asked for -- run `frob
doctor` at the start of a session before dispatching a land-touching
wave, the same way natives/derived-state health is already checked
first.

### Orphaned (dead-holder) land.lock is self-healing (T-1634)

The liveness probe (`frob.tickets._land._probe_land_lock_pid_liveness`)
is three-state, mirroring the confirmed_absent/ambiguous split
`frob.tickets._leases._probe_worktree_liveness` already draws for
cross-worktree leases (T-0782/T-0584): `True` (alive), `False`
(CONFIRMED dead -- `os.kill(pid, 0)` raised `ProcessLookupError`), or
`None` (AMBIGUOUS -- e.g. a `PermissionError` probing a pid this process
does not own). Only `None` still makes `DoctorReport.healthy` `False`
now -- the same "cannot confirm either way" caution `_probe_worktree_
liveness` already applies, never a license to treat an unconfirmed
holder as safely gone.

A CONFIRMED-dead holder (`alive is False`, the T-1495 orphaned-lock
shape) no longer blocks `healthy` at all: the OS already released the
underlying `flock` the instant that process exited (SIGKILL included),
so nothing is actually blocked by the leftover file -- only its STALE
CONTENT lingered, requiring a human to notice `frob doctor`'s
remediation hint and delete `.frob/land.lock` by hand before this fix.
As of T-1634, the very next real `_land_lock` acquisition (the next
`frob ticket land` against the same `root`) reads the prior holder's
content before overwriting it, confirms the pid is dead via the same
probe, and logs a loud WARNING disclosing the reclaimed identity --
self-healing, not merely diagnosing. `frob doctor`'s own plain-text
output still surfaces the finding (even though it no longer flips
`healthy`), naming it explicitly as self-healing so it is never silently
dropped from the report.

## Honest pytest-collection failure in the coverage gate (T-1161)

<!-- frob:describes src/frob/testing/_collect.py::python_collection_failure_detail -->

The other half of the 2026-07-28 incident: when `collect_python_tests`
itself fails outright (a broken venv shim above, a missing dependency, any
reason `uv run pytest --collect-only` exits nonzero), the COVERAGE gate
used to have no way to tell "the collector is broken" apart from "every
one of these thousands of archived evidence ids independently stopped
resolving" -- it degraded to an empty node-id set and let `COV003`
(`docs/modules/gates.md#public-api`) fire once per unresolved evidence id,
6219 times in the incident that motivated this fix.

`collect_python_tests` now additionally records a human-readable failure
detail (spawned argv, exit code, stderr tail) via a module-level
`python_collection_failure_detail()` read (its `Result[CollectedTests,
TestingError]` return contract is unchanged -- every existing caller's
`.is_err` handling keeps working exactly as before). `run_gates` threads
that detail into `coverage_gate`, which reports ONE `COV003` naming the
real collection failure (with the stderr tail) instead of iterating every
archived ticket's evidence ids and reporting each as independently
unresolved.

## External tool inventory and preflight (T-3276)

<!-- frob:describes src/frob/doctor.py::ToolCategory -->
<!-- frob:describes src/frob/doctor.py::ExternalToolStatus -->
<!-- frob:describes src/frob/doctor.py::scan_external_tools -->

Measured 2026-08-28: `shutil.which` appeared in only 10 files across
`src/frob/`, `frob doctor` checked exactly one binary (`frob` itself, for
`GlobalBinarySkew`), and at least three spawn conventions coexisted for
the same tool (`sys.executable -m pytest`, `uv run pytest`, a bare
`pytest`/`python` PATH lookup). A confirmed consumer incident (diax
FROBLEMS.md F-011): `frob coverage --full` spawned a global pytest with
neither `pytest-cov` nor `pytest-xdist` installed, exited 4 (usage
error), and frob marked the run DEGRADED and continued -- so `TEST006`
could never be satisfied through `frob coverage` at all, and the user
bypassed frob entirely.

`frob doctor` now enumerates and reports every external tool it can spawn
or depends on for a gate to measure something, each tagged with one of
three categories (`ToolCategory`):

- **REQUIRED** -- frob cannot perform the operation at all without it
  (`python`, `git`, `uv`, `ruff`, `ty`). Absence makes `frob doctor`
  report `healthy=False` with a remediation line naming the tool and its
  install command.
- **OPTIONAL** -- frob never uses it unless the repo opts in, e.g. a
  per-language toolchain for a language this repo does not contain
  (`cargo`, `npm`, `ctest`). Absence is silent -- it never affects
  `healthy` or produces a remediation line.
- **OPTIONAL_FOR_GATE** -- a `frob check` gate needs it to MEASURE
  something (`pytest`, `pytest-xdist`, `pytest-cov`). Absence must make
  the affected gate report UNMEASURED, loudly, distinguishable from
  CLEAN -- never a silent skip and never `frob doctor`-unhealthy on its
  own (that per-gate wiring is tracked separately: see T-3311/T-3316 in
  `tickets/archive/` for the call-site work this ticket's own scope,
  `src/frob/doctor.py`, did not reach).

`scan_external_tools()` probes each `_EXTERNAL_TOOLS` entry: a binary via
`shutil.which` plus a best-effort `--version` spawn, a Python plugin
(`pytest-xdist`, `pytest-cov` -- loaded in-process by pytest, never
spawned as their own binary) via `importlib.metadata.version`. Every
probe is fail-soft (never raises); `ExternalToolStatus.present=False`
plus its `install_hint` is the reported outcome for a missing tool,
matching the MUST-FIRE fixture this ticket's own acceptance criteria
named: a missing REQUIRED tool's message names the tool and the install
command. A fully-present environment produces no new output and no
measurable slowdown beyond the cheap presence probes themselves (the
MUST-STAY-QUIET fixture).
