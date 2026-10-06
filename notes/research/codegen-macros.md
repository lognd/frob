# Codegen / macro / config research: mature Rust linters vs frob-v2

Date 2026-10-06. Read-only on frob-v2. All claims cite path:line@sha against shallow
clones (depth 1) taken today. Clones were deleted after the research.

SHAs: ruff (includes ty) 57a6e86 | clippy fcffb58 | rust-analyzer ce37b24 |
biome f0f82425 | oxc 80840ac | frob-v2 9ee656fba (working tree).
Abbreviations: RA = rust-analyzer, F2 = frob-v2, mr = macro_rules!.
Paths are repo-relative to the named codebase. "UNVERIFIED" = not confirmed in source.

Coverage (Phase 0 denominator): 5 clones (ruff incl. ty = 6 codebases) + frob-v2 side
(gob-macros, registry, artifact, gob-dev, GEN001, design doc 3 and 6) + 3 tickets.
All 6 external codebases and all F2 items were read; none pending, none blocked.
Depth limit: per codebase I read the declaration macro, registry, generator, and CI wiring;
I did not read every generator body (e.g. biome's 40 xtask codegen modules, oxc ast_tools).

---------------------------------------------------------------------------------------
## (a) Comparison by dimension

### 1. Rule / lint declaration

| Codebase | Macro kind | Required vs defaulted | Docs capture and enforcement | Stability / version metadata |
|---|---|---|---|---|
| ruff | proc-macro derive `ViolationMetadata` with helper attr `violation_metadata` (crates/ruff_macros/src/lib.rs:85) | REQUIRED: a status (one of stable_since/preview_since/deprecated_since/removed_since) and `category`; missing -> compile error "Missing required rule status metadata" / "...category metadata" (crates/ruff_macros/src/violation_metadata.rs:14-25). Name = struct ident. | Docs = all `///` lines concatenated (violation_metadata.rs:63-80). The macro does NOT require non-empty docs and does NOT check sections. Test `documentation` (crates/ruff_linter/src/registry.rs:485) asserts `explanation().is_some()`, but the derive always emits `Some(docs)` (violation_metadata.rs:44-46) so the check is effectively vacuous for derived rules (my inference from the two sites). Doc code blocks are formatted-checked by scripts/check_docs_formatted.py (run at .github/workflows/ci.yaml:1094). | Status is a 4-state enum with `since`; version string regex-validated at expansion: `^(v0.[0-4].\d+\|\d+\.\d+\.\d+\|NEXT_RUFF_VERSION)$` (violation_metadata.rs:157-175); placeholder is rewritten by release tooling (comment at :158-160). Naming convention test: registry.rs:496. |
| ty | `macro_rules! declare_lint` (crates/ty_python_semantic/src/lint.rs:257) | REQUIRED: >=1 `#[doc]`, `summary: literal`, `status: expr`. DEFAULTED via `..lint_metadata_defaults(status)`: `default_level = Error`, file/line filled by `file!()`/`line!()` (lint.rs:152-162, 257-281). Name = kebab-case of the static ident (`kebab_case!`, lint.rs:269). | Docs from doc comment OR `#[doc = include_str!("../resources/lint_docs/<name>.md")]` (diagnostic.rs:210-246; 141 declare_lint! sites in ty_python_semantic/src). The macro does NOT enforce the "What it does / Why is this bad / Examples" sections; the sections appear only in the rustdoc example (lint.rs:229-251). Examples in lint_docs/*.md ARE executed: mdtest root `./resources/lint_docs` with `lint_doc` test kind (crates/ty_python_semantic/tests/mdtest.rs:37,84). | `LintStatus` enum Preview/Stable/Deprecated(since,reason)/Removed(since,reason) with `since: &'static str` unvalidated (lint.rs:170-203). |
| clippy | `mr declare_clippy_lint!` wrapping `declare_tool_lint!` (declare_clippy_lint/src/lib.rs:121-150, 152+) | REQUIRED: `#[clippy::version = "..."]`, name, category ident, description literal. DEFAULTED: default level is derived from the category token (correctness->Deny, style/complexity/perf/suspicious->Warn, nursery/pedantic/cargo/restriction->Allow; lib.rs:152-260). | Docs = `#[doc]` lines captured to `LintInfo.explanation` and `location` via `file!()`/`line!()` (lib.rs:102-110,144-145). Sections are convention only (book/src/development/adding_lints.md:248); no test found enforcing "What it does". | Version string checked by an internal lint `invalid_clippy_version_attribute` (clippy_lints_internal/src/lint_without_lint_pass.rs:75, check at :208) with a UI test (tests/ui-internal/check_clippy_version_attribute.stderr). |
| rust-analyzer | None: assists/diagnostics are plain functions; docs are TAGGED COMMENT BLOCKS (`// Assist: <id>`) scraped by xtask (xtask/src/codegen.rs:50-99 CommentBlock::extract; xtask/src/codegen/assists_doc_tests.rs:102) | id must be `[a-z_]+` (assists_doc_tests.rs:108) | Format enforced at codegen time with panics: first paragraph must be a capitalised sentence ending in "." (assists_doc_tests.rs:119); `before`/`->`/`after` fenced shape (:122-127). Tidy requires module `//!` docs (xtask/src/tidy.rs:232-270). | No per-assist version/stability. |
| biome | `mr declare_lint_rule!` -> `declare_rule!` (crates/biome_analyze/src/rule.rs:984, 1068) | REQUIRED: >=1 doc line, `version`, `name`, `language`. DEFAULTED builder: recommended=false, fix_kind=None, severity=Information, sources/domains/rule_presets empty (rule.rs:870-889). | Docs = `$(#[doc])+` -> `RuleMetadata.docs`. Enforcement is OUTSIDE the macro in `cargo run -p rules_check` (xtask/rules_check/src/lib.rs:48+; CI .github/workflows/lint_rule_docs.yml:45): parses docs as markdown, runs every fenced code block as a test (`expect_diagnostic` fences, lib.rs:287-340), checks HTML validity for MDX (lib.rs:430-440), rule-specific policy (Options must not be `()` :70, issue_number only in nursery :78, tailwind domain needs a section :86). | `version` is a literal string, unvalidated in the macro (rule.rs:986). `deprecated(&str)` builder. |
| oxc | proc-macro function-like `declare_oxc_lint!` (crates/oxc_macros/src/lib.rs:118; impl crates/oxc_macros/src/declare_oxc_lint.rs:245) | REQUIRED: struct name, plugin, category, `version = "x.y.z"\|"next"` (compile error at declare_oxc_lint.rs:200-205). DEFAULTED: fix kind (none), config (none). Invalid category/fix kind PANIC in the macro (:272, :420-466). | Docs from `///`; under feature `ruledocs` only: unclosed ``` fences and missing docs are compile errors (declare_oxc_lint.rs:210-222). In the normal build docs are not required. Test that every rule with config has schema docs: crates/oxc_linter/tests/rule_configuration_documentation_test.rs (cfg ruledocs, :1-14). | `version` presence enforced (:200-205) but format not validated (parsed as an expr, :163-166). `const VERSION` emitted (:334). |
| F2 | proc-macro derive `Rule` via darling (crates/gob-macros/src/lib.rs:265, expand :147-254) | REQUIRED: id, slug, family, severity, tier, scope, fix, version (lib.rs:60-80). DEFAULTED: `polarity` -> Pplus, `must_measure` -> false, `product` -> "frob", `since` -> "2.0.0" (lib.rs:67-79, 181-184, 259-263). | Docs from `///`; compile error only if EMPTY (lib.rs:197-201). No section check. Rule pages combine meta + mdtest corpus (crates/gob-dev/src/render/rules.rs:101-135). | `since` and `version` unvalidated; id shape and slug kebab-case ARE validated (lib.rs:90-109, 151-169). Accumulated errors via darling (lib.rs:149-202). |

### 2. Registration, uniqueness, rename/redirect

| Codebase | Registry mechanism | Uniqueness guarantee | Rename / redirect |
|---|---|---|---|
| ruff | One reviewed central table: `#[ruff_macros::map_codes] pub fn code_to_rule(...)` with a big `match (Linter, "CODE") => path::Rule` (crates/ruff_linter/src/codes.rs:237-262; macro crates/ruff_macros/src/lib.rs:104). The macro consumes the function as a DSL and generates the `Rule` enum, prefixes, rule->code maps (crates/ruff_macros/src/map_codes.rs:86-135, 420-470). | Rule -> exactly one code: `assert_eq!(codes.len(), 1, ...)` PANIC at macro-expansion time = compile time (map_codes.rs:287-300). Duplicate `(linter, code)` pair: the macro inserts into a `BTreeMap` (map_codes.rs:86-95) with no explicit duplicate check that I found; the match function is not re-emitted, so rustc's unreachable-pattern lint cannot catch it. UNVERIFIED whether any test catches it. Duplicate rule struct name -> duplicate enum variant (compile error, my inference). | Separate runtime table `REDIRECTS: LazyLock<HashMap>` in crates/ruff_linter/src/rule_redirects.rs:15 (NOT part of map_codes). Test `overshadowing_redirects` fails if a live code is shadowed by a redirect (rule_redirects.rs:149-166). `RuleStatus::Removed` keeps retired rules (codes.rs:213-232). |
| ty | Manual list `register_lints(registry)` of `registry.register_lint(&LINT)` (crates/ty_python_semantic/src/types/diagnostic.rs:71+) feeding `LintRegistryBuilder`. | RUNTIME `assert_eq!(by_name.insert(..), None, "duplicate lint registration for '{name}'")` (crates/ty_python_semantic/src/lint.rs:372-378). Aliases may not point to aliases nor to unregistered lints (lint.rs:386-406). I found NO test or lint that every `declare_lint!` is in `register_lints` (grep over ty_python_semantic, ty_dev, ruff_dev): UNVERIFIED / likely absent. | First-class: `register_alias(from, to)` (lint.rs:385-408), `LintStatus::Removed` entries kept in `by_name` and answer `GetLintError::Removed` (lint.rs:430-445). |
| clippy | Generated list `declared_lints::LINTS` of `crate::mod::NAME_INFO` (clippy_lints/src/declared_lints.rs:1-8; generator clippy_dev/src/generate.rs:164-188) plus per-pass `declare_lint_pass!` lists. | clippy_dev parses sources and rejects duplicates: `emit_duplicate_lint` "duplicate lint name declared" (clippy_dev/src/parse.rs:169, diag.rs:132). Internal lint `lint_without_lint_pass` ensures every lint is in a pass (clippy_lints_internal/src/lint_without_lint_pass.rs:38). | `deprecated_lints.rs` holds DEPRECATED and RENAMED lists, GENERATED by `cargo dev` (generate.rs:57-98); the `tests/ui/deprecated.rs` and `tests/ui/rename.rs` ui tests are also generated from them (generate.rs:107-135). Edit commands: clippy_dev/src/deprecate_lint.rs, edit_lints.rs. |
| rust-analyzer | Hand-maintained `handlers::all()` array (crates/ide-assists/src/lib.rs:242+); doc-derived tests are generated. | Handled by Rust (one fn per name); id uniqueness not separately enforced that I found. | n/a |
| biome | NO hand list: proc-macro `declare_group_from_fs!` scans the group directory at compile time, one file = one rule, struct name = Pascal(file stem) (crates/biome_analyze_macros/src/lib.rs:27-30; group_macro.rs:80-137). Group/category/registry files are GENERATED by `xtask_codegen analyzer` (xtask/codegen/src/generate_analyzer.rs:116-380), marked "Generated file, do not edit by hand, see `xtask/codegen`" (crates/biome_js_analyze/src/registry.rs:1). | Filesystem uniqueness (two files cannot share a stem); empty group is a compile error (group_macro.rs:122-124). | `deprecated` builder + `sources` (eslint etc.) in metadata; `xtask/codegen/src/move_rule.rs`, `promote_rules.rs` for moves. |
| oxc | Hand module list in crates/oxc_linter/src/rules.rs (`pub mod import { pub mod default; ...}`) parsed with syn by `oxc_linter_codegen` which GENERATES `RuleEnum`, dispatch and `rule_runner_impls.rs` (tasks/linter_codegen/src/main.rs:35-60; crates/oxc_linter/src/generated/rules_enum.rs:1-2). | Rust module/type names; kebab name derived by `rule_name_converter()` (declare_oxc_lint.rs:233-235). No explicit duplicate-name check found: UNVERIFIED. | Not found (UNVERIFIED). |
| F2 | link-time `inventory`: `inventory::submit! { RuleEntry::new(&X::META) }` emitted by the derive (crates/gob-macros/src/lib.rs:250-252); `Registry::global()` iterates the inventory (crates/gob-rules/src/registry.rs:48-51). Same for config tables, commands, directives (32 inventory sites in crates/) and artifacts (crates/gob-config/src/artifact.rs:32-37). | RUNTIME-OR-TEST: `Registry::verify_unique()` returns `DuplicateId`/`DuplicateSlug` naming both declaring modules (registry.rs:83-103); called at process start by `gob_product::main` (crates/gob-product/src/lib.rs:38) and in tests (crates/gob-rules/tests/derive.rs:59-71, crates/frob-obligations/tests/repo.rs:297). | None. No alias, no removed state, no redirect table. |

### 3. Config / options metadata, schema, CLI help

| Codebase | Options metadata | JSON schema | CLI help / docs |
|---|---|---|---|
| ruff | derive `OptionsMetadata` with field attr `#[option(default=, value_type=, example=)]` (crates/ruff_macros/src/lib.rs:23; crates/ruff_workspace/src/options.rs:62-66). Missing field doc comment -> compile error "Missing documentation for field" (crates/ruff_macros/src/config.rs:167); optional `scope`, `deprecated` attrs (config.rs:191-230). | `schemars::JsonSchema` derive behind a feature (options.rs:50); generated to ruff.schema.json by `generate_json_schema` (crates/ruff_dev/src/generate_json_schema.rs:20-50); ty analogue generate_ty_schema.rs, generate_ty_options.rs. | clap derive in crates/ruff/src/args.rs; `generate_cli_help` rewrites marked regions between `<!-- Begin auto-generated ... -->` pragmas (crates/ruff_dev/src/generate_cli_help.rs:14-21). ty: generate_ty_cli_reference.rs, generate_ty_env_vars_reference.rs (via `attribute_env_vars_metadata`, ruff_macros/src/lib.rs:154). |
| ty | same `OptionsMetadata` derive over `ty_project::metadata::options::Options`; checked-in output crates/ty/docs/configuration.md with a "WARNING: auto-generated" comment (crates/ty/docs/configuration.md:1). | ty.schema.json (generate_ty_schema.rs). | crates/ty/docs/cli.md:1 header generated. |
| clippy | `mr define_Conf!` (clippy_config/src/conf.rs:76+): per-field `#[doc]`, `#[default_text]`, `#[rename]`, `#[lints(a,b)]`; deprecated fields have no type. | n/a (TOML). | book/src/lint_configuration.md regenerated by test `book` in tests/config-metadata.rs:20-50 (bless env). Cross-check test: every `#[lints(..)]` name must be a declared lint (tests/config-consistency.rs:12-26). |
| rust-analyzer | config via a hand `config.rs` macro (not read in depth: UNVERIFIED). Feature docs scraped from `// Feature:` comments (xtask/src/codegen/feature_docs.rs). | n/a | n/a |
| biome | `biome_configuration_macros` function-like macros (crates/biome_configuration_macros/src/lib.rs:10,68); rule options as generated structs in `biome_rule_options` with `schemars` feature (crates/biome_rule_options/src/no_base_to_string.rs:5); rules_check forbids `type Options = ()` (xtask/rules_check/src/lib.rs:70). | `cargo codegen-schema`, `codegen-bindings`, `codegen-configuration` aliases (.cargo/config.toml, alias block). | codegen aliases only; CLI docs on the website repo (UNVERIFIED). |
| oxc | rule config is a struct deriving `JsonSchema`, passed as `config = Type` in `declare_oxc_lint!` (declare_oxc_lint.rs:307-320 under ruledocs); schema generated to npm/oxlint/configuration_schema.json; website docs generated via `cargo run -p website_linter cli/schema-markdown` (justfile:390-394). | CI regenerates and diffs (.github/workflows/ci.yml:896-904). | as left. |
| F2 | `#[derive(ConfigTable)]` + `#[config(table=, materialize)]`, field `#[config(default=, enforcement)]`; `///` docs become generated docs; an `enforcement` field must have a default (crates/gob-macros/src/lib.rs:274-286; tests/ui/config_enforcement_no_default.rs). Verbs: `#[derive(Command)]` (lib.rs:288-300). | JSON schemas registered as `ArtifactEntry` with `ArtifactFamily::Schemas` (crates/gob-config/src/artifact.rs:5-30). | `cargo dev gen cli|config|directives|schemas` (crates/gob-dev/src/lib.rs:27-42, 69-98). |

### 4. Code generation: generator, outputs, freshness, marking

| Codebase | Generator | What is generated | Checked in? | CI freshness check | Marking |
|---|---|---|---|---|---|
| ruff | `cargo dev` alias (.cargo/config.toml:2) -> crates/ruff_dev; `generate-all` runs 8 generators (crates/ruff_dev/src/generate_all.rs:41-57) with `Mode::{Write(default),Check,DryRun}` (generate_all.rs:21-36) | ruff.schema.json, ty.schema.json, ty docs (rules.md, configuration.md, cli.md, env vars), CLI help blocks, per-rule docs (generate_docs, `--dry-run` only, NOT in a check mode: generate_docs.rs:15-20; rule docs pages are not checked in, built at docs time by scripts/generate_mkdocs.py:239-257). Python generators: crates/ruff_python_ast/generate.py, crates/ruff_python_formatter/generate.py. | yes | **CI does NOT invoke `generate-all --mode check` (no `cargo dev` in .github/workflows/ci.yaml).** Freshness is enforced by unit tests that call each generator in `Mode::Check` and run under `cargo insta test` (ci.yaml:443): test_generate_json_schema (generate_json_schema.rs:63; `RUFF_UPDATE_SCHEMA=1` flips it to Write), ty_rules_up_to_date (generate_ty_rules.rs:162), ty_configuration_markdown_up_to_date (generate_ty_options.rs:311), ty_cli_reference_is_up_to_date (generate_ty_cli_reference.rs:335), plus generate_cli_help.rs:145 and generate_ty_schema.rs:63. I found no such test for generate_ty_env_vars_reference.rs (has Check mode, no test): a gap in ruff. Python generators: CI runs them then `test -z "$(git status --porcelain)"` (ci.yaml:708-711). New-rule scaffold `scripts/add_rule.py` is compiled in CI (ci.yaml:712-718). | Markdown `<!-- WARNING: This file is auto-generated (cargo dev generate-all). ... -->` first line (crates/ty/docs/rules.md:1); `.gitattributes:27-30` marks ruff.schema.json, ty.schema.json and two generated.rs as `linguist-generated -diff`; rs file header "This is a generated file" (crates/ruff_python_ast/src/generated.rs:1). Diff output capped at 100 lines (generate_all.rs:58-80). |
| clippy | `cargo dev` alias (.cargo/config.toml:5) -> clippy_dev; `update_lints [--check]` (clippy_dev/src/main.rs:148-160); parse-based (clippy_dev/src/parse.rs) | declared_lints.rs, `mod x;` regions in lib.rs, deprecated_lints.rs, CHANGELOG link block, README lint-count, tests/ui/deprecated.rs, tests/ui/rename.rs (generate.rs:18-188) | yes | Dedicated workflow runs `cargo dev update_lints --check` and `cargo dev fmt --check` (.github/workflows/clippy_dev.yml:29-33) and also `cargo dev new_lint` scaffolding is exercised in the same workflow (:35+). Config book: test `book` fails with "run cargo bless --test config-metadata" (tests/config-metadata.rs:20-50). | Header: "This file was generated by `cargo dev update_lints`. ... do not edit by hand." (generate.rs:10-12; declared_lints.rs:1-3). Text regions delimited by begin/end comments. |
| rust-analyzer | `cargo xtask codegen [type] [--check]` alias `cargo codegen` (.cargo/config.toml alias; xtask/src/codegen.rs:17-40) | syntax kinds, AST nodes/tokens (xtask/src/codegen/grammar.rs:36-60), assist doctests (crates/ide-assists/src/tests/generated.rs), parser inline tests, feature/diagnostic docs | yes (assists/feature MANUAL not committed: assists_doc_tests.rs:56-60) | `cargo codegen --check` in main CI job on ubuntu (.github/workflows/ci.yaml:122-124). `ensure_file_contents` panics "not up-to-date" in check mode, rewrites file otherwise (xtask/src/codegen.rs:182-218). Lint-definition codegen deliberately excluded from `All` because it clones rust-lang/rust (codegen.rs:28-31); separate scheduled workflow gen-lints.yml. | Preamble "//! Generated by `cargo xtask codegen <type>`, do not edit by hand." (codegen.rs:173-178). |
| biome | `cargo codegen ...` aliases (.cargo/config.toml) / `just gen-all` (justfile:26-31) -> xtask/codegen (40+ modules incl. generate_analyzer.rs, generate_configuration.rs, generate_schema.rs, generate_bindings.rs, diagnostic_categories.rs) | group/category/registry modules, node factories, configuration, JSON schema, TS bindings, migrate tables | yes | NO fail-on-drift job found. `just ready` runs gen-all then `git diff --exit-code --quiet` locally (justfile:366-374); CI workflow `autofix.ci` re-runs codegens and COMMITS the result via autofix-ci/action (.github/workflows/autofix.yml:36-64). Rule docs verified separately by rules_check (lint_rule_docs.yml:45). | "//! Generated file, do not edit by hand, see `xtask/codegen`" (crates/biome_js_analyze/src/lint.rs:1). |
| oxc | `cargo lintgen` alias (.cargo/config.toml:13) -> tasks/linter_codegen; `just ast` -> oxc_ast_tools (justfile:141) | RuleEnum + dispatch, rule_runner_impls (node-type sets derived by static analysis of each rule), AST visitors etc. | yes | Per-area jobs regenerate then `git diff --exit-code || (echo '...run cargo lintgen...' && exit 1)`: AST at .github/workflows/ci.yml:863-868, linter at :896-904 (path-filtered by check-changes). Also `just ready` (justfile:36-46) and generic `git diff --exit-code # Must commit everything` after tests (ci.yml:38). | "// Auto-generated code, DO NOT EDIT DIRECTLY! // To regenerate: `cargo lintgen`" (crates/oxc_linter/src/generated/rules_enum.rs:1-2). |
| F2 | `cargo dev gen <kind> [--check]` (crates/gob-dev/src/main.rs:46-58; Kinds rules/directives/config/cli/schemas/all lib.rs:27-42). Pure functions of inventories (lib.rs:3-6). | rule pages + index, directive reference, config pages, CLI verb tables, schemas, registered artifacts | yes | CI step `cargo dev gen all --check` (crates/gob-dev/src/ci.rs:484; ci.yml via `cargo dev ci --step gen`); `Mode::Check` diffs (files.rs:55-110); failure message "GEN001: N of M generated files are stale" (main.rs:253). A unit test also checks, but only `Kind::Schemas` (lib.rs:160-173). Repo-local `[[check.tool]]` stage maps output to GEN001 (docs/design/build-test-ci.md:131-134). | `<!-- generated by cargo dev gen <kind>; do not edit -->` and JSON `$comment` (crates/gob-dev/src/render/mod.rs:10-32). No `.gitattributes` generated markers (only Cargo.lock: .gitattributes:9). |

### 5. Tests tied to codegen / macros

| Codebase | Macro compile-fail / expansion tests | Docs-example tests | "Every rule has X" checks |
|---|---|---|---|
| ruff | NONE found: no trybuild dep (grep of Cargo.toml), crates/ruff_macros has no tests dir. | `scripts/check_docs_formatted.py` (formats doc snippets, ci.yaml:1094). Rule doc examples are not executed as tests. | `documentation` (registry.rs:485, weak, see 1); naming convention vs disallowed list (registry.rs:496-516); code round-trip (:518+); `check_code_serialization`; fixtures per rule under crates/ruff_linter/resources/test/fixtures with insta snapshots; `cargo insta test --unreferenced reject` rejects orphan snapshots (ci.yaml:443). |
| ty | none for `declare_lint!`; unit tests on doc-prefix handling (crates/ty_python_semantic/src/lint.rs:284-321). | YES: lint docs are markdown files run as mdtests (tests/mdtest.rs:37,84; resources/lint_docs/*.md with `# error` annotations, e.g. call-non-callable.md). | none found for declared-vs-registered. |
| clippy | UI tests for internal lints: tests/ui-internal/*.rs + .stderr; `test_missing_tests` fails if a .stderr/.stdout has no .rs (tests/missing-test-files.rs:10-60). | UI test per lint (tests/ui/*.rs/.stderr/.fixed), blessed with `cargo uibless`; `cargo collect-metadata` renders docs for the website (tests/compile-test.rs:~620-700). | `config_consistency` (config options -> lints exist); `lint_without_lint_pass`; `invalid_clippy_version_attribute`. No "every lint has a ui test" test found by me (UNVERIFIED). |
| rust-analyzer | none for macros (no macros). | YES: each `// Assist:` before/after pair is turned into a generated `doctest_<id>` test (xtask/src/codegen/assists_doc_tests.rs:20-50; generated file crates/ide-assists/src/tests/generated.rs). | tidy: module docs, trailing whitespace, cov-mark pairing, `check_test_attrs`, lsp ext.rs hash vs doc (xtask/src/tidy.rs:15-60, 193-336). Tidy runs as a `#[test]` (tidy.rs:366-368). |
| biome | proc-macro crates have a few unit tests (group_macro.rs:189-205, rule_source_variant_index.rs:64,93); trybuild is used by `biome_diagnostics` (crates/biome_diagnostics/Cargo.toml:53), not by the analyzer macros. | YES, strongest: rules_check runs every ```lang,expect_diagnostic block through the real analyzer, per heading section, and fails if the diagnostic count does not match (xtask/rules_check/src/lib.rs:287-345, 416-420). | rules_check policy lints over registry metadata (Options struct, nursery issue number, severity per group, source cross-refs, lib.rs:60-130). |
| oxc | none found. | `rule_configuration_documentation_test.rs` (schema doc presence), rulegen snapshot tests (tasks/rulegen/src/snapshots). | tests/rule_configuration_test.rs. No "every rule has a test" check found (UNVERIFIED). |
| F2 | YES: trybuild compile-fail harness `t.compile_fail("tests/ui/*.rs")` (crates/gob-macros/tests/ui.rs:3-6) with 13 cases and committed .stderr (e.g. bad_polarity, bad_severity, missing_id, command_no_doc, directive_bad_order, ticket_schema_required_default). None of ruff/ty/oxc/biome-analyzer have this. | Rule pages embed mdtest corpus examples (render/rules.rs:101-135); `snapshots` guard step against pending/unreferenced insta files (crates/gob-dev/src/ci.rs:280-289, 482). | Registry-driven "every rule has an mdtest pair or fixture" is DESIGNED (docs/design/build-test-ci.md section 6 row 2) and has a ticket (01M47QTTKVRY3C52CXZBGB8V55 "Rule coverage test..."); not verified as implemented. |

### 6. Other best practices observed

| Practice | Where | F2 status |
|---|---|---|
| Scaffolding command whose output is COMPILED IN CI | ruff `scripts/add_rule.py` + `add_plugin.py` then `cargo check` (ci.yaml:712-722); clippy `cargo dev new_lint` (clippy_dev.yml:35+); biome `just new-rule`/xtask new-lintrule (justfile:169-170); oxc `cargo run -p rulegen` (justfile:277) | Not found in gob-dev (src list: ci, files, import_v1, isolation, out, publish, wheel, wheel_smoke). NEW. |
| Rule source location in metadata (`file!()`/`line!()`) used for "View source" links | ruff derive (violation_metadata.rs:51-57), ty (lint.rs:276-277), clippy `location` (declare_clippy_lint/src/lib.rs:145) | RuleMeta has `module` only (crates/gob-rules/src/meta.rs:85-115; derive lib.rs:240). NEW, small. |
| Rule docs in a separate markdown file executed as a test | ty resources/lint_docs (mdtest.rs:84) | ticket ~D3ZK8NM acceptance 4. |
| Policy tests over registry metadata | biome rules_check; clippy config-consistency | ticket 01M47QTTKVRY3C52CXZBGB8V55 (coverage) only; no policy-test ticket for config-references-rules. |
| Generated-file markers for git/review tooling | ruff .gitattributes:27-30 (`linguist-generated -diff`) | not present for docs/reference/** or schema files. NEW, small. |
| Check-mode diff truncated | ruff generate_all.rs:58-80 | in ~JMDMEKV (capped diff). |
| Generated tests derived from the registry (rename lists produce ui tests) | clippy generate.rs:107-135 | candidate under ~67J8R53 (redirect table -> generated redirect test). |
| Path-filtered regeneration jobs with an explicit "run X and commit" failure message | oxc ci.yml:896-904, ruff ci.yaml:708-711 | F2 failure message is "run `cargo dev gen all`" (main.rs:253): matches. |
| Version placeholder resolved at release | ruff NEXT_RUFF_VERSION (violation_metadata.rs:157-160), oxc `"next"` (declare_oxc_lint.rs:203) | F2 has literal `since = "2.0.0"` default; no placeholder story. Fold into ~D3ZK8NM. |

---------------------------------------------------------------------------------------
## (b) Where frob-v2 already matches or leads

1. Check mode with unified diff and a named failure code: F2 `Mode::{Write,Check}`, GEN001, "N of M stale; run cargo dev gen all" (crates/gob-dev/src/files.rs:9-16,55-110; main.rs:253) equals ruff's `generated_file_diff` + "please run generate-all" (generate_json_schema.rs:35) and is stricter in CI placement: ruff has no CI call to generate-all, F2 has an explicit `gen all --check` step (ci.rs:484).
2. Generators are pure functions of registries, with no per-rule edits in the generator (gob-dev/src/lib.rs:3-6); matches biome's proc-macro-from-fs and clippy's parse-based lists, better than ruff's central 1400-line table for maintenance.
3. Compile-fail tests for every derive: 13 trybuild cases (crates/gob-macros/tests/ui). Nobody in the sample does this for rule macros (ruff/oxc none; biome only for diagnostics macros).
4. Derive-time validation of id shape, family-prefix agreement and slug shape with accumulated spanned errors (gob-macros/src/lib.rs:151-202); ruff validates only version strings, clippy only version.
5. Duplicate id and slug detection naming both declaring modules (registry.rs:83-103) is at least as informative as ty's runtime assert (lint.rs:372-378) and stronger than ruff/oxc where I found no explicit check.
6. Unreferenced-snapshot guard (ci.rs:280-289) = ruff `--unreferenced reject` (ci.yaml:443).
7. Artifact registry (`ArtifactEntry`) so products register generated files without gob-dev naming them (artifact.rs:21-30; render/artifacts.rs): comparable to biome's per-language registries and better than ruff's hand list in generate_all.rs:41-57.
8. Design doc section 6 already schedules the ruff/ty practices (rule coverage test, snapshot-diagnostics, fix convergence).

---------------------------------------------------------------------------------------
## (c) Concrete gaps and ticket mapping

| # | Gap (evidence) | Maps to |
|---|---|---|
| G1 | `polarity` and `must_measure` silently default (gob-macros/src/lib.rs:73-76,181-184,259-263; the derive's own doc says to declare them). ruff makes status and category required (violation_metadata.rs:14-25); oxc makes `version` required (declare_oxc_lint.rs:200-205). | ~D3ZK8NM (acceptance 1). Matches the evidence. |
| G2 | `version`/`since` unvalidated (lib.rs:77-79). ruff validates by regex with a release placeholder (violation_metadata.rs:157-175). ty and oxc do NOT validate format, so ruff is the only precedent. | ~D3ZK8NM (acceptance 2). Add: accept `NEXT_FROB_VERSION`-style placeholder if releases rewrite it, otherwise plain semver. |
| G3 | Doc sections not enforced. Correction to ticket premise: ruff does NOT enforce sections in the derive, ty does NOT enforce them in `declare_lint!`; biome enforces at a separate check (rules_check) and ty runs examples as mdtests. So enforcing sections in the macro would exceed all precedents; a compile error is fine but the stronger practice is the executable example. | ~D3ZK8NM (acceptance 3, 4). Suggest: keep macro check to "summary + at least one section heading", move "has Example that runs" to a registry-driven test (like biome rules_check lib.rs:287-345). Reword the ticket's ruff/ty rationale (see (d)). |
| G4 | Registration relies on link-time inventory; `link_inventories()` anchor hack (crates/gob-dev/src/lib.rs:44-67); duplicate detection runtime/test only; no alias/removed/redirect. Best templates: ty `register_alias` + `Removed` status (lint.rs:385-445); ruff REDIRECTS + overshadow test (rule_redirects.rs:15,149); clippy generated DEPRECATED/RENAMED lists with generated ui tests (generate.rs:57-135). Note ruff's map_codes does not itself contain the redirect table (it is a separate file), so ~67J8R53's text about "map_codes ... renames go through a redirect table" blends two mechanisms. | ~67J8R53. Add acceptance: removed-status keeps ids reserved (ty), and a test that no live id is shadowed by a redirect (ruff). |
| G5 | No test that every declared rule type is linked/registered. Clippy solves it with an internal lint (lint_without_lint_pass.rs:38); ty has no such check. With inventory a type that is never linked is invisible, same problem as G4. | ~67J8R53 acceptance 1 covers crates; add "every `#[derive(Rule)]` type in source (scanned) appears in the registry" (clippy_dev parse-style source scan, parse.rs:169). |
| G6 | Generated files not all under gen: docs/reference/languages.md kept by a test; no manifest of generated files; no dry-run. ruff has DryRun (generate_all.rs:32-34), a diff cap (:58-80). Note ruff has gaps of its own: generate_docs has no check mode (generate_docs.rs:15-20) and ty env-vars has no test (see 4). | ~JMDMEKV (acceptance 1-3). Its premise "gen --check ... matches ruff's generate-all --mode check" is right as an interface but see (d) on how ruff CI actually verifies. |
| G7 | `cargo test` only checks `Kind::Schemas` freshness (gob-dev/src/lib.rs:160-173) while ruff and ty tests cover each generator in Check mode (generate_ty_rules.rs:162, etc.). Local `cargo test` therefore misses stale rule/config/cli pages until `cargo dev ci --step gen`. | NEW (small), see proposal N1. Could be folded into ~JMDMEKV. |
| G8 | No `.gitattributes` generated markers on generated outputs. ruff .gitattributes:27-30 marks generated outputs `linguist-generated -diff`, which collapses them in review. | NEW, see N2. |
| G9 | No new-rule scaffold exercised in CI. ruff add_rule.py (ci.yaml:712-718) and clippy new_lint (clippy_dev.yml) prove the scaffold still compiles after macro changes, which protects exactly the macro changes G1-G3 introduce. | NEW, see N3. |
| G10 | RuleMeta lacks source file/line for "View source" links on rule pages (meta.rs:85-115). ruff/ty/clippy all capture `file!()`/`line!()` in the metadata. | NEW (tiny), fold into ~D3ZK8NM or N3; see N4. |
| G11 | Config-to-rule cross-validation: clippy's config-consistency test (tests/config-consistency.rs:12-26) fails when a config option names a lint that does not exist. UNVERIFIED whether F2 config tables reference rule ids and whether anything validates them. | NEW only if F2 config references rule ids; see N5 (conditional). |

### Proposed new tickets

N1 (task, low) "gob-dev: per-kind GEN001 freshness tests in cargo test". Replace the single `Kind::Schemas` check in
crates/gob-dev/src/lib.rs:160-173 with one test per Kind (rules, directives, config, cli, schemas, registered artifacts)
that calls `generate` + `apply(.., Mode::Check)` and fails with the capped diff, the way ruff's per-generator
`*_up_to_date` tests do (crates/ruff_dev/src/generate_ty_rules.rs:162). Keep `cargo dev gen all --check` as the CI step.
Acceptance: editing a rule doc comment without regenerating fails `cargo test -p gob-dev` naming the stale path;
each Kind has a test; a test enumerates `Kind` variants so a new Kind without a test fails.

N2 (task, low) "Mark generated files in .gitattributes". Emit (or check via GEN001) `linguist-generated=true -diff`
entries for every path the artifact registry and gob-dev renderers produce (docs/reference/rules/*.md,
schemas, cli/config pages), modelled on ruff .gitattributes:27-30. Best done as a derived block written by
`cargo dev gen` (generated-files manifest from ~JMDMEKV supplies the list), so it cannot drift. Acceptance: a new
registered artifact appears in .gitattributes after `cargo dev gen all`; GEN001 fails if the block is stale.

N3 (task, medium) "cargo dev new-rule scaffold, compiled in CI". Add `cargo dev new-rule --id COV007 --slug ...
--family COV` that writes the rule struct with ALL required attributes (polarity, must_measure, version, since) and a
doc skeleton with the required sections, the mdtest corpus file (crates/*/tests/mdtest/<id>.md), and the registration
touchpoints, modelled on ruff scripts/add_rule.py and clippy `cargo dev new_lint`. CI step: run the scaffold into a temp
copy and `cargo check` + run the new mdtest (ruff ci.yaml:712-718). Acceptance: scaffold output passes trybuild-style
build with the tightened derive from ~D3ZK8NM; CI fails if the scaffold stops compiling. Depends on ~D3ZK8NM.

