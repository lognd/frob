# Build, test, docs generation, CI

Status: DRAFT (T-0001, a v1-format id that migrates with an alias). Inputs: notes/rust-ecosystem.md sections 1 and
5, notes/v1/ops-and-integrations.md section 8 (v1 CI: 7 green of the
last 100 runs, green median 123 minutes).

## Milestone 1

Milestone 1 (D36) is: `frob check` and `frob land` run green on this
repository, with tickets in the v2 ledger, using the Rust, markdown and
TOML adapters only. There is no grimble, crunk, GUI, daemon, job store,
salsa, IR, PM forecasting or Jira-parity feature in it. Self-hosting
means frob alone: the self check does not merge sibling findings, and
the CI jobs below that mention grimble, crunk, bundling, macOS and
Windows packaging, benches and release are Milestone 2 or later (D36)
unless they say otherwise. The crate cut, with the verbs and rules each
crate brings, is the table at the end of notes/audit-design.md.

Status: the crates under `crates/` are `frob` (the binary, package
`frob-cli`), `frob-ack`, `frob-evidence`, `frob-lease`, `frob-ledger`,
`frob-obligations`, `frob-tests`, `frob-worktree`, `gob-cache`,
`gob-cli`, `gob-config`, `gob-dev`, `gob-diagnostics`, `gob-directives`,
`gob-exec`, `gob-git`, `gob-languages`, `gob-lock`, `gob-log`,
`gob-macros`, `gob-mdtest`, `gob-rules`, `gob-symbols`, `gob-text` and
`gob-walk`, plus `frob-check` and `frob-land`, which have landed (the
exact set is `ls crates/`). The self-host switch remains: `frob check`
and `frob land` run green on this repository only once it is made, and
until then the v1 `frob:waive DOC006` comments in the design files and
the `frob:waive DOC004` lines that gob-dev emits into generated rule
pages still fail DSL001; the switch converts both to `frob:accept ...
because="..."` (gob-dev emits the new form).

Milestone 1 carried no digest or lock decisions beyond scheme 1 (code-model.md
section 2); this repository's `frob.lock` is empty today.

## Milestone 2

The single authoritative statement of milestone-2 order (D36 deferrals
included); monorepo.md section 5, universal-model.md section 8,
grimble-model.md 9.7, cicd.md section 6 and migration.md point here.

1. The gob-diagnostics Unresolved gate fix (cli.md section 2): the
   landed `exit.rs` skips Unresolved findings; it gains the
   `[check] fail_on_unresolved` test, the `required` mark on the finding
   record and the three required cases. A ticket changes it before any
   sibling can be configured.
2. gob-ir: U terms, scope graph with status, canonical facet stream,
   queries, Kleene evaluator and answer lattice, the atom registry and
   callee vocabularies; the Rust and markdown adapters re-expressed over
   U in gob-symbols (universal-model.md section 8; gaps G1-G4 and
   G10-G19).
3. The digest scheme and typed lock (G05): canonical facet streams,
   facets Sig, Body, Doc, Attr and Contract, `digest_scheme` in
   gob-lock, typed `symbol | flow` entries, the ack planner moved to
   gob-lock. Open question 5 of universal-model.md (G9) is closed first.
   Consumer `frob.lock` import (migration.md) waits for this item; this
   repository's own `frob.lock` is regenerated at this point.
4. gob-check extraction (G06): the product-neutral pipeline, exception
   application moved to gob-rules, rule `polarity` and
   `subjects_examined`.
5. The grimble cut G01-G19 (notes/review/grimble-review.md section 5,
   critical path T-IR, G01, G02, G07, G08, G09, G11, G14): G01 .grmb
   specification, G02 binding semantics over U, G03 sibling JSON
   contract, G04 packs and drift-lock, G05 and G06 above, G07 selectors,
   G08 grimble-model parser and U adapter, G09 binary skeleton, G10
   grimble-arch (CYCLE, LARGE, DEAD), G11 and G12 grimble-bind, G13 frob
   orchestration of the sibling stage, G14 grimble-capabilities with the
   cell set of grimble-model.md 9.6, G15 shrink, G16 kernel port, G17
   gob-pattern and GPOL (blocked by the ast-grep `Doc`-over-U spike,
   rules.md section 3), G18 `grimble migrate`, G19 grimble-serve.
6. The first ten NEAT rules (neatness.md section 4), then
   `[neat] require_effects` for this repository's public surface.
7. The GitHub Actions and Dockerfile adapters and the CI and DK rules in
   grimble-ci (cicd.md); the zizmor and actionlint `[[check.tool]]`
   stages with parsers and id maps in frob-check land earlier and are
   adopted by this repository first.
