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
   rules.md section 3), G18 (was `grimble migrate`; dropped, D136), G19 grimble-serve.
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
| markdown corpora | `gob-mdtest`: a fenced in-memory repo, then expected findings or expected symbols/edges; the `mdtest!` macro generates one nextest case per corpus directory (reporting every file in it); a fenced block without `expect=` is documentation, not a test | `crates/*/tests/mdtest/**/*.md` |
| snapshots | insta for rendered output, `--json` payloads, generated docs | each crate |
| proc macros | trybuild compile-pass and compile-fail cases | `gob-macros/tests` |
| CLI end to end | assert_cmd + assert_fs against a fixture repo; snapbox transcripts for `--help` | `crates/{frob,grimble,crunk}/tests` |
| property | proptest for ids, merge driver, lease overlap | ledger, lease |
| language conformance | per-adapter fixture dir with expected symbols, digests, U terms, imports; the capability matrix test | `gob-languages`, `gob-symbols`, `gob-ir` |
| rule docs executable | every rule's doc example runs as an mdtest (ty lint_docs pattern) | generated |
| self-hosting | `frob check` on this repo in CI, zero errors (milestone 1: frob only; sibling merging is Milestone 2 or later (D36)) | workflow |

Markdown corpus format (the authority is `crates/gob-mdtest/FORMAT.md`):

````
<!-- mdtest: rule=COV001 -->
# COV001 fires for an undocumented public function

```rust expect=fire file=src/lib.rs
pub fn f() {} // error: COV001
```

```rust expect=clean file=src/lib.rs
/// Documented.
pub fn f() {}
```
````

Rule testing model (D103, from the source review in
notes/research/rule-testing.md): ruff now tests rules with the same shared
mdtest crate as ty, so the primary rule test here is one mdtest file per
rule with strict inline markers (rule, severity, line, optional column and
message), sections that can hold several files and a toml config block,
and inline `snapshot` blocks for the rendered diagnostic including the fix
diff. The runner applies ruff's fix invariants to every case with a
fixable finding (fixpoint within 10 rounds, reparse, no new parse error,
no fixable finding left). Each rule's documentation is itself an mdtest
file (ty lint_docs), so a bare `error:` there means that rule. Large
real-shaped inputs keep the fixture plus insta snapshot layer
(`resources/test/fixtures/<FAMILY>/<RULE>.<ext>`). Coverage meta-tests
(every rule has a fire and a clean case or a fixture, every fixable rule
has a fix snapshot, every rule has runnable docs) and the ecosystem check
(section 6) sit on top. The fire-and-clean controls and the shrink-only
coverage allowlist are frob additions that neither ruff nor ty has. D106
(testing.md) extends the vocabulary to unresolved and notapplicable with
subject accounting, because U is not two-valued: a clean case certifies
at least one examined subject, and strictness counts Unresolved findings.

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
| command profile | `cargo dev profile`: every leaf command of frob, grimble and crunk against `profile.toml` budgets, report artifact, deltas against the last experimental run (Command profile below) | 20 min |
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
The `dotnet` evidence provider (~9W0WEA9) runs `dotnet test --nologo --logger
trx;LogFileName=frob.trx --results-directory <fresh dir>` with a `--filter` of
`FullyQualifiedName=<id>|FullyQualifiedName~<id>\(` per C# test id (the second form
folds parameterized cases into their method), parses the TRX per test (outcome,
duration, error message, stdout) and names each test `Namespace.Type.Method` from the
report's `TestMethod` definition. `dotnet` must be in `[evidence] allowed_tools`;
`[evidence.dotnet] path` names the executable (empty finds `dotnet` on `PATH`), and an
absent executable or a host without an SDK (`dotnet --version` not exiting 0) refuses
with `E-EVIDENCE-RUNNER-MISSING` and a remedy, recording nothing. A run that exits 0
yet executed no test refuses as `E-EVIDENCE-NO-TESTS`. Its tests need no .NET SDK: they
run the `fake-dotnet` helper binary of `gob-testsupport` (a stand-in that copies a canned
TRX to the results directory; a native executable, not a shell script, so it runs on
Windows too).
The `pytest` provider and `frob test` start pytest through the project interpreter
(~FP0SDK3): `[tests] python` when set (a name on `PATH`, or a path relative to the
repository root), else `.venv/bin/python` in the repository root when it exists, else
`pytest` on `PATH`; the first two run `<python> -m pytest`, and `frob test --dry-run`
prints the resolved launcher as `pytest_runner`. Exit 2, 3 or 4 (interrupted, internal or
usage and collection errors) means pytest could not run the tests: the run refuses with
`E-EVIDENCE-RUNNER-ERROR` (reason `runner-error`) naming the files that failed to
collect, and records no evidence.
Tests that run pytest (frob-evidence and frob-tests) need `python3` and
`pytest` on `PATH` and skip with a named reason when they are absent
(`gob_testsupport::python_test_prerequisites`); setting
`FROB_REQUIRE_PYTHON_TESTS` turns the skip into a failure, so a host that
installs both can never pass silently without them. Under `CI` (set by
GitHub) `steps()` gives the `nextest` step that variable, and a `pytest`
step (before `nextest`; `ci.yml` sets up python 3.12 and uv first)
runs `uv tool install --force` of the pinned `PYTEST_REQUIREMENT` (idempotent; pip
is not used because hosts under PEP 668 refuse it), and the `nextest` step
runs with `uv tool dir --bin` in front of `PATH`, so CI cannot skip them.
uv is a declared prerequisite: the repo-root `goway.toml` lists it under
`[toolchain] tools` so `goway doctor --fix` installs it on each helper, and
`ci.yml` installs it with a pinned `astral-sh/setup-uv` (the zizmor and
actionlint steps need `uvx` from it too). A developer machine
keeps the named skips. The Windows job does not set the variable yet: its
python has no `python3` name for the probe (follow-up ticket).
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

