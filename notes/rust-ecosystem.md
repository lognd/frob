# Rust ecosystem survey for frob v2

Date: 2026-10-01. Toolchain on this machine: cargo/rustc 1.98.0, mold and
clang at /usr/bin. Versions below were checked against the crates.io API on
the date above unless marked UNCERTAIN. Local ~/.cargo/registry already holds
most candidates (salsa 0.28.5, gix 0.81, tree-sitter 0.25.10, insta 1.48,
schemars 1.2.2, rkyv 0.8.18, miette 7.6, clap 4.6.6, datatest-stable 0.3.3,
libtest-mimic 0.8.1, tower-lsp-server 0.23, lsp-server 0.10, notify 8.2).

Sections:

0. Lint-rule macro machinery (top priority)
1. How ruff / uv / ty are structured
2. Crate shortlist per concern
3. Prior art: in-repo issue tracking
4. Prior art: cross-language symbol identity
5. Workspace layout for fast incremental builds
6. Open questions / uncertainties

---------------------------------------------------------------------------

## 0. Lint-rule macro machinery

### 0.1 ruff: ViolationMetadata + Violation + map_codes

Files (astral-sh/ruff, main):

| File | Role |
|---|---|
| crates/ruff_macros/src/violation_metadata.rs | `#[derive(ViolationMetadata)]` proc macro |
| crates/ruff_macros/src/derive_message_formats.rs | `#[derive_message_formats]` attribute on `fn message` |
| crates/ruff_macros/src/map_codes.rs | `#[map_codes]` attribute: generates `Rule` enum and all code tables |
| crates/ruff_macros/src/rule_namespace.rs | `#[derive(RuleNamespace)]` on the `Linter` enum |
| crates/ruff_macros/src/rule_code_prefix.rs | per-linter prefix enums (`E1`, `E11`, ...) |
| crates/ruff_linter/src/violation.rs | `ViolationMetadata`, `Violation`, `AlwaysFixableViolation` traits |
| crates/ruff_linter/src/codes.rs | the one big `match` of `(Linter, "CODE") => path::ToStruct` |
| crates/ruff_linter/src/registry.rs | `Linter` enum with `#[prefix = "E"]` attrs; re-exports `Rule` |
| crates/ruff_dev/src/generate_docs.rs | one Markdown page per rule from `Rule::explanation()` |
| crates/ruff_dev/src/generate_rules_table.rs | rules.md table |
| crates/ruff_dev/src/generate_all.rs | `cargo dev generate-all` with Write/Check/DryRun modes |

How the pieces compose (verified from source):

1. A rule is a plain struct with doc comments and one attribute:

```rust
/// ## What it does
/// Checks for ...
///
/// ## Why is this bad?
/// ...
#[derive(ViolationMetadata)]
#[violation_metadata(stable_since = "0.1.0", category = Category::Correctness)]
pub(crate) struct MixedSpacesAndTabs;

impl Violation for MixedSpacesAndTabs {
    const FIX_AVAILABILITY: FixAvailability = FixAvailability::None;
    #[derive_message_formats]
    fn message(&self) -> String { "Indentation contains mixed spaces and tabs".to_string() }
    fn fix_title(&self) -> Option<String> { None }
}
```

2. `derive(ViolationMetadata)` (violation_metadata.rs, 175 lines) collects
   every `#[doc]` attr into one string, parses `violation_metadata(...)`
   (`stable_since|preview_since|deprecated_since|removed_since` validated
   against a semver regex, plus `category`), and emits
   `impl ViolationMetadata for T { fn rule() -> Rule { Rule::T } fn explain()
   -> Option<&'static str> fn status() fn category() fn file() { file!() }
   fn line() { line!() } }`. The struct name is the `Rule` variant name;
   nothing else links them.

3. `#[derive_message_formats]` walks the body of `fn message`, finds every
   `format!("...")` / `"...".to_string()` branch and emits
   `fn message_formats() -> &'static [&'static str]` so docs can list all
   message shapes without instantiating the struct.

4. `#[map_codes]` on `fn code_to_rule(linter, code) -> Option<(RuleStatus,
   Rule)>` in codes.rs parses the trailing `Some(match (linter, code) {
   (Pycodestyle, "E101") => rules::pycodestyle::rules::MixedSpacesAndTabs,
   ... })` and generates:
   - `pub enum Rule { MixedSpacesAndTabs, ... }` (`#[repr(u16)]`, strum
     `kebab-case` names, `EnumIter`), keeping each arm's `#[cfg]` attrs;
   - `Rule::{message_formats, explanation, fixable, status, category, file,
     line, noqa_code, is_preview, ...}` as big `match` tables that call the
     trait statics on each struct path;
   - `RuleCodePrefix` enum, per-linter prefix enums, `Linter::rules()`,
     `Linter::all_rules()`, `code_for_rule()`, `FromStr` for kebab names;
   - output is sorted to keep proc-macro output stable for incremental
     compilation (comment in generate_rule_to_code).
   The macro panics if one rule maps to two codes.

5. `derive(RuleNamespace)` on `enum Linter` reads `#[prefix = "E"]`
   (multiple allowed, must not share first char, globally unique) and the
   variant doc comment (`/// [pycodestyle](https://...)`) and emits
   `parse_code`, `common_prefix`, `name`, `url`.

6. `ruff_dev generate-docs` iterates `Rule::iter()`, takes `explanation()`,
   `status()`, `file()`/`line()` (for a "View source" link), `fixable()`,
   and writes `docs/rules/<kebab>.md`. `generate-rules-table` writes the
   big table. `generate-all` runs every generator; `--mode check` fails CI
   with a truncated unified diff (`similar::TextDiff`) if files are stale.
   Alias: `.cargo/config.toml` `dev = "run --package ruff_dev --bin ruff_dev"`.

Properties worth copying: docs live on the struct; the registry is one
greppable match; status/version metadata is validated at compile time;
`file!()`/`line!()` give free source links; everything downstream is
generated and checked in CI.

Properties not worth copying: the Rule enum is a closed world generated by
one macro invocation over a 1400-line file; adding a rule touches two
places (struct + codes.rs arm); `map_codes` is tightly bound to ruff's
`Linter`/prefix selection model (`--select E1`), which frob does not need.

### 0.2 ty: declare_lint! + LintMetadata + LintRegistry

File: crates/ty_python_semantic/src/lint.rs (681 lines), plus
crates/ty_python_semantic/src/types/diagnostic.rs (`register_lints`).

```rust
declare_lint! {
    /// ## What it does
    /// Checks for references to names that are not defined.
    pub(crate) static UNRESOLVED_REFERENCE = {
        summary: "detects references to names that are not defined",
        status: LintStatus::stable("1.0.0"),
        default_level: Level::Warn,
    }
}
```

`declare_lint!` is a `macro_rules!` (not proc) that expands to a
`static NAME: LintMetadata = LintMetadata { name: LintName::of(
ruff_macros::kebab_case!(NAME)), summary, raw_documentation: concat!(docs),
file: file!(), line: line!(), default_level, ..lint_metadata_defaults(status) }`.
Docs may also be `#[doc = include_str!("../resources/lint_docs/x.md")]`;
`documentation_lines()` strips the leading space only when the text came
from `///`. `LintId` is a pointer-identity newtype over `&'static
LintMetadata`. Registration is explicit and manual:
`pub(crate) fn register_lints(registry: &mut LintRegistryBuilder) {
registry.register_lint(&UNRESOLVED_REFERENCE); ... }` with duplicate-name
asserts and `register_alias`. `ruff_dev generate-ty-rules` walks
`default_lint_registry().lints()` and writes crates/ty/docs/rules.md.