8. PM enforcement (PM026 included) and the remaining D36 deferrals
   (grimble-vet, packs, SARIF, salsa, GUI, daemon, jobs, crunk).

## 1. Build locality

- Proc-macro crate (`gob-macros`) tiny and stable; grammar C builds
  isolated in `gob-languages` with per-grammar features; tokio only in
  the serve and gh crates (boundaries.md section 6).
- Dev profile: `opt-level = 2` for `gob-ir` only (section 5, "Suite time"), `debug = "line-tables-only"`,
  `split-debuginfo = "unpacked"`, incremental on; lld (default since
  1.90) or mold via `.cargo/config.toml`; `sccache` for grammar C.
- Release profile: lto = "fat", codegen-units = 1, panic = "abort",
  strip symbols; profile `release-fast` without lto for local benches.
- `cargo hakari` workspace-hack if feature unification causes rebuilds.
- Target: touch one rule file, `cargo nextest run -p grimble-arch` in
  under 5 s warm; full workspace debug build under 2 min cold on the dev
  box.

## 2. Tests

| Kind | Tool | Where |
|---|---|---|
| unit | plain `#[test]`, rstest for parametrization | each crate |
| markdown corpora | `gob-mdtest`: a fenced in-memory repo, then expected findings or expected symbols/edges; the `mdtest!` macro generates one nextest case per corpus directory (reporting every file in it); a fenced block without `expect=` is documentation, not a test | `crates/*/tests/md/*.md` |
| snapshots | insta for rendered output, `--json` payloads, generated docs | each crate |
| proc macros | trybuild compile-pass and compile-fail cases | `gob-macros/tests` |
| CLI end to end | assert_cmd + assert_fs against a fixture repo; snapbox transcripts for `--help` | `crates/{frob,grimble,crunk}/tests` |
| property | proptest for ids, merge driver, lease overlap | ledger, lease |
| language conformance | per-adapter fixture dir with expected symbols, digests, U terms, imports; the capability matrix test | `gob-languages`, `gob-symbols`, `gob-ir` |
| rule docs executable | every rule's doc example runs as an mdtest (ty lint_docs pattern) | generated |
| self-hosting | `frob check` on this repo in CI, zero errors (milestone 1: frob only; sibling merging is Milestone 2 or later (D36)) | workflow |

Markdown corpus format:

```
# COV001 fires for an undocumented public function

## repo
`src/a.py`:
    def f(): ...

## expect
COV001 src/a.py::f
```

Runner: `cargo nextest run` everywhere (per-test process isolation,
retries off, junit output); `cargo test --doc` separately.

## 3. Generated artifacts (`cargo dev gen`, checked with `cargo dev gen --check`)

gob-dev's `cargo dev gen` writes every generated page, schema, type
file and completion for all three products in one run. The authoritative
list of outputs, their paths and the command that writes each is the
path table in documentation.md section 3; this file does not repeat it.
Nothing generated is hand-edited. `cargo dev gen --check` runs in CI and
also as a repo-local `[[check.tool]]` stage in this repo's `frob.toml`
(its output maps to GEN001), so drift is a failure locally, not only in
CI. `cargo dev` exists only in this workspace, so GEN001 is not a rule
that consumer repos inherit.

## 4. CI

Jobs, all on PR and main:

| Job | Content | Target |
|---|---|---|
| fmt + clippy | `cargo fmt --check`, `cargo clippy --all-targets -D warnings` with `missing_docs`, `missing_errors_doc`, `missing_panics_doc`, `missing_safety_doc` as errors from the first commit (decided 2026-10-02, no warn-then-ratchet) | 2 min |
| test linux | nextest, all features | 5 min |
| test macos, windows | nextest, default features | 6 min |
| generate check | `cargo dev gen --check` | 1 min |
| self check | `frob check` on this repo (milestone 1: frob only; merging grimble and crunk findings is Milestone 2 or later (D36)), `frob test --base origin/main` | 2 min |
| spawn budget | snapshot test of subprocess counts per CLI scenario (git-io.md section 7) | in test linux |
| bench (scheduled) | criterion cold and warm check on the 100k-line fixture, regression threshold (architecture.md section 9) | 10 min |
| deny | cargo-deny advisories, licenses, bans; cargo-shear | 1 min |
| workflow lint | zizmor and actionlint through frob's `[[check.tool]]` stage (cicd.md section 6; adopted before the CI adapters exist) | 1 min |
| release (tag) | cargo-dist per binary on `frob-v*`, `grimble-v*`, `crunk-v*`; linux x86_64/aarch64, macos arm64, windows; crates.io publish of the full crate set in lockstep versions (monorepo.md section 4); `uv tool`-installable PyPI shims (the `frob` wheel bundles all three); Milestone 2 or later (D36) | 10 min |