### Command profile (~RWD03DW)

`cargo dev profile` times every leaf command of `frob`, `grimble` and
`crunk` and fails when one is over its budget. Nothing is hand-listed:

- **Binaries.** It builds the three products with `[profile.profiling]`
  (inherits `release`, no LTO so a profile build links quickly,
  `debug = "line-tables-only"` so `perf` and `samply` can attribute
  frames). `--bin-dir DIR` skips the build.
- **Leaf discovery.** Each binary's own `--help` is walked (`Commands:`
  sections, recursively); a leaf is a command with no subcommands. This
  was chosen over the clap trees in-process (`Cli::verb_flags`) because
  linking `grimble` and `crunk` into the tool would register their verbs
  in the command inventory and change the generated CLI reference
  (`cargo dev gen`); help text needs no dependency and is the very
  binary being measured. `crates/gob-dev/tests/profile_coverage.rs` does
  use `verb_flags` (grimble and crunk as dev-dependencies, which the
  generator test binary does not link) and fails naming every leaf with
  no scenario and no `skip` reason, and every scenario naming no leaf.
  Deprecated aliases are not leaves; their target is profiled.
- **Scenarios.** `crates/gob-dev/profile.toml` holds one
  `[scenario."<product> <verb...>"]` per leaf: `args` (`{ticket}`
  expands to a ticket handle of the clone), `fixture` (`repo`, the
  default, or `tmp`), `readonly`, `cold`, `timing`, `exit` (the allowed
  exit codes; refusals such as 3 are legitimate outcomes for verbs whose
  precondition the fixture does not meet), `runs` (a cap for slow
  commands), `budget_ms` and, with `cold`, `cold_budget_ms`, or `skip =
  "reason"` instead.
- **Isolation.** No scenario runs in the source checkout. `repo` is a
  `git clone --local` of it into a temporary directory, taken at HEAD
  with every branch and tag copied, `experimental` forced to a local
  branch at HEAD and `origin` removed, so no verb can push back; `tmp`
  is a fresh repository with one empty commit. A scenario not marked
  `readonly` (the default) gets a clone of its own, so mutating verbs
  (`work`, `land`, `ticket new`, `ack`, `release cut`, ...) never see
  each other's changes. A test mutates a clone (commits, moves branches
  and tags, edits the index) and asserts that the source's HEAD, refs,
  index, status and config are byte-identical afterwards.