Each lint also has a Markdown fixture under resources/lint_docs/<name>.md
that is executed as an mdtest (see 1.4), so every rule doc is a test.

Verdict: much simpler than ruff's, open-world (any crate can declare a
lint), and the only cost is the explicit `register_lint` list. This is the
model closest to what frob needs.

### 0.3 clippy: declare_clippy_lint!

declare_clippy_lint/src/lib.rs: `declare_clippy_lint!` dispatches on the
category token, calls rustc's `declare_tool_lint!`, and additionally emits
`pub(crate) static <NAME>_INFO: &'static LintInfo = &LintInfo { lint,
category, explanation: concat!(docs), location: concat!(file!(), "#L",
line!()), version }`. The registry
clippy_lints/src/declared_lints.rs (`pub static LINTS: &[&LintInfo] = &[
crate::absolute_paths::ABSOLUTE_PATHS_INFO, ... ]`) is a GENERATED file
(`cargo dev update_lints` scans source for the macro). Same shape as ty but
the registration list is produced by a dev tool instead of by hand.

### 0.4 biome and oxc

- biome: crates/biome_analyze/src/rule.rs `declare_lint_rule!` ->
  `declare_rule!` -> `enum RuleName {}` + `impl RuleMeta { type Group;
  const METADATA: RuleMetadata = RuleMetadata::new(version, name, docs,
  language).severity(..).fix_kind(..) }` (const-builder chain for optional
  keys). Groups: `declare_lint_group! { Correctness { rules: [a, b] } }`,
  now generated at compile time by a proc macro
  `biome_analyze_macros::declare_group_from_fs! { category: "lint", group:
  "correctness" }` which scans the group directory for .rs files. Rule
  metadata docs and the JSON schema are generated by
  xtask/codegen/src/generate_rules_metadata.rs, generate_configuration.rs,
  generate_schema.rs, generate_new_analyzer_rule.rs (scaffolds a rule).
- oxc: crates/oxc_macros/src/declare_oxc_lint.rs is a proc macro
  `declare_oxc_lint!(/// docs  Name, plugin, category, fix)` that implements
  `RuleMeta { NAME, PLUGIN, CATEGORY, FIX, documentation() }`, validates
  that doc code fences are closed, supports `docs = "path"` for shared docs.
  Registry is `declare_all_lint_rules!` in crates/oxc_linter/src/rules.rs
  (hand-listed). `oxc_macros` is `publish = false`.

### 0.5 Reusable as published crates?

| Crate | crates.io | Reusable for frob? |
|---|---|---|
| ruff_macros 0.0.16 (2026-10-01) | yes, "internal component crate" | No. Generated impls reference `crate::registry::Rule`, `crate::codes::RuleStatus`; only works inside ruff_linter. |
| ruff_diagnostics / ruff_db / ruff_text_size / ruff_source_file 0.0.16 | yes, 0.0.x, lockstep with ruff releases | `ruff_text_size` (TextSize/TextRange) and `ruff_source_file` (line index) are small, stable, and usable. `ruff_db::diagnostic` (Diagnostic, Span, Annotation, rendering with annotate-snippets) is good but drags salsa + ruff's file system abstraction. Pin exact versions; no semver promise. |
| ruff_options_metadata 0.0.16 | yes | The `OptionsMetadata`/`Visit`/`OptionField` traits are 300 lines; copy rather than depend (the derive lives in ruff_macros and emits `ruff_options_metadata::` paths, so you cannot reuse the derive without the crate). |
| uv-macros / uv-options-metadata 0.0.89 | yes, same caveat | Same model as ruff's; uv-macros also has `attribute_env_vars_metadata` for env var docs. |
| biome_analyze 0.5.7 | STALE (2024-03-12); biome_diagnostics/biome_rowan/biome_console republished at 0.7.0 on 2026-09-19 | biome_analyze is not kept published; biome_diagnostics 0.7.0 is a solid diagnostics/rendering crate if you want biome's console model. Do not build on biome_analyze. |
| oxc_macros, oxc_linter | not published (`publish = false`) | No. |
| ast-grep-core / -config / -language 0.45.3 (2026-08-31) | yes, actively published | Yes for structural search over tree-sitter: `Pattern`, `Matcher`, YAML rule schema (`ast-grep-config` has `RuleConfig`, `Severity`, fix/transform). Use it as the engine for user-defined policy rules in frob.toml (frob already has tree-sitter query policy rules). It does not provide rule-doc/registry macros. |
| inventory 0.3.24 (2026-03-30) | yes | Registry by link-time collection (`inventory::submit!`, `inventory::iter`). Works on Linux/macOS/Windows; not on wasm. |
| linkme 0.3.37 (2026-07-18) | yes | `#[distributed_slice]`; same purpose, no ctor, needs `-Clink-dead-code`-safe usage on some platforms; both are fine for a native CLI. |
| rustc `declare_lint` | rustc internal | No. |

Conclusion: nothing published gives you the macro + registry + docs loop as
a drop-in. ty's 60-line `macro_rules!` plus a small proc macro is the
right size to own.

### 0.6 Recommendation: `frob-macros` + inventory registry