Every third-party action is pinned by SHA, and every job has
`permissions` and `timeout-minutes` (pinned by the workflow tests in
frob-release). The budget for a green PR run is 15 minutes wall, against
v1's 123.

**One source of the checks: `cargo dev ci` (~AHBKXAZ).** The first push
of experimental (2026-10-03) failed in CI four times on things no local
gate ran: the host git identity, an actionlint pin, Windows-only code,
rustdoc. The checks now live in one place, `crates/gob-dev/src/ci.rs`:
each step's argv, environment and platform (fmt, clippy for the host,
clippy for `x86_64-pc-windows-gnu`, docs with `RUSTDOCFLAGS=-D
warnings`, nextest `--profile ci`, gen check, zizmor and actionlint at
the versions `frob.toml` pins, ticket doctor, frob check, test
dry-run). `ci.yml` runs `cargo dev ci --step NAME` per step and carries
no argv, environment or tool version of its own; a parity test fails
when the two disagree. Locally `cargo dev ci` stops at the first
failing step (`--keep-going` runs all) and is the gate every
implementer runs before reporting. The windows-latest job stays the
real-platform check; `goway run --host win` adds it before push
(paths.md section 4).

**`cargo dev` builds once (~J9BCSXD, ~3YYNHAC).** The `dev` alias runs
`gob-dev` from the shared `target/` (`run -p gob-dev --`); a separate
target dir (the earlier xtask-style fix) compiled nearly the whole
workspace a second time, 2.7 GB per checkout. On Windows a running
`target\debug\gob-dev.exe` cannot be replaced while `cargo dev ci`
rebuilds the workspace, and a self-copy re-exec cannot fix that under
`cargo run` (the original must stay alive to relay the exit code, so it
stays locked). Windows therefore uses the second alias `dev-isolated`
(`run -p gob-dev --target-dir target/dev-tool --`), which builds the tool
into its own target dir at the cost of one extra build. The windows-latest
job calls `cargo dev-isolated ci --step <name>`; the Linux job keeps
`cargo dev ci --step <name>`. On Windows, gob-dev run from the shared
target dir for a rebuilding task (`ci` without `--list`, `publish`) fails
fast naming `cargo dev-isolated` (`isolation::check`). A parity test pins
both aliases and requires the same step names and order per OS.

**Offloading heavy steps to a goway host (~ZWEYXGZ).** Opt-in:
`CARGO_DEV_CI_REMOTE=<goway binary>` (a bare name or a path; a
`--remote` flag will set the same once it can be registered in
`main.rs`). Each step marked `offload` in `ci.rs` (clippy, clippy for
the Windows target, docs, nextest, doctor, check) runs as
`goway run --with-git --needs cores>=8 --needs mem>=2G --needs os=linux
--report target/goway-ci-report.json [-e K=V]... -- <program> <args>`: the
step's own program, args and env, so `steps()` stays the single source and
the parity test still holds. `--with-git` ships a minimal `.git` (no
remotes, credentials or hooks), so `doctor`, `check` and the git-dependent
tests run remotely too. Cheap or host-bound steps (fmt, gen, zizmor,
actionlint, `test --dry-run`, which needs the `origin/` ref) stay local.
Tests that run pytest (frob-evidence and frob-tests) need `python3` and
`pytest` on `PATH` and skip with a named reason when they are absent
(`gob_testsupport::python_test_prerequisites`); setting
`FROB_REQUIRE_PYTHON_TESTS` turns the skip into a failure, so a host that
installs both can never pass silently without them.
Declared prerequisites are probed on the host (`rustup target list
--installed`, `which`), and the step is then pinned to that host
(`--host`). Missing items are reported as `HOSTREQ`, naming the host, each
item and its install command: a host setup problem, not a code failure. goway exit 125 means goway failed or no host qualifies: it is
retried five times with backoff (15 s doubling to 120 s) and then
reported as `GOWAY` in the summary, distinct from a `FAILED` step; any
other exit is the step's own. The summary names host, os and arch per
remote step. Nextest's junit timing report stays on the host, so the
local soft-budget report is skipped for a remote run. `RemoteOs` holds
every OS-specific term (needs term, probe commands); a Windows host
(`--remote-os windows`) is one more variant there, deliberately not built.
CI never sets the variable.

## 5. Developer loop