N4 (task, low) "RuleMeta: capture file and line". Add `file: file!()` and `line: line!()` to the derive expansion
(gob-macros/src/lib.rs:222-241) and RuleMeta (gob-rules/src/meta.rs), render a "View source" link on rule pages
(gob-dev/src/render/rules.rs), as ruff does (violation_metadata.rs:51-57; generate_docs.rs:66-72). Acceptance: rule page
links to the declaring file and line; a snapshot test pins one page. (May be folded into ~D3ZK8NM.)

N5 (conditional, low) "Config-references-rules consistency test". If any ConfigTable field or frob.toml section names
rule ids/slugs, add a registry-driven test that every referenced id/slug exists or redirects, as clippy does
(tests/config-consistency.rs:12-26). Verify first that F2 has such references; otherwise drop with a reason.

---------------------------------------------------------------------------------------
## (d) Your earlier claims versus the source

1. "ruff's derive(ViolationMetadata) takes docs from the doc comment and requires stability metadata."
   CONFIRMED with detail: docs come from `///` lines (crates/ruff_macros/src/violation_metadata.rs:63-80);
   status (stable_since/preview_since/deprecated_since/removed_since) AND `category` are both required
   (violation_metadata.rs:14-25); versions are regex-validated (:157-175). BUT the macro does not require docs to be
   non-empty or sectioned, and the `documentation` test (registry.rs:485) is effectively vacuous because the derive emits
   `Some(docs)` unconditionally (violation_metadata.rs:44-46). Ticket ~D3ZK8NM's "docs from the doc comment, required
   stability metadata" is accurate; do not read it as precedent for section enforcement.