- **Measures.** One warm-up, then `--runs N` (default 5) timed runs, the
  median reported; `cold = true` deletes `.frob/` and also times the first
  run; peak RSS comes from one extra run under GNU `time -f %M` (Linux;
  absent elsewhere); `timing = true` records the `--timing` stage tree of
  `frob check`. Wall time is the supervising runner's, which polls the
  child every 5 ms, so fast commands read up to 5 ms high.
- **Budgets.** `budget_ms` is absolute. A run fails (exit 1, one `PROFILE:`
  line each naming command, measured value and `budget x factor`) when a
  warm median or cold run exceeds `budget_ms * --budget-factor`, or when
  any run exits with a code the scenario does not allow. Seeds are about 3
  times the warm median measured below, rounded up to 100 ms, with a floor
  of 500 ms (cold budgets: 3 times, rounded up to a second).
- **Output.** `target/profile/report.json` (the serde `Report` in
  `profile/model.rs`, `schema_version` 1) and a markdown table on stdout
  and appended to `$GITHUB_STEP_SUMMARY` when set. `--compare BASE.json`
  adds per-command deltas and never fails (a missing base only warns).
  `--only GLOB` (repeatable) profiles a subset, for example
  `cargo dev profile --only 'frob ticket *'`.
- **CI.** The `profile` job in `ci.yml` runs on ubuntu-latest in parallel
  with the `rust` job (same toolchain pin, cache and linker step), runs
  `cargo dev profile --budget-factor 2 --compare
  target/profile/base/report.json` (GitHub runners are slower than the
  seed host; the factor is the headroom), uploads `report.json` as the
  `profile-report` artifact and downloads the newest successful
  `experimental` run's artifact with the `gh` CLI as the comparison base.
  Like every test job it is awaited by the dev-channel jobs (a test in
  frob-release pins that), so a budget breach holds the dev publish.

Measured 2026-10-08 on the aarch64 development host (12 cores, load
average 8 to 12 from other builds, so absolute numbers are pessimistic),
`profiling` profile, 5 runs (3 for the slow commands), milliseconds and
MiB:

| Command | Warm | Cold | RSS | Exit | Budget |
|---|---:|---:|---:|---:|---:|
| `crunk check` | 7 | 10 | 6 | 3 | 500 |
| `crunk doctor` | 6 | - | 6 | 0 | 500 |
| `crunk schema` | 6 | - | 6 | 0 | 500 |
| `frob ack` | 2151 | - | 408 | 0 | 6500 |
| `frob board` | 2605 | - | 49 | 0 | 7900 |
| `frob check` | 12761 | 195569 | 449 | 0 | 38300 |
| `frob config show` | 11 | - | 15 | 0 | 500 |
| `frob config sync` | 6 | - | 15 | 0 | 500 |
| `frob cycle assign` | 81 | - | 22 | 3 | 500 |
| `frob cycle close` | 128 | - | 22 | 3 | 500 |
| `frob cycle list` | 230 | - | 23 | 0 | 700 |
| `frob cycle new` | 116 | - | 21 | 0 | 500 |
| `frob cycle plan` | 96 | - | 22 | 3 | 500 |
| `frob cycle show` | 137 | - | 23 | 0 | 500 |
| `frob cycle unassign` | 129 | - | 22 | 3 | 500 |
| `frob cycle velocity` | 3501 | - | 59 | 0 | 10600 |
| `frob doctor` | 2040 | - | 35 | 0 | 6200 |
| `frob graph affects` | 2163 | - | 409 | 0 | 6500 |
| `frob graph why` | 1953 | - | 412 | 0 | 5900 |
| `frob init` | 31 | - | 16 | 0 | 500 |
| `frob land` | 16 | - | 19 | 3 | 500 |
| `frob lease list` | 11 | - | 15 | 0 | 500 |
| `frob lease widen` | 21 | - | 19 | 3 | 500 |
| `frob milestone add` | 36 | - | 22 | 3 | 500 |
| `frob milestone criterion add` | 43 | - | 22 | 0 | 500 |
| `frob milestone criterion remove` | 32 | - | 22 | 2 | 500 |
| `frob milestone evidence add` | 27 | - | 22 | 3 | 500 |
| `frob milestone evidence list` | 31 | - | 22 | 0 | 500 |
| `frob milestone list` | 47 | - | 23 | 0 | 500 |
| `frob milestone new` | 33 | - | 21 | 0 | 500 |
| `frob milestone show` | 50 | - | 23 | 0 | 500 |
| `frob release adopt` | 42 | - | 22 | 0 | 500 |
| `frob release bump` | 16 | - | 14 | 0 | 500 |
| `frob release changelog` | 82 | - | 19 | 3 | 500 |
| `frob release cut` | 31 | - | 22 | 3 | 500 |
| `frob release notes` | 6 | - | 13 | 0 | 500 |
| `frob release status` | 1581 | - | 44 | 0 | 4800 |
| `frob requeue` | 22 | - | 19 | 0 | 500 |
| `frob schema` | 7 | - | 13 | 0 | 500 |
| `frob test` | 4918 | - | 455 | 0 | 14800 |
| `frob ticket branch init` | 20 | - | 15 | 0 | 500 |
| `frob ticket close` | 57 | - | 24 | 3 | 500 |
| `frob ticket comment` | 157 | - | 47 | 0 | 500 |
| `frob ticket doable` | 36 | - | 21 | 0 | 500 |
| `frob ticket doctor` | 8888 | - | 62 | 0 | 26700 |
| `frob ticket drop` | 17 | - | 19 | 0 | 500 |
| `frob ticket evidence add` | 11 | - | 19 | 3 | 500 |
| `frob ticket evidence fetch` | 37 | - | 24 | 3 | 500 |
| `frob ticket evidence list` | 26 | - | 24 | 0 | 500 |
| `frob ticket fragment` | 21 | - | 19 | 3 | 500 |
| `frob ticket link` | 17 | - | 19 | 3 | 500 |
| `frob ticket list` | 28 | - | 22 | 0 | 500 |
| `frob ticket new` | 144 | - | 30 | 0 | 500 |
| `frob ticket reopen` | 21 | - | 19 | 0 | 500 |
| `frob ticket show` | 41 | - | 24 | 0 | 500 |
| `frob ticket triage accept` | 36 | - | 24 | 0 | 500 |
| `frob ticket triage decline` | 16 | - | 19 | 2 | 500 |
| `frob ticket triage duplicate` | 41 | - | 24 | 3 | 500 |
| `frob ticket triage snooze` | 39 | - | 24 | 3 | 500 |
| `frob ticket unlink` | 19 | - | 19 | 0 | 500 |
| `frob ticket update` | 21 | - | 19 | 0 | 500 |
| `frob work` | 16 | - | 19 | 3 | 500 |
| `grimble ack` | 11 | - | 11 | 2 | 500 |
| `grimble check` | 964 | 1087 | 185 | 0 | 2900 |
| `grimble doctor` | 412 | - | 126 | 0 | 1300 |
| `grimble exceptions list` | 1031 | - | 151 | 0 | 3100 |
| `grimble fmt` | 532 | - | 143 | 1 | 1600 |
| `grimble init` | 11 | - | 11 | 0 | 500 |
| `grimble schema` | 5 | - | 7 | 0 | 500 |

Findings from the first run, filed as follow-ups rather than fixed here:
`frob check` takes about 13 s warm in a fresh clone against the 2 s warm
budget of architecture.md section 9 (cold 196 s against 20-30 s measured
in release by the `full_check` bench), `frob ticket doctor` about 9 s,
`frob cycle velocity` 3.5 s, `frob test` 4.9 s, and `frob board` and
`frob doctor` 2 to 3 s; their budgets above are the measured numbers, not
targets.