```
cargo dev gen                   # after adding a rule / command / config key
cargo nextest run -p <crate>    # focused
frob check --ticket <id>        # the gate, scoped
frob test --base main           # touched tests via frob's own selection
cargo dev ci                    # exactly what CI runs on Linux, before reporting
```

### Suite time (~B6VY10G)

`cargo nextest run --workspace --profile ci` measured 138 s wall on the
12-core host with 1355 tests, 765 s of test time; one test was the wall
(`frob-check::perf`, a cold then warm full check of this repository in a
debug build, 98-136 s). The fix keeps every proof and moves it to the
place that can check it cheaply:

- Function and performance are separate. `frob-check/tests/perf.rs`
  asserts on a small generated fixture that stages are timed and that a
  second run hits the cache (0.3 s). The real-repository measurement is
  the `full_check` criterion bench ("bench (scheduled)", section 4), in
  release: it deletes the derived `.frob/cache.sqlite`, times the cold
  run (budget 60 s, measured 20-30 s on a loaded host) and the warm run
  (budget 2 s, architecture.md section 9; measured 1.2 s), and fails
  with the number. Run it with `cargo bench -p frob-check --bench
  full_check`.
- `frob-ack/tests/workspace.rs` walks a generated 40-module fixture
  instead of this repository: DRIFT002 on a bad target is covered by
  `ack.rs`, and this repository's own doc targets are what the `check`
  step of `cargo dev ci` enforces, so the real walk only repeated it.
- `gob-ir/tests/deep.rs` keeps the million levels, built once (totality
  on a default stack). Determinism is compared across two builds at
  50,000 levels: the property is per algorithm, not per depth.
- Build profile: `[profile.dev.package.gob-ir] opt-level = 2` takes the
  deep test from 70 s to 8-14 s at no measurable clean-compile cost (the
  crate is small). Rejected on measurement: `[profile.dev.package."*"]
  opt-level = 2` (clean compile with sccache warm 1 m 36 s against 1 m 07 s,
  suite no faster) and `gob-symbols`, `frob-check`, `frob-cli` at
  opt-level 1 (clean compile slower, suite no faster). The suite is now
  bound by aggregate CPU of the many `frob-cli` tests that spawn the debug
  binary, which no per-crate opt level moved outside noise.
- Two guards, for two purposes. Hang guard: the nextest `ci` profile
  terminates and fails any test over 120 s (`slow-timeout` period 30 s,
  `terminate-after` 4), so a hung test fails fast while slower CI runners
  (4-core GitHub runners, windows-latest) never trip it; a test that
  legitimately needs more gets a reasoned entry in the reviewed override
  list in `.config/nextest.toml` (none today), never an ignore. Speed
  regression: `cargo dev ci` reads `target/nextest/ci/junit.xml` after the
  nextest step, prints the suite wall time and the five slowest tests, and
  warns (never fails) when a test exceeds 30 s or the suite exceeds 90 s on
  the host running it. A wall-clock failure threshold would fail by machine
  speed (8 s tests timed out at host load 26), which is noise, not a guard.

Measured 2026-10-03 on the shared 12-core host (load varied 9 to 60 from
other builds, so compare within a row, not across rows):

| Measure | Before | After |
|---|---|---|
| nextest ci wall (tests only) | 138 s idle; 295 s at load 34 with a terminate | 47-62 s at load 10-17 (target 60 s, met in all but one run, 62 s); 78 s inside `cargo dev ci` |
| slowest test | perf 98-136 s | `gob-ir::deep` 8-14 s |
| clean compile, sccache warm | 1 m 07 s to 3 m 53 s (load 17 to 61) | 1 m 36 s with `"*"` opt 2 (rejected); gob-ir opt 2 within noise of baseline |

`frob` in this checkout is the workspace binary via `cargo run -q --`
alias `cargo frob`; a stale global install is detected (version
mismatch warning) as in v1 but never blocks.

Test selection as built (frob-tests): a test is detected by an attribute
scan (`#[test]` and its relatives), by items inside a `tests` module, or
by living in a `tests/` directory (a heuristic that over-approximates
helpers in `tests/`; a helper only adds a filter that matches nothing).
Selection walks the reach of the touched symbols through the call graph
and adds a backstop: a test calling a touched function by a unique name
is selected even when the edge is Ambiguous. Selection is a lower bound:
when an Unknown edge leaves a touched symbol, the run reports one
Unresolved ("selection incomplete: N unresolved call sites") and widens
to the file's crate instead of recording Passed over an incomplete set
(code-model.md section 6). `frob test` runs the
selection through nextest and records evidence on the lease-holding
ticket; TEST001 is owned by frob-tests.
