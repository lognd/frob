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

## 1. Build locality

- Proc-macro crate (`gob-macros`) tiny and stable; grammar C builds
  isolated in `gob-languages` with per-grammar features; tokio only in
  the serve and gh crates (boundaries.md section 6).
- Dev profile: `opt-level = 1` for deps, `debug = "line-tables-only"`,
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
| markdown corpora | `gob-mdtest` on datatest-stable: a fenced in-memory repo, then expected findings or expected symbols/edges | `crates/*/tests/md/*.md` |
| snapshots | insta for rendered output, `--json` payloads, generated docs | each crate |
| proc macros | trybuild compile-pass and compile-fail cases | `gob-macros/tests` |
| CLI end to end | assert_cmd + assert_fs against a fixture repo; snapbox transcripts for `--help` | `crates/{frob,grimble,crunk}/tests` |
| property | proptest for ids, merge driver, lease overlap | ledger, lease |
| language conformance | per-adapter fixture dir with expected symbols, digests, IR, imports; the capability matrix test | `gob-languages`, `gob-symbols`, `gob-ir` |
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
| release (tag) | cargo-dist per binary on `frob-v*`, `grimble-v*`, `crunk-v*`; linux x86_64/aarch64, macos arm64, windows; crates.io publish of the full crate set in lockstep versions (monorepo.md section 4); `uv tool`-installable PyPI shims (the `frob` wheel bundles all three); Milestone 2 or later (D36) | 10 min |

Every third-party action pinned by SHA, every toolchain version pinned
in one `env:` block (v1 lesson: unpinned actions drifted). The budget for a green PR run is
15 minutes wall, against v1's 123.

## 5. Developer loop

```
cargo dev gen                   # after adding a rule / command / config key
cargo nextest run -p <crate>    # focused
frob check --ticket <id>        # the gate, scoped
frob test --base main           # touched tests via frob's own selection
```

`frob` in this checkout is the workspace binary via `cargo run -q --`
alias `cargo frob`; a stale global install is detected (version
mismatch warning) as in v1 but never blocks.