### Fast lands: affected cone at land, full check on CI (~TSYTGDE)

Landing is the throughput ceiling: a land re-ran the whole check three
times (452 to 643 s measured, notes/research/profile-2026-10-07.md
section 3.8). The decision (owner, 2026-10-09) is the one large
monorepos converged on: **test the change, not the repository, before
merge; test everything after merge, and stop the line when it is red.**
Precedents: Google's Test Automation Platform runs, per change, only the
tests whose build-graph cone contains a touched target and runs the
rest continuously post-submit (Memon et al., "Taming Google-Scale
Continuous Testing", ICSE-SEIP 2017); Uber's SubmitQueue orders and
speculatively builds changes, merging only those that pass against the
tip, and finds culprits by bisection (Ananthanarayanan et al., "Keeping
Master Green at Scale", EuroSys 2019).

1. **Affected cone at land.** The check of `frob land` evaluates the
   touched files plus their dependency cone: for frob rules the reverse
   closure over the obligation graph, with `Unknown` and `May` edges
   included (an edge that cannot be resolved widens the cone, never
   narrows it). Cargo stages run over the affected crates and their
   reverse dependencies; a stage that declares input paths in
   `frob.toml` (`dev gen --check` declares the generator inputs) is not
   run or gated when the ticket touches none of them.
2. **Moving base.** New base commits that touch nothing in the ticket's
   cone, ledger-only commits included, force neither a re-check nor
   `E-LAND-STALE`; only a commit inside the cone does.
3. **CI split.** The full unscoped check, the whole suite and the
   cross-platform jobs run on CI after every land. This is the safety
   net for what the cone misses, so the cone may be conservative but
   never needs to be exact.
4. **Red CI stops the line.** A red CI run on the base blocks further
   lands (`require_base_green`, already enforced) until it is fixed or
   reverted; the culprit is found automatically by bisecting the lands
   since the last green run, and the ticket that introduced it is
   reopened with the failing evidence.
5. **Cheap guards first.** Ledger-only close guards (unbound criteria,
   missing evidence) are evaluated before any check, so a doomed land
   refuses in seconds (~Y7E721R).
6. **Shared build state.** Land checkouts share one persistent cargo
   target directory and one persistent base checkout (~8J3BE8W), and
   tool stages run concurrently (~S2EJV2N), so a scoped stage starts
   warm.

Guardrails: a land never skips a rule it cannot place in a cone (it
runs it); a stage without declared inputs always runs; the ratchet
(rules.md section 6) still refuses only findings the ticket introduces;
and the cone computation is itself covered by a CI job that compares the
scoped verdict against the full check on recent lands and reports any
disagreement as a defect of the cone.

Target: a one-crate code ticket lands in under 60 s on this repository.
The CLI-side wording (the `land` verb's scope flags and report fields)
belongs in cli.md section 3 and follows the implementation tickets.

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

C# tests (~YJ5RTJ6) are detected by attribute (NUnit, xUnit, MSTest,
UnityTest) and selected through the same reach graph; a changed C# file
seeds its changed members (a namespace or type whose own signature is
unchanged is not a seed, so editing one method does not select every test
of the file), and the parts of a partial type are one unit. A selected test
is a `TestTarget` carrying the fully qualified method name
(`Namespace.Type.Method`) and its owner: a Unity `.asmdef` assembly when
the file belongs to one, else its `.csproj` project. Plan lines are
`dotnet <project> <id>` and `unity <assembly> <id>`. Projects run through the
`dotnet` evidence provider, one `dotnet test <project> --filter ...` per
project (`--all` runs each test project whole), and the TRX results become
one evidence event per project. Selecting a Unity assembly test refuses the
run with `E-TESTS-UNITY-PROVIDER` before anything runs: the message carries
the selection and names the unity provider (~F17DMKH), and the remedy is
the Unity Test Runner. `--dry-run` still prints the selection. A change no
test reaches selects nothing and the run says so (`no tests reach the
touched set; nothing was run`).

## 6. Tests and CI modelled on ruff and ty (D98)

Owner request 2026-10-06: build the tests, snapshots and CI/CD like
Astral's ruff and ty. Most of section 2 already follows them (mdtest is
ty's format, insta snapshots, rule docs as tests). The rest:

| Practice (Astral source) | Ours |
|---|---|
| Rule tests as markdown with inline assertions; `<!-- snapshot-diagnostics -->` snapshots the rendered diagnostics of a section (ty mdtest) | `gob-mdtest` already has markers and positive controls; it gains the `snapshot-diagnostics` header, which writes an insta snapshot of the full text rendering (source excerpt, labels, help) for that file |
| One fixture file per rule plus a snapshot of its diagnostics, and a registry test that no rule lacks one (ruff `resources/test/fixtures/<linter>/<CODE>.py`) | `crates/<product>-rules/resources/test/fixtures/<FAMILY>/<RULE>.<ext>` for larger real-shaped inputs; a registry-driven test fails naming every registered rule with neither an mdtest fire/clean pair nor a fixture |
| Fix snapshots and fix convergence: apply fixes to a fixpoint, snapshot the diff, fail if a fix introduces a parse error or does not converge (ruff test harness) | the gob-fix harness (~29MKDDF) snapshots each fixable rule's diff and runs the fixpoint (at most 10 rounds), reparse and no-new-error checks for every fixture |
| Inline parser tests: `test_ok`/`test_err` comments in parser source extracted to `resources/inline/{ok,err}` with AST and error snapshots (ruff_python_parser, from rust-analyzer) | GRL, .grmb, directives and the crunk.toml spec parser use `// test_ok NAME` / `// test_err NAME` blocks; `cargo dev gen` extracts them, GEN001 keeps them current, insta snapshots the tree and errors |
| Formatter idempotence and stability (ruff_python_formatter) | `grimble fmt` and the GRL printer: format(format(x)) = format(x) and parse(print(t)) = t over every fixture and a proptest generator |
| Snapshot hygiene: no stale or unreviewed snapshots (`cargo insta test --unreferenced reject`) | the nextest step runs with `INSTA_UPDATE=no`; a `snapshots` step in `cargo dev ci` fails on unreferenced or pending `.snap.new` files |
| Ecosystem check: run the base and PR binaries over pinned real projects and comment the finding diff (ruff ecosystem, ty ecosystem-analyzer) | `cargo dev ecosystem`: a pinned corpus (`ecosystem.toml`, repository and SHA per entry: Rust, Python, TS/React, C#/Unity, this repo) checked by both binaries; report = per-rule added/removed/changed findings, crashes, Unresolved deltas and timing; non-blocking PR comment; runs on goway helpers |
| Fuzzing in CI (ruff `fuzz/`, built on every PR) | `fuzz/` with cargo-fuzz targets for every parser (GRL, .grmb, directives, crunk.toml, ledger events) and the fold; PRs build the targets and run each 60 s; a nightly job runs longer and files a ticket per crash |
| Deterministic benchmarks on PRs (ruff on CodSpeed) | instruction-count benchmarks (iai-callgrind or its maintained successor, Valgrind based, no external service; the ticket pins the crate) for cold and warm check, the plan executor and the parsers, compared against the base and commented; criterion stays for the scheduled wall-clock bench |
| Change detection: skip jobs a diff cannot affect (ruff `determine_changes`) | a first `changes` job maps paths to job sets (Rust, docs only, crunk node and playwright ~2H41VF1, workflows); a docs-only PR runs fmt, gen check and frob check only |
| Hygiene jobs: cargo-shear, cargo-deny, typos, MSRV | `deny` (cargo-deny advisories, licenses, bans), `shear` (unused deps), `typos`, `msrv` (build at `rust-version`) steps in `cargo dev ci`, each a tool pinned in frob.toml like zizmor |
| Release through one workflow with wheels and binaries (cargo-dist plus maturin) | unchanged: the hand-written release.yml (D83) already does both |

Every row is a `cargo dev ci` step or a nextest test, so local runs, goway
runs and GitHub Actions run the same thing (section 4).