2. "ruff's codes.rs uses a map_codes attribute giving compile-time unique codes and has a redirect table."
   PARTLY CONTRADICTED.
   - Attribute: yes (crates/ruff_linter/src/codes.rs:237, macro lib.rs:104). The function is a DSL carrier; the macro
     generates the Rule enum and code maps and does not re-emit the match.
   - "compile-time unique codes": only rule -> single code is asserted at macro time (map_codes.rs:287-300).
     Duplicate `(linter, code)` pairs go into a BTreeMap (map_codes.rs:86-95) with no explicit duplicate error that I found
     (UNVERIFIED whether any test catches it).
   - "has a redirect table": the redirect table is NOT in codes.rs or map_codes; it is a separate runtime
     `LazyLock<HashMap>` in crates/ruff_linter/src/rule_redirects.rs:15, guarded by a unit test (:149).
     Ticket ~67J8R53 describes them as one mechanism; split them.

3. "ty declares lints with a declare_lint! macro_rules whose docs need fixed sections and are rendered to a rules page."
   PARTLY CONTRADICTED. `declare_lint!` is macro_rules (crates/ty_python_semantic/src/lint.rs:257) and docs are
   rendered to crates/ty/docs/rules.md (generate_ty_rules.rs:23-60). But "need fixed sections" is NOT enforced: the
   macro only requires >=1 `#[doc]`, a summary and a status (lint.rs:258-269); the What it does / Why is this bad /
   Examples sections appear only in the doc example of the macro (lint.rs:229-251) and in the markdown files by
   convention. What ty does enforce is that the Examples in resources/lint_docs/*.md run as mdtests
   (tests/mdtest.rs:37,84). Also notable: ty registration is a manual list with runtime duplicate asserts (lint.rs:372-378),
   plus aliases and removed lints, which is the better template for ~67J8R53.

4. "ruff_dev generate-all --mode check is how CI verifies generated files."
   CONTRADICTED. `generate-all --mode check` exists (crates/ruff_dev/src/generate_all.rs:21-36) but nothing in
   .github/workflows/ci.yaml invokes `cargo dev` (grep returned no match). CI verifies freshness through
   per-generator unit tests that call `main(Mode::Check)`, run by `cargo insta test` (ci.yaml:443): e.g.
   generate_json_schema.rs:63, generate_ty_rules.rs:162, generate_ty_options.rs:311, generate_ty_cli_reference.rs:335,
   generate_cli_help.rs:145, generate_ty_schema.rs:63. Python generators are verified by running them and
   `test -z "$(git status --porcelain)"` (ci.yaml:708-711). Also: generate_docs (per-rule pages) has no check mode and
   generate-all does not include generate_rules_table/default_rules/options (generate_all.rs:41-57).
   Ticket ~JMDMEKV says "our gen with --check and GEN001 matches ruff's cargo dev generate-all --mode check":
   true for the CLI shape, but the CI mechanism is tests (hence N1).

Other observations that touch the tickets:
- ~D3ZK8NM scope lists `crates/*/src/**` for migrating rules; the macro edit can stay in gob-macros if
  polarity/must_measure are required, because every existing rule must then name them (grep of `#[rule(` sites needed;
  not done here).
- ~JMDMEKV acceptance 2 ("--dry-run prints a capped diff and writes nothing"): ruff's DryRun prints the generated CONTENT
  to stdout (generate_json_schema.rs:26-28) and Check prints the capped diff (generate_all.rs:58); the ticket merges the two.
  Decide which you want; the capped diff belongs to Check mode (F2 `apply` already prints the full diff, files.rs:75-84).

Not verified (UNVERIFIED list): RA config macro and per-assist uniqueness checks; oxc/RA duplicate-name checks;
clippy "every lint has a ui test" check; whether a test catches duplicate `(linter, code)` in ruff; biome CLI help
generation (lives outside this repo); whether F2 ConfigTable references rule ids (N5); whether F2 `crates/*/src/**`
rules all already set polarity/must_measure.