Design goals: one declaration site per gate rule; docs are the doc
comment; rule id, severity, category, fixability, status/since, and the
owning gate are compile-time constants; registry is open-world (any crate
in the workspace can add rules, including `frob-strata` kernel rules and
ticket-ledger rules); `frob dev generate-all` emits docs/rules/*.md, a
rules table, a JSON schema for `[rules]` config, and a `--list-rules`
JSON; a test asserts every rule has docs and a passing+failing fixture.

Macro input (derive form; mirrors ruff's ergonomics):

```rust
/// ## What it does
/// Flags `# TODO` comments that are not bound to a ticket.
///
/// ## Why is this bad?
/// Unbound TODOs are invisible to the ledger; use `frob:todo T-1234`.
///
/// ## Example
/// ```python
/// # TODO: handle timeout          # TODO001
/// # frob:todo T-1234 handle timeout
/// ```
#[derive(Rule)]
#[rule(
    code = "TODO001",
    gate = Gate::Directives,
    category = Category::Hygiene,
    severity = Severity::Error,
    fix = FixAvailability::Sometimes,
    stable_since = "2.0.0",
)]
pub struct BareTodo { pub text: String }

impl Violation for BareTodo {
    #[message_formats]
    fn message(&self) -> String { format!("bare TODO: {}", self.text) }
    fn fix_title(&self) -> Option<String> { Some("bind to a ticket".into()) }
}
```

Generated output (sketch):

```rust
impl ::frob_rules::RuleMeta for BareTodo {
    const META: &'static ::frob_rules::RuleMetadata = &::frob_rules::RuleMetadata {
        code: "TODO001",
        name: "bare-todo",                       // kebab of ident, via heck
        gate: Gate::Directives,
        category: Category::Hygiene,
        default_severity: Severity::Error,
        fix: FixAvailability::Sometimes,
        status: RuleStatus::Stable { since: "2.0.0" },
        explanation: "## What it does\nFlags ...",  // joined doc lines
        message_formats: &["bare TODO: {}"],      // from #[message_formats]
        file: file!(), line: line!(),
        type_name: ::core::any::type_name::<BareTodo>(),
    };
}
::inventory::submit! { ::frob_rules::RuleRegistration(BareTodo::META) }
```

Runtime registry (in `frob-rules`, ~150 lines): `RuleRegistry::global()`
builds once from `inventory::iter::<RuleRegistration>`, asserts unique
codes and names, sorts by code, exposes `get(code|name)`, `by_gate`,
`iter`, and a `schemars::JsonSchema` for the `[rules."TODO001"]` config
table. `RuleId` is a pointer-identity newtype like ty's `LintId`.

Code-generation (in `frob-dev`, run as `cargo dev generate-all` and checked
in CI with `--mode check`): docs/rules/<code>.md (header, status, gate,
"view source" link from file/line, message formats, explanation),
docs/rules.md table, schema/frob.schema.json (merging `OptionsMetadata`
output for frob.toml and the rules schema), docs/cli.md from clap
(`Command::render_long_help` per subcommand, like ruff's
generate_cli_help.rs with begin/end pragma markers), and
docs/env-vars.md if you adopt uv's `attribute_env_vars_metadata`.

Tests: `trybuild` compile-fail cases for the derive (missing code, bad
version); an `insta` snapshot of `frob --list-rules --format json`; a
`datatest-stable` harness over tests/rules/<CODE>/*.md Markdown fixtures
(ty's lint_docs pattern) so each rule's doc example is executed.

Why not macro_rules only (ty style): doc extraction and kebab naming are
trivial in macro_rules (`concat!`, plus a tiny `kebab_case!` proc macro),
but validating `stable_since`, collecting `format!` strings, and emitting
`inventory::submit!` with good error spans want syn. Keep both: the derive
for rules, and a `declare_rule!` macro_rules wrapper if you want the
ty-style `static` form.

Why inventory instead of a hand-written register list: frob rules will be
spread across ~6 crates (directives, ledger, strata, deps, tests, docs).
inventory costs one `ctor` per rule and nothing at runtime after init.
Fallback if you ever target wasm: a `frob-dev` generator that writes the
list, exactly like clippy's `cargo dev update_lints`.

---------------------------------------------------------------------------

## 1. How ruff / uv / ty are structured

### 1.1 Crate layout

| Repo | Layout | Count | Naming |
|---|---|---|---|
| astral-sh/ruff | `crates/*`, `resolver = "2"`, members glob | 53 dirs (ruff_*, ty_*, mdtest) | `ruff_<domain>` snake_case; shared infra `ruff_db`, `ruff_text_size`, `ruff_source_file`, `ruff_index`, `ruff_cache`, `ruff_macros`, `ruff_options_metadata`, `ruff_annotate_snippets` (vendored fork); product crates `ruff_linter`, `ruff_python_{ast,parser,semantic,formatter,codegen,trivia,stdlib,index,literal,importer,edits}`, `ruff_workspace` (config), `ruff_server` (LSP), `ruff_wasm`, bin `ruff`, dev bin `ruff_dev`, `ruff_benchmark` |
| ty (same repo) | `crates/ty_*` | 15 | `ty` (bin), `ty_project`, `ty_python_semantic` (the type checker, salsa), `ty_module_resolver`, `ty_ide`, `ty_server`, `ty_test` (mdtest runner), `ty_vendored` (typeshed), `ty_static`, `ty_combine` (+ derive Combine in ruff_macros), `ty_wasm`, `ty_site_packages`, `ty_completion_{bench,eval}` |
| astral-sh/uv | `crates/uv-*` kebab-case | 75 | `uv` (bin), `uv-cli` (clap types only), `uv-dev`, `uv-macros`, `uv-options-metadata`, `uv-settings`, `uv-workspace`, `uv-cache`, `uv-cache-key`, `uv-client`, `uv-resolver`, `uv-fs`, `uv-git`, `uv-pep440`, `uv-pep508`, `uv-small-str`, `uv-once-map`, `uv-static`, `uv-version`, `uv-warnings`, `uv-test`, ... |

Patterns:
- CLI arg types live in their own crate (`uv-cli`, `ruff::args`) so the
  doc generator can `use ruff::args::Args; Args::command()` without
  linking the whole binary logic.
- Settings structs (`ruff_workspace::options::Options`,
  `uv_settings::Options`) derive `Deserialize + JsonSchema +
  OptionsMetadata + CombineOptions`; the dev generator renders both the
  settings reference Markdown and `ruff.schema.json` from the same struct.
- `*_dev` crate is a clap binary with subcommands `generate-all`,
  `generate-json-schema`, `generate-cli-help`, `generate-docs`,
  `generate-options`, `print-ast`, `round-trip`, `repeat` (bench),
  `format-dev` (ecosystem check); aliased as `cargo dev`. uv gates it
  behind `--features dev`.
- Vendored forks when upstream is too slow: `ruff_annotate_snippets`.
- `ruff_benchmark` is separate so criterion/codspeed deps never touch the
  product build.

### 1.2 Settings metadata (uv-macros / ruff OptionsMetadata)

crates/ruff_macros/src/config.rs: `#[derive(OptionsMetadata)]` on a
struct with named fields. Each field has `#[option(default = "...",
value_type = "...", example = r#"..."#)]` or `#[option_group]` (nested
struct) or `#[serde(flatten)]`; the struct doc comment becomes the set's
documentation (dedented via ruff_python_trivia::textwrap). Output:
`impl OptionsMetadata for T { fn record(visit: &mut dyn Visit) {
visit.record_field("name", OptionField { doc, default, value_type,
example, deprecated, possible_values }) ... } fn documentation() }`.
uv's copy (crates/uv-options-metadata/src/lib.rs, uv-dev/src/
generate_options_reference.rs) adds `possible_values` and a
`CombinedOptions` struct that flattens `uv_settings::Options` and
`ToolUv` so one schema covers both `uv.toml` and `pyproject.toml`.
`generate_options.rs` sorts fields and groups by name for deterministic
output.

### 1.3 salsa usage

- ruff pins salsa to a git rev in `[workspace.dependencies]` (historically
  `salsa = { git = "https://github.com/salsa-rs/salsa.git", rev = "..." }`);
  crates.io has 0.28.5 (2026-09-24). UNCERTAIN whether ruff main is on a
  published version this month; check Cargo.toml before pinning.
- `ruff_db` defines `#[salsa::db] pub trait Db: salsa::Database` with
  files, source text, parsed module as `#[salsa::tracked]` queries;
  `#[salsa::input] File`, `#[salsa::interned]` for names/types;
  `ty_project` owns the concrete `#[salsa::db] struct ProjectDatabase`.
- Dev profile compiles salsa at `opt-level = 3`.
- Pattern to copy for frob: inputs = file contents + frob.toml + ticket
  files; tracked = parsed tree-sitter tree, extracted directives, symbol
  table per file, obligation edges per file; derived = graph queries,
  gate results. Persisting salsa memos is not supported; use your own
  on-disk cache keyed by content hash + parser identity (T-4484).

### 1.4 mdtest (markdown test corpora)

- `crates/ty_test` is the framework; `crates/mdtest` (new, 2026) is a
  generic extraction (`mdtest::{parser, matcher, attempt_test, run}`)
  reused by `crates/ruff_mdtest` to run ruff lint fixtures the same way.
- Dispatch is datatest-stable, not libtest-mimic:
  crates/ty_python_semantic/tests/mdtest.rs ends with
  `datatest_stable::harness! { { test = mdtest, root = "./resources/mdtest",
  pattern = r"\.md$" }, { test = lint_doc, root = "./resources/lint_docs",
  pattern = r"\.md$" } }` and Cargo.toml has `[[test]] name = "mdtest"
  harness = false`. One test per .md file: filterable, parallel under
  nextest.
- Format (crates/ty_test/README.md): a .md file is a suite; `#`/`##`
  headers are test names; fenced blocks ` ```py path=a/b.py ` are files in
  an in-memory filesystem; assertions are inline comments
  `# error: [rule-name] "msg"` and `# revealed: int`; a `toml` block sets
  config; snapshots of full diagnostics go to resources/mdtest/snapshots
  via insta. `MDTEST_TEST_FILTER` env var filters by test name;
  `mdtest.py` watches files.
- A thread_local one-thread rayon pool per worker avoids pool contention.

### 1.5 insta

ruff: `insta = { features = ["filters", "json", "redactions"] }`,
`insta::with_settings!({ omit_expression => true }, { assert_snapshot!(..)
})` wrapped in `ruff_linter/src/test.rs::test_snippet` helpers; CI runs
`cargo insta test --all-features --unreferenced reject --test-runner
nextest --disable-nextest-doctest`. `profile.dev.package.insta.opt-level =
3`. Snapshots live next to tests in `snapshots/`; reviewed with `cargo
insta review`.

### 1.6 CLI reference generation

crates/ruff_dev/src/generate_cli_help.rs: `ruff::args::Args::command()`
(clap `CommandFactory`), `render_long_help()` per subcommand, trim trailing
whitespace, splice between `<!-- Begin auto-generated command help. -->`
pragmas in docs/configuration.md; `--mode check` diffs. ty has
generate_ty_cli_reference.rs that walks all subcommands recursively into
crates/ty/docs/cli.md. uv does the same (uv-dev generate_cli_reference)
and also emits env var docs from the `EnvVars` impl block. Shell
completions use `clap_complete` at runtime (`ruff generate-shell-completion
bash`), not committed files.

### 1.7 Build/CI tricks (verified in Cargo.toml / CI yml)

| Trick | ruff | uv |
|---|---|---|
| dev profile | opt-level=1, debug="line-tables-only", lto="off" | debug="line-tables-only" |
| hot deps opt-level 3 in dev | insta, similar, salsa (+ruff_python_parser at 1) | none |
| release | lto="fat", codegen-units=16, cu=1 for parser/ast/salsa | strip, lto="fat", panic="abort" |
| extra profiles | profiling, fast-test, minimal-size, dist | profiling, fast-build, no-debug, *-nightly, minimal-size, dist |
| linker | CI: rui314/setup-mold; local: rust-lld default (1.90+) | same |
| tests | cargo-nextest, `.config/nextest.toml` profile ci (slow-timeout 60s, serial group for watch tests) | nextest |
| unused deps | `cargo shear --deny-warnings` | cargo shear |
| lints | `[workspace.lints]` pedantic -2 with allow list, unreachable_pub, unsafe_code | same shape |
| toolchain | rust-toolchain.toml channel pinned (1.99.0 on main), rust-version 1.97, edition 2024 | pinned |
| CARGO_INCREMENTAL | 0 in CI | 0 in CI |
| codegen | checked-in generated files + `cargo dev generate-all --mode check` | same |

---------------------------------------------------------------------------

## 2. Crate shortlist per concern

Versions: crates.io, 2026-10-01. "Pick" is the recommendation.

| Concern | Pick (version) | Alternatives | Why |
|---|---|---|---|
| CLI | clap 4.6.7 (derive) + clap_complete 4.6.11 | bpaf, argh | Industry default; `CommandFactory` enables doc generation; clap-markdown 0.1.5 (2025-05) is thin, write your own renderer like ruff. clap_mangen for man pages. |
| Config | serde + toml 1.1.6 (read) + toml_edit 0.25.15 (write, preserves comments) | figment 0.10.19 (stale since 2024-05), config | toml 1.0 (2025) shares the parser with toml_edit; figment adds layering but is unmaintained-ish. Do layering by hand with a `Combine` derive (ty_combine pattern). |
| Errors (lib) | thiserror 2.0.21 | snafu 0.9.2, error_set 0.9.2 | thiserror is the community standard. error_set gives Zig-style error unions with auto `From` between sets; nice for `Result[T, E]`-style typed errors but young (0.9, single maintainer). Try it in one crate first. |
| Errors (CLI/diagnostics) | miette 7.6.0 (fancy feature in bin only; last release 2025-04, slow) | annotate-snippets 0.12.16 (rustc's renderer, active), ariadne, codespan-reporting 0.13 | miette gives source spans, help, URLs, `#[diagnostic(code(...))]` which maps to rule codes. For gate diagnostics with many labels, annotate-snippets (what ruff vendors) renders rustc-style. anyhow only in the bin. |
| Logging | tracing 0.1.44 + tracing-subscriber 0.3.23 (fmt, env-filter, json) + tracing-appender 0.2.5 | log + env_logger | Structured JSON via `fmt().json()`; spans for gate timing; tracing-tree / tracing-indicatif for TTY; tracing-error for SpanTrace in errors. |
| Incremental | salsa 0.28.5 | custom memo + blake3 keys | Pin a version (or git rev like ruff). API: `#[salsa::db]`, `#[salsa::input]`, `#[salsa::tracked]`, `#[salsa::interned]`, `#[salsa::accumulator]` for diagnostics. Memos are in-memory only. |
| Parsing | tree-sitter 0.27.0 + per-language grammar crates | ast-grep-core 0.45.3 for pattern matching on top | Grammar crates export `LanguageFn` via tree-sitter-language 0.1.x, so grammar/core versions may differ; test every grammar at upgrade (difftastic notes 0.26.11 broke solidity). Grammars checked: python 0.25.0, rust 0.24.2, javascript 0.25.0, typescript 0.23.2, go 0.25.0, c 0.24.2, cpp 0.23.4, java 0.23.5, bash 0.25.1, yaml 0.7.2, toml-ng 0.7.0, markdown: tree-sitter-md 0.5.3 (the `tree-sitter-markdown` crate is a 2021 relic). ABI: tree-sitter 0.27 is ABI 15 and accepts 13-15; python/rust/js/go/c/bash/md are ABI 15, typescript/cpp/java/yaml/toml-ng are ABI 14; all load. |
| Structural search | ast-grep-core + ast-grep-config 0.45.3 | custom tree-sitter queries | Pattern syntax `$VAR`, YAML rules, fixes; perfect for user policy rules. Ties you to ast-grep's tree-sitter version; check it matches. |
| Git | gix 0.88.0 (gitoxide; 0.x, breaking changes often, feature-gate tightly) | git2 0.21.0 (bundles libgit2 1.9.7) | gix is pure Rust, fast, no C build, good for read paths (refs, trees, blame, status, worktrees). Some write paths (merge, rebase) are newer; keep `git` CLI shell-out for landing/merge like v1 if gix lacks something. git2 is the safe fallback. |
| Cache store | rusqlite 0.40.2 `bundled` (SQLite 3.53.2 via libsqlite3-sys 0.38.2) | redb 4.3.0, fjall 3.1.10 (sled is dead: 1.0.0-alpha.124 from 2024-10, last stable 2021) | SQLite gives ad-hoc queries (`frob graph-query`), WAL concurrency across worktrees, and a known file format. redb if you only need KV; fjall if write-heavy LSM. |
| Parallelism | rayon 1.12.0 | std threads + crossbeam | File-level parallel parse/extract; keep salsa queries single-threaded per db or use salsa's parallel support with `Snapshot`. |
| File watching | notify 8.2.0 + notify-debouncer-full 0.7.0 (9.0 still rc.5) | watchexec 8.4 | Standard; use polling fallback on WSL2 (inotify across /mnt is unreliable). |
| Hashing | blake3 1.8.7 (content), xxhash-rust 0.8.19 (xxh3, hot path), rustc-hash 2 / foldhash (maps) | sha2 | blake3 for cache keys/ids (parallel, keyed), xxh3 for in-memory. |
| Serialization | serde 1.0.229 + serde_json; cache: postcard 1.1.3 or rkyv 0.8.18 | rmp-serde 1.3, ciborium (dormant) | postcard is tiny and serde-native; rkyv zero-copy for big graphs but needs its own derives. Do NOT use bincode: 3.0.0 is a tombstone (`compile_error!`), 2.0.1 is the last working release and the project has ceased. |
| IDs | ulid 3.0.0 for draft/event ids; sequential `T-####` on landing | uuid 1.26.1 (v7 feature), svix-ksuid | ULID is 26 chars Crockford base32, lexically time-sorted, no hyphens, URL/file safe; uuid v7 is the standard alternative if other tools must parse it. Pick ULID for internal/draft ids, keep human `T-####` as the public alias (see 3.4). |
| Markdown | pulldown-cmark 0.13.4 (parse, fast, CommonMark + GFM tables/footnotes) | comrak 0.55.0 (full GFM + render + AST mutation), markdown 1.0.0 (markdown-rs, mdast) | pulldown for reading ticket bodies/docs; comrak if you need an AST you can edit and re-emit. Frontmatter: gray_matter 0.3.2 (TOML/YAML/JSON) or 20 lines of your own split. |
| YAML | serde-saphyr 1.3.0 (serde on saphyr) | yaml-rust2 0.13.0 (low level), serde_yaml_ng 0.10 (2024, stale) | serde_yaml 0.9.34 is deprecated and serde_yml 0.0.13 is a dead shim; saphyr family is the maintained lineage (saphyr 0.1.0 2026-09). Prefer TOML frontmatter anyway. |
| TOML edit | toml_edit 0.25.15 | - | Round-trips comments/order for `frob ack`-style edits to frob.toml. |
| Glob / ignore | ignore 0.4.33 + globset 0.4.20 | walkdir, jwalk | Honors .gitignore; parallel walker. |
| Templating | minijinja 2.24.0 | tera, askama (compile-time) | Jinja syntax for done-report/docs templates; askama if templates are static and you want type checking. |
| Tables / terminal | comfy-table 8.0.1, console 0.16, anstream/anstyle | tabled 0.22, ratatui 0.30 (optional TUI) | comfy-table handles wrapping/TTY width; indicatif for progress. |
| MCP server | rmcp 3.5.0 (official modelcontextprotocol/rust-sdk) | mcp-sdk-rs, mcpr | rmcp: `#[tool_router]`/`#[tool]` macros, schemars-derived tool schemas, stdio + streamable HTTP transports; requires tokio. |
| LSP (if frob gets one) | lsp-server 0.10 (rust-analyzer's sync, channel model; no tokio) | tower-lsp-server 0.23 (maintained fork; tower-lsp 0.20 is abandoned), async-lsp 0.2 | lsp-types 0.97 (2024) is stale; check the `ls-types` fork.  ruff_server/ty_server use lsp-server (sync, crossbeam); simpler with salsa. |
| Schema | schemars 1.2.2 (+ jsonschema 0.58 for validation, pin it) | - | 1.x API (`schema_for!`, `JsonSchema` derive, `#[schemars(...)]`); generate frob.schema.json and ticket.schema.json; also used by rmcp. |
| Tests | insta 1.48 + cargo-insta, rstest 0.27.0, proptest 1.11, datatest-stable 0.3.3 (md corpora), trybuild 1.0.121 (macro errors), cargo-nextest 0.9.146, assert_cmd 2.2 + assert_fs/predicates (CLI), snapbox/trycmd (CLI transcript tests) | libtest-mimic 0.8.2 (lower level than datatest) | Use datatest-stable harness for tests/mdtest/*.md exactly like ty. |
| Semver | semver 1.x, cargo_metadata 0.23 | cargo-semver-checks (binary; trustfall) | Only for `frob vet`; shell out to cargo-semver-checks rather than embedding. |
| Diffing | similar 3.2.0 | imara-diff, dissimilar | Unified/inline diffs for `--mode check` and doc drift. |
| Process | std::process + duct 1.1.2 (sync pipelines) | tokio::process (async paths only), xshell | duct for test runners/git; tokio::process inside MCP server. |
| Async | tokio 1.53.1 only in `frob-mcp` and `frob-serve` crates | smol | Core stays sync + rayon; tokio is forced by rmcp. |
| Python interop | pyo3 0.29.3 + maturin, optional crate `frob-py` | - | Only if you keep a Python API; not needed for the CLI. |
| Deterministic output | indexmap 2.14.2, serde_json `preserve_order`, BTreeMap for emitted files | - | Sorted keys + canonical emitter = clean diffs (see 3.4). |
| Paths / time / misc | camino 1.2.6 (UTF-8 paths), jiff 0.2.37 (time; civil + tz, better API than chrono), etcetera/directories (XDG), fs-err 3.3, tempfile, dashmap 6.2, petgraph 0.8.3 (graph algos), bstr, memchr, regex, compact_str/smol_str, lasso 0.7 or ustr 1.1 (interning; or salsa interned) | chrono 0.4.45, time 0.3 | camino everywhere internally (ruff/uv do); jiff for ULID timestamps and ticket dates. |
| Dev tooling | cargo-nextest, cargo-insta, cargo-shear 1.14 (astral) or cargo-machete 0.9, cargo-deny 0.19 (installed), cargo-hack (feature matrix), typos, cargo-dist or release-plz, sccache 0.18 (C grammar builds), cargo-hakari 0.9.39 (workspace-hack if feature unification causes rebuilds) | cargo-udeps (nightly) | |

Notes:
- error_set: evaluate against the typani `Result[T, E]` idiom; it maps
  well (named error sets, subset coercion) but check compile-time cost and
  miette interop (needs `Diagnostic` derive on the generated enums; UNCERTAIN
  whether error_set supports attribute pass-through for that).
- tree-sitter 0.27 vs local 0.25.10: your cached grammar crates
  (python 0.25.0, rust 0.24.2, typescript 0.23.2, cpp 0.23.4) all use
  `tree-sitter-language`, so they should load under 0.27; verify ABI
  (`LANGUAGE_VERSION` 14/15) at startup and snapshot-test each grammar.

---------------------------------------------------------------------------

## 3. Prior art: in-repo issue tracking

| System | Lang | Storage | IDs | Merge model | Format | 2026 status |
|---|---|---|---|---|---|---|
| git-bug | Go | git objects under `refs/bugs/<id>`, identities under `refs/identities/*`; nothing in the worktree | hash of first op commit, short prefix | operation log with Lamport clocks; deterministic replay, no conflicts; multi-process clock lock fix 2026-09 | JSON ops per commit | v0.11.0 2026-09-22 after 16 months; entity framework generalized |
| git-issue | sh | `.issues/<sha>/{description,comments/,tags}` in tree | SHA of creation | plain git text merge; dir-per-issue + file-per-comment makes conflicts rare | plain files | low activity |
| Radicle (heartwood) | Rust | COBs: signed commit DAG per object under `refs/cobs/<type>/<id>` per peer namespace | git OID of root commit; typed `xyz.radicle.issue` | per-type CRDT replay over the DAG (moved off automerge to custom) | JSON ops | active; 1.1.0 2024-12 |
| Fossil | C | SQLite repo; immutable ticket-change artifacts folded into a ticket table by TH1 config | artifact hash; ticket UUID = hash of first artifact | union of artifacts on sync; per-field last-writer-wins by mtime | card text | maintained |
| Jujutsu | Rust | op store + git backend | change id (stable) vs commit id (per rewrite) | operation log DAG; conflicts stored as first-class data | protobuf | active |
| git-appraise | Go | `refs/notes/devtools/*`, one JSON per line | target commit hash | `cat_sort_uniq` notes merge (append-only set) | JSONL | dormant |
| beads (bd, Yegge) | Go | moved from `.beads/issues.jsonl` to Dolt (`refs/dolt/data`); JSONL now export | `bd-a1b2` hash with growing length; hierarchical `bd-a3f8.1` | Dolt cell-level 3-way merge | SQL + JSONL | active (2026-07) |
| beads_rust | Rust | SQLite + JSONL export | bd-compatible | JSONL text merge | JSONL | exists, UNCERTAIN maturity |
| ticgit / ditz / bug / Bugs Everywhere | Ruby/Go/Py | orphan branch or `bugs/*.yaml`, `issues/*.md`, `.be/` | sha / slug / uuid | git text merge | files | dead or low activity |
| Pijul / Darcs | Rust/Haskell | patch DAG | patch hash | patch theory; commuting patches, conflicts first-class | n/a | Pijul active, small |

Lessons:
- git-bug and Radicle prove op-log + clocks is conflict-free, but the
  ledger becomes invisible to grep/diff/code review and awkward across
  worktrees and CI. Not what frob wants.
- git-issue and the surviving file-based trackers show that one directory
  per ticket with one file per event has near-zero conflicts with plain git.
- Fossil's "immutable change artifacts + derived table, rebuilt any time"
  is the model that fits: tracked files are the truth, SQLite is a cache.
- jj: separate stable identity (change id) from revision (commit id);
  record conflicts as data instead of failing.
- beads: hash ids with prefix solve multi-agent creation; a single JSONL
  file did not survive concurrent edits at scale; `bd ready` (unblocked
  work) is the query agents use -- frob already has `doable_tickets`.
- Sequential ids (PROJ-123) need a serialized allocator. Options: reserved
  ranges per worktree (gaps, bookkeeping); hash + later alias (beads);
  ULID + alias; allocation at landing on main (dense, needs reference
  rewriting). v1 already does draft -> `T-####` promotion at landing.

### 3.4 Recommendation for frob v2 ledger

- One file per ticket in tree (`tickets/T-0001.md`), Markdown body with
  TOML frontmatter (not YAML: typed, comment-preserving edits via
  toml_edit, no serde_yaml deprecation problem). Flat, sorted keys,
  canonical emitter enforced by `frob format`.
- Drafts created in worktrees: `tickets/drafts/<ulid>.md`; promotion to
  `T-####` happens only in the serialized landing step on main under a
  file lock; keep `aliases = ["01J..."]` so old references resolve.
  ULID (ulid 3.0.0) over uuid v7 because it is shorter, Crockford base32,
  case-insensitive, sortable, and safe in filenames and directive comments.
- Append-only per-ticket events as separate files
  (`tickets/T-0001/events/<ulid>.toml`) if history matters beyond git log;
  otherwise rely on git history and keep tickets single-file.
- Field-aware merge driver (`.gitattributes` + `merge.frob.driver`) for
  ticket files: scalars LWW-with-conflict, sets union with tombstones,
  status as a state machine; on failure write an explicit
  `conflict = true` field that `frob check` reports (jj lesson).
- Derived index: SQLite under `.frob/` (gitignored), keyed by
  (content blake3, schema version, parser identity); parallel scan with
  `ignore` + rayon; reparse only changed files; thousands of tickets load
  in tens of ms.
- Never use refs/notes/Dolt as the primary store.

---------------------------------------------------------------------------

## 4. Prior art: cross-language symbol identity

| Scheme | Durable string? | Path-independent? | Overloads | Locals/anon | Needs compiler? | Rust crate | Status |
|---|---|---|---|---|---|---|---|
| SCIP | yes: `scheme manager pkg version descriptors` with suffixes `/ # . (). : [] () !` | yes | method disambiguator `name(+1).` | `local N` per document (unstable) | precise indexers yes; scip-syntax no | scip 0.10.0 (2026-09-03) | active; repo moved to github.com/scip-code/scip |
| LSIF | no (int graph ids, optional monikers) | via moniker | indexer-defined | kind: local | yes | none | deprecated |
| Universal ctags | display strings (`scope:class:Foo`), JSON output | partly | no | `__anon<hash>` | no | tree-sitter-tags 0.27.0 is the analogue | active |
| tree-sitter tags.scm | flat tags (`@definition.function @name @doc`, `#strip!`, `#select-adjacent!`) | n/a | no | n/a | no | tree-sitter-tags 0.27.0 | maintained with tree-sitter |
| stack-graphs | graph, not string; TSG rules per language | n/a | no | n/a | no | tree-sitter-stack-graphs 0.10.0 (2024-12) | ARCHIVED 2025-09-09 ("no longer maintained") |
| Kythe VName | `{signature, corpus, root, path, language}`, `kythe://corpus?lang=..?path=..#sig` | no (path inside) | indexer | indexer | yes | none | low activity |
| rustdoc JSON / cargo-semver-checks | `paths[id] = ["crate","mod","Item"]` | yes | n/a | no | yes | rustdoc-types | active |
| Python qualname | `pkg.mod.Cls.method`, `<locals>`, `<lambda>` | yes | n/a | by convention | no | n/a | n/a |
| Glean / Joern / LSP DocumentSymbol | typed facts / `fullName` with signature / `containerName` | mixed | Joern yes | Joern `<lambda>0` | mostly yes | none | reference only |

scip-syntax (Sourcegraph's tree-sitter "syntactic" indexer, in the
archived sourcegraph-public-snapshot under
docker-images/syntax-highlighter/crates/{scip-syntax,syntax-analysis}) is
the closest existing design: per-language .scm with `@scope`,
`@definition.*`, `@local`; a byte-range-containment scope tree; a
descriptor stack producing SCIP symbols with package `.`; locals skipped
via a bitvec; also emits ctags. Port the idea, do not depend on the code.

### 4.1 Recommended symbol id scheme for frob v2

Be SCIP-shaped (so `frob export --scip` is mechanical via the `scip`
crate), syntactic (function of the enclosing definition chain only),
location-free (path is a hint column, not part of the key), and
deterministic.

```
symbol     = "frob" SP scope SP chain [ SP disamb ]
scope      = package | "."              ; module root; "." if unknown
chain      = descriptor { descriptor }
descriptor = name "/"                    ; namespace / module / dir
           | name "#"                    ; type: class struct enum trait interface
           | name "."                    ; term: fn const static field var
           | name "(" [ovl] ")."         ; callable, optional overload tag
           | name "!"                    ; macro
           | "[" name "]"                ; type parameter / trait-impl qualifier
           | "(" name ")"                ; parameter
           | "<" kind ":" ordinal ">" "." ; anonymous: <closure:0>. <lambda:1>.
ovl        = "~" hex8 | "+" digits       ; hash of normalized params | source-order index
disamb     = "~" hex12                   ; content-hash fallback (volatile)
name       = ident | "`" escaped "`"
```

Examples: `frob proj util/io/Foo#bar().` (Python method),
`frob proj util/Foo#new().` (Rust inherent fn),
`frob proj util/Foo#[Display]fmt().` (Rust trait impl; extension beyond
SCIP), `frob proj src/a/A#m(~3fa9c1d2).` (TS overload),
`frob proj pkg/srv/Server#Start().` (Go method, pointer receiver
stripped), `frob proj src/x/f().` (C; header and source merge by name).

Rules: emit the overload tag only when a sibling shares the name (and
always for languages with syntactic overloads: TS, Java, C++); Python
conditional redefinition uses `+N`; anonymous ordinals count siblings of
the same kind inside the nearest named scope (damage from renumbering is
confined to one function); locals get no ledger ids; re-exports get their
own id plus an `alias_of` edge, unresolved targets recorded as
`unresolved:<module>#<name>`; every row carries `path_hint` and
`body_hash` (blake3 of normalized text) so moves and edits are detected
and recorded as `id_aliases` rather than silently rewriting keys.

Node-kind -> descriptor mapping lives in per-language `.scm` files plus a
tiny capture->suffix table, so adding a language is data not code, and
each language gets snapshot tests over a fixture corpus.

Crates: tree-sitter 0.27 + grammar crates; your own QueryCursor-driven
tagger (tree-sitter-tags gives flat tags without the scope path);
`scip` 0.10.0 behind a feature for export; blake3 for hashes. Do not use
tree-sitter-stack-graphs (archived).

---------------------------------------------------------------------------

## 5. Workspace layout for fast incremental builds

### 5.1 Crates (proposal: ~22, grow only when a boundary earns it)

| Crate | Depends on | Notes |
|---|---|---|
| frob (bin) | everything | thin: parse args, build db, dispatch |
| frob-cli | clap | arg types only (uv-cli pattern) so docs gen links only this |
| frob-macros | syn, quote, heck | proc-macro; `derive(Rule)`, `derive(OptionsMetadata)`, `message_formats`, `kebab_case!` |
| frob-rules | inventory, schemars, serde | RuleMetadata/Registry/Severity/Gate enums; no heavy deps |
| frob-diagnostics | miette or annotate-snippets, frob-text (TextRange) | Diagnostic model + renderers (text, json, github, sarif) |
| frob-text | - | TextSize/TextRange/LineIndex (or depend on ruff_text_size + ruff_source_file pinned) |
| frob-db | salsa, frob-text | `#[salsa::db]` trait, File input, source text, system abstraction |
| frob-config | serde, toml, toml_edit, schemars, frob-macros | frob.toml model + OptionsMetadata + Combine |
| frob-languages | tree-sitter, grammar crates (feature-gated) | `Language` enum, `LanguageFn` table, .scm bundles via include_str |
| frob-syntax | frob-languages, frob-db | tracked parse query, symbol extraction, symbol ids (section 4) |
| frob-directives | frob-syntax | comment DSL parser (`frob:ticket`, `frob:todo`, ...) |
| frob-graph | petgraph, frob-syntax, frob-directives | obligation graph, queries, affects |
| frob-ledger | serde, toml_edit, ulid, jiff, gix | ticket files, drafts, promotion, merge driver |
| frob-gates | frob-rules, frob-graph, frob-ledger | gate implementations (one module per gate) |
| frob-strata | frob-syntax (own grammar) | .strata parser + semantic kernel (keep dir name, see T-4485) |
| frob-tests | duct, frob-graph | touched-set test selection + runners |
| frob-vet | cargo_metadata, semver | dependency vetting |
| frob-git | gix (+ git CLI fallback) | worktrees, landing, locks |
| frob-cache | rusqlite bundled, postcard/rkyv | on-disk index keyed by content+parser identity |
| frob-mcp | rmcp, tokio, frob-* | MCP server; the only tokio consumer besides serve |
| frob-dev (bin, `cargo dev`) | all + similar | generate-all (rules docs, cli docs, schema, options), print-ast, bench helpers; `publish = false` |
| frob-mdtest | datatest-stable, insta | markdown corpus runner shared by gate/strata/directive tests |
| xtask or alias | - | prefer `[alias] dev = "run -p frob-dev --"` over a separate xtask |

Boundaries that matter for rebuild locality: proc-macro crate isolated
(any change recompiles all users, so keep it tiny and stable);
tree-sitter grammars in one leaf crate so a C rebuild never cascades;
tokio only in leaf crates; test harness and dev generators out of the
product graph; `frob-rules` has no deps so rule-heavy crates do not pull
diagnostics rendering.

### 5.2 Profiles (verified against ruff/uv/zed/rust-analyzer)

```toml
[workspace]
resolver = "3"
members = ["crates/*"]

[workspace.package]
edition = "2024"
rust-version = "1.98"

[workspace.lints.rust]
unsafe_code = "warn"
unreachable_pub = "warn"
[workspace.lints.clippy]
pedantic = { level = "warn", priority = -2 }
print_stdout = "warn"      # frob logs via tracing, never print
print_stderr = "warn"
dbg_macro = "warn"

[profile.dev]
opt-level = 1                  # ruff does this; measure, drop to 0 if edit-compile suffers
debug = "line-tables-only"
lto = "off"                    # avoid implicit local thin-LTO at opt-level >= 1
split-debuginfo = "unpacked"   # zed; faster relinks on Linux
codegen-units = 16

[profile.dev.build-override]   # build.rs + proc macros (zed pattern)
opt-level = 3
debug = 0

[profile.dev.package]
salsa = { opt-level = 3 }
tree-sitter = { opt-level = 3 }
insta = { opt-level = 3 }
similar = { opt-level = 3 }
syn = { opt-level = 3 }
quote = { opt-level = 3 }
proc-macro2 = { opt-level = 3 }
rusqlite = { opt-level = 3 }
libsqlite3-sys = { opt-level = 3 }

[profile.fast-test]
inherits = "dev"
debug = 0
strip = "debuginfo"

[profile.release]
lto = "fat"
codegen-units = 1
panic = "abort"
strip = true

[profile.profiling]
inherits = "release"
debug = "full"
strip = false
lto = false
codegen-units = 16
```

```toml
# .cargo/config.toml
[alias]
dev = "run --package frob-dev --"

[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=mold"]
# rust-lld is the default since Rust 1.90 (2025-09); mold still wins on
# large links. Benchmark both with `cargo build --timings`; delete these
# two lines to fall back to lld.
```

Facts: Rust 1.90 made rust-lld default on x86_64-unknown-linux-gnu
(blog.rust-lang.org/2025/09/01/rust-lld-on-1.90.0-stable). wild
(wild-linker 0.10.0, 2026-08) is a Rust linker in the Rust Foundation
Innovation Lab, Linux only, no incremental linking yet; optional
experiment. Parallel frontend (`-Zthreads`) and cranelift
(`codegen-backend = "cranelift"`) are still nightly-only as of this date.

### 5.3 dylib in dev?

Not recommended. Bevy's `dynamic_linking` (bevy_dylib, `crate-type =
["dylib"]`, `-C prefer-dynamic`) helps a 400-crate game engine with
seconds-long links; for a CLI with mold/lld the link is well under a
second, and dylib breaks with proc macros, release parity, and rpath
handling. Measure first with `cargo build --timings`; revisit only if
link time dominates an incremental rebuild.

### 5.4 Feature gating of grammars

`frob-languages/Cargo.toml` (ast-grep pattern,
crates/language/Cargo.toml in ast-grep/ast-grep):

```toml
[features]
default = ["python", "rust", "toml", "markdown"]
all-languages = ["python", "rust", "javascript", "typescript", "go", "c",
                 "cpp", "java", "bash", "toml", "yaml", "markdown"]
python = ["dep:tree-sitter-python"]
typescript = ["dep:tree-sitter-typescript"]
# ...
[dependencies]
tree-sitter-python = { version = "0.25", optional = true }
```

Each grammar crate compiles parser.c (+ scanner.c/.cc) with `cc` in its
own build.rs; typescript (two grammars) and cpp are the largest. Use
`sccache` for cold CI builds and `all-languages` in CI/release only.
Runtime `.so` loading via tree-sitter-loader 0.27 is possible for
user-supplied grammars but adds a runtime toolchain dependency; keep it
as an optional later feature.

### 5.5 Tooling baseline

cargo-nextest (per-test process isolation, `.config/nextest.toml` with a
`serial` group for watcher/git tests, `slow-timeout`), cargo-insta
(`--unreferenced reject` in CI), cargo-shear (unused deps), cargo-deny
(licenses/advisories; already installed), cargo-hack (feature matrix for
frob-languages), rust-toolchain.toml pinned, `CARGO_INCREMENTAL=0` in CI,
`cargo dev generate-all --mode check` as a CI gate, `cargo build
--timings` before any restructuring.

---------------------------------------------------------------------------

## 6. Uncertainties to verify before committing

| Item | Why |
|---|---|
| salsa version ruff pins today (git rev vs 0.28.x) | ruff historically pins a git rev; API churn between 0.2x releases |
| error_set + miette interop | need `#[diagnostic]` pass-through on generated enums; unverified |
| tree-sitter 0.27 with 0.23-0.25 grammar crates | should work via tree-sitter-language; test each grammar |
| current tree-sitter markdown crate name (`tree-sitter-md`?) | the `tree-sitter-markdown` crate is a 2021 relic |
| ast-grep-core's pinned tree-sitter version | may drag a second tree-sitter into the graph; check before adopting |
| gix write-path coverage (merge/rebase/worktree add) | keep `git` CLI fallback for landing |
| beads_rust maturity | single-author port |
| mold vs rust-lld on this machine | measure; lld may be enough |
| biome_diagnostics 0.7.0 API stability | republished after 21 months; may lag biome main |
| Symbol-id extensions (`[Trait]`, `<closure:N>`) | not SCIP-standard; must be backtick-escaped on SCIP export |

## Sources

- ruff: https://github.com/astral-sh/ruff (crates/ruff_macros/src/{violation_metadata,map_codes,rule_namespace,derive_message_formats,config}.rs, crates/ruff_linter/src/{violation,codes,registry}.rs, crates/ruff_dev/src/{generate_all,generate_docs,generate_rules_table,generate_cli_help,generate_options,generate_ty_rules}.rs, crates/ty_python_semantic/src/lint.rs, crates/ty_python_semantic/tests/mdtest.rs, crates/ty_test/README.md, crates/mdtest, crates/ruff_mdtest, Cargo.toml)
- uv: https://github.com/astral-sh/uv (crates/uv-options-metadata/src/lib.rs, crates/uv-dev/src/generate_options_reference.rs, Cargo.toml)
- clippy: https://github.com/rust-lang/rust-clippy (declare_clippy_lint/src/lib.rs, clippy_lints/src/declared_lints.rs)
- biome: https://github.com/biomejs/biome (crates/biome_analyze/src/rule.rs, crates/biome_analyze_macros/src/lib.rs, xtask/codegen/src/)
- oxc: https://github.com/oxc-project/oxc (crates/oxc_macros/src/declare_oxc_lint.rs)
- rust-analyzer: https://github.com/rust-lang/rust-analyzer/blob/master/Cargo.toml
- zed: https://github.com/zed-industries/zed/blob/main/Cargo.toml
- bevy fast builds: https://github.com/bevyengine/bevy/blob/main/.cargo/config_fast_builds.toml
- rust-lld default: https://blog.rust-lang.org/2025/09/01/rust-lld-on-1.90.0-stable
- wild: https://github.com/davidlattimore/wild
- cargo unstable (cranelift, codegen-backend): https://doc.rust-lang.org/cargo/reference/unstable.html
- parallel frontend goal: https://rust-lang.github.io/rust-project-goals/2026/parallel-front-end.html
- ast-grep languages: https://github.com/ast-grep/ast-grep/blob/main/crates/language/Cargo.toml
- difftastic: https://github.com/Wilfred/difftastic/blob/master/Cargo.toml
- SCIP: https://github.com/scip-code/scip (scip.proto), https://crates.io/crates/scip
- scip-syntax: https://github.com/sourcegraph/sourcegraph-public-snapshot (docker-images/syntax-highlighter/crates)
- stack-graphs (archived): https://github.com/github/stack-graphs
- git-bug: https://github.com/git-bug/git-bug/releases, https://github.com/git-bug/git-bug/pull/1625
- Radicle COBs: https://radicle.dev/2024/12/05/radicle-1.1.0, https://lwn.net/Articles/966869/
- beads: https://steveyegge.github.io/beads/, https://github.com/Dicklesworthstone/beads_rust
- issues-in-repo survey: https://nesbitt.io/2026/08/20/issues-in-the-repo.html
- crates.io API for every version above: https://crates.io/api/v1/crates/<name>
