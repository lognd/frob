# Reusing existing linters in frob: research, 2026-10-08

## Honesty block

- Scope: research only. No repository was modified, no ticket filed. Nothing was built, installed or run:
  every compile-cost, speed and behaviour statement is from fetched documentation or metadata, not measured.
- Fetched sources: 108 table rows (ids S1-S99 plus letter-suffixed companions; S78 unused; all fetched 2026-10-08 with curl, WebFetch or the
  GitHub / crates.io / npm registry JSON APIs). A claim carries its source id in brackets.
- [unsourced] items: 14 topics (43 inline tags), collected in section 7. None supports a
  recommendation on its own.
- Repo facts (docs/design/rules.md section 4, plugins.md, language-engines.md, cohesion.md section 2,
  notes/research/lint-catalogue-2026-10-08.md, crates/gob-check/src/tools.rs, tool_parse.rs) were read from
  the local checkout this session; they are cited as [repo:file].
- "Today" is 2026-10-08. Versions quoted are the latest at fetch time and will drift.

## 0. What frob has today (repo, read-only)

- Tool stages are `[[check.tool]]` entries that run through the gob-exec job pool with a `parser` and an id
  map; findings carry the frob id plus `source_rule`; native suppression hides the finding before frob sees
  it (EXC017 flags unmatched native suppressions); a stage with no evidence is TOOL001 Unresolved
  `tool-failed` [repo:rules.md s4].
- Only two parsers exist: zizmor and actionlint (`parse_zizmor`, `parse_actionlint` in tool_parse.rs) [repo].
  The catalogue lists the missing enablers: N01 SARIF 2.1.0 parser, N02 cargo JSON (clippy, rustc), N03 ruff
  JSON, N04 ESLint JSON, N16 precision ledger [repo:lint-catalogue, enablers line E1-E5].
- D96 puts language facts in gob-* over tree-sitter (tree-sitter 0.27.0, ast-grep-core 0.45.3 pinned, D42)
  [repo:language-engines.md, README D42]. D119 says a checker is a bound tool and "frob never implements a
  type checker; it consumes one" [repo:cohesion.md s2.2].
- Note the catalogue's own bind rows already depend on tool structured output (ruff, clippy, ESLint, Roslyn,
  stylelint, typos, cargo-semver-checks) [repo:lint-catalogue].

## 1. Aggregators: how they solve the six problems

Matrix. "Config ownership" = who owns the tool's native config file. Evidence ids after each cell.

| Tool | Tool versions | Config ownership | Caching | Output normalisation | Dedup | Changed-lines gating | Fixes |
|---|---|---|---|---|---|---|---|
| qlty (Rust CLI, BSL 1.1) | Plugin def has `latest_version`, `known_good_version`, `known_bad_versions`, `version_command`; runtime (python, node) + `package` installed by qlty [S81,S82] | Plugin lists `config_files` (e.g. `ruff.toml`) and can `copy_configs_into_tool_install`; own `.qlty/qlty.toml` [S80,S82] | `cache_results` per driver, `affects_cache`, `--no-cache` [S82,S83] | One Rust parser per tool (ruff, eslint, clippy, mypy, tsc, sarif, rdjson, lsp ...) in qlty-check/src/parser [S84] | not documented in fetched sources [unsourced] | `--upstream <ref>`, "Git-aware: focus on newly introduced issues", `--sample N`, `--all` [S83,S80] | `--fix`, `--unsafe`, tool and AI fixes; formatter driver `output = "rewrite"` [S83,S81] |
| Trunk Check (closed CLI, MIT plugin repo) | Hermetic: downloads and installs tools into `$HOME/.cache/trunk`, `known_good_version`, per-command `version: ">=0.6.0"` ranges [S85,S86,S89] | `lint.definitions` + repo configs; tools managed by Trunk [S85] | Content-addressed tool cache plus `trunk cache prune/clean` [S86] | `output:` kinds (sarif, regex, ...); custom `parser.run` script (python or node) turns tool output into SARIF-like input; ruff plugin runs `ruff_to_sarif.py` [S85,S87] | not documented in fetched sources [unsourced] | `--upstream` "branch used to compute changed files"; "hold-the-line" hides existing issues; `--show-existing` reveals them [S88] | `format` command `output: rewrite` [S85] |
| MegaLinter (AGPL-3.0) | Docker image per flavor, pinned by image tag [S90] | Per-linter config files in repo + env vars [S90] | not documented in fetched sources [unsourced] | Reporters incl. SARIF, GitHub/GitLab comments [S90] | not documented [unsourced] | not documented in fetched README [unsourced] | "apply fixes" to branch or provide in reports [S90] |
| super-linter (MIT) | Container image; `linterVersions.txt` lists versions per image; immutable full tags [S91] | `*_FILE_NAME` variables point at the tool's own config (e.g. `.hadolint.yaml`) [S91] | n/a | Text output; no normalisation in the fetched README [S91] | n/a | `VALIDATE_ALL_CODEBASE` toggle [unsourced: only the option name was seen via grep context, not its text] | `FIX_<LINTER>` flags per linter (FIX_BIOME_LINT, FIX_CSHARP ...) [S91] |
| reviewdog (MIT) | None: runs on tool output you produce [S92] | None | n/a | `errorformat` (Vim) patterns, rdjson, SARIF input: "can support any tool output with ease" [S92] | n/a | `-filter-mode`: `added` (default), `diff_context`, `file`, `nofilter` [S92] | Suggestions via rdjson; reporters differ in filter support (table in README) [S92] |
| pre-commit (MIT) | Each hook repo pinned by `rev`; env built per hook, reused; `additional_dependencies`, `language_version`, `minimum_pre_commit_version` [S93] | Hook reads the tool's own config | Environment cache ("Once installed this environment will be reused") [S93] | None (exit code and text); `pass_filenames`, `require_serial` [S93] | n/a | `--from-ref/--to-ref` changed files; `--files`, `--all-files` [S93] | Hooks edit files; `--show-diff-on-failure` [S93] |
| lefthook (MIT, Go) | None: "single dependency-free binary", runs commands you configure [S94] | Yours | none | none | none | Controls files passed to commands [S94] | via your command |
| Bazel rules_lint (Apache-2.0) | Bazel pins tools hermetically; linters declared as aspects [S95] | "Honors the same configuration files you use outside Bazel" [S95] | Bazel actions: Remote Cache and Remote Execution [S95] | Reports as files per target; Aspect CLI collects them [S95] | n/a | "Can lint changes only", Water Leak Principle [S95] | Linters produce fixes as patches, shown as suggested edits [S95] |
| SonarQube Server / SonarLint | Own analyzers; external tools via import [S96] | Quality profiles on server | server-side incremental analysis (nav title "Managing incremental analysis mechanisms") [S96] | Generic issue import format and SARIF import for external analyzers [S96] | n/a | New-code period / PR analysis (nav: pull request analysis) [S96] | not applicable to imports [unsourced] |
| Semgrep (LGPL-2.1; core is OCaml) | CLI binary | rules YAML | n/a | `--json`, `--sarif`, `--emacs`, ... [S53] | n/a | `--baseline-commit`: "only show results that are not found in this commit" [S53] | `--autofix`, "experimental ... data loss can occur" [S53] |
| Codacy | Legacy `codacy-analysis-cli` (AGPL-3.0) ran tools in Docker with Java 8+; README now says legacy, use CLI v2 [S97] | "your configuration files or your settings saved on Codacy" [S97] | n/a | uploads results [S97] | n/a | n/a | n/a |
| Danger (MIT) | not a linter runner | Dangerfile code | n/a | PR comments | n/a | PR-diff-scoped by design ("runs during CI, ... code review chores") [S98] | n/a |

What this says about the problem as a whole:

1. Tool versions. Every serious aggregator pins. qlty and Trunk keep the pin as data next to the tool
   definition and install the tool themselves (runtime + package) [S81,S85,S86]. Trunk goes further and
   supports multiple command variants selected by version range because CLIs change flags across versions
   (ruff `--format` became `--output-format` at 0.1.0, columns 1-indexed at 0.0.266) [S85]. This is exactly
   the version-drift risk frob has, and frob already has `version_args` and a version-range check in
   tool_parse.rs [repo].
2. Config ownership. No aggregator rewrites the tool's own config; they point at it (`config_files`,
   `*_FILE_NAME`, "honors the same configuration files") [S82,S91,S95]. qlty can copy configs into the tool
   install [S82]. Recommendation: frob owns only the stage definition and the id map, never the tool config.
3. Caching. Two layers: a tool cache (install once, keyed by version; Trunk [S86], pre-commit [S93]) and a
   result cache keyed by inputs (qlty `cache_results`, `affects_cache` [S82]; Bazel remote cache [S95]).
   frob's shared sqlite cache keyed by content digests [repo:rules.md s4] fits the second layer directly.
4. Normalisation. Two schools: write a native parser per tool in the host language (qlty: 30+ Rust parsers
   [S84]) or normalise to one interchange format (Trunk uses SARIF as the internal target and ships python
   converter scripts [S85,S87]; reviewdog uses rdjson/errorformat [S92]; Sonar takes generic or SARIF [S96]).
   Native Rust parsers are the pattern that matches frob (tool_parse.rs) and avoid a Python/Node runtime for
   the parsers themselves.
5. Dedup. None of the fetched primary sources documents cross-tool deduplication [unsourced]; treat it as a
   frob-owned problem (section 6).
6. Changed-lines gating. Three flavours: file-level via git ref (pre-commit `--from-ref` [S93], qlty/Trunk
   `--upstream` [S83,S88]), line-level on added lines (reviewdog `-filter-mode added` [S92]), and baseline
   comparison by result identity (Semgrep `--baseline-commit` [S53], Trunk hold-the-line [S88]). frob's
   delta/baseline/ratchet (rules.md s6) already covers the third; the missing piece is mapping tool
   findings to added lines.
7. Fixes. All delegate to the tool's own fixer with a safe/unsafe split (qlty `--unsafe` [S83], ruff
   `--unsafe-fixes` [S7], oxlint `--fix`/`--fix-suggestions`/`--fix-dangerously` [S29], Biome `--unsafe`
   [S34]). Super-linter makes fixing opt-in per linter [S91].

Ideas for frob to copy, ranked (top 5 repeated in the final report):

1. Plugin definitions as data (qlty plugin.toml, Trunk plugin.yaml): runtime, package, pinned and known-good
   version, version command, driver script with `${target}`, success/no-issue/error exit codes, output
   format, batch, file types, config files [S81,S82,S85]. Fits packs.md; the data crate can ship in the
   binary and be overridden per repo.
2. Hermetic tool download with known-good pin and a version-range-keyed command variant (Trunk) [S85,S86].
3. One interchange format at the boundary: SARIF 2.1.0 parser first (oxlint, Biome, golangci-lint, Roslyn
   ErrorLog, ESLint via formatter all emit it: S21,S34,S60,S57,S64), plus native JSON parsers for the
   non-SARIF tools (ruff, clippy, pyright, mypy).
4. Baseline / upstream comparison: hide pre-existing findings by identity, `--show-existing` to reveal
   (Trunk hold-the-line [S88]; Semgrep baseline [S53]; qlty `--upstream` [S83]).
5. Per-driver exit-code classes (`success_codes`, `no_issue_codes`, `error_codes`) so "violations found"
   is distinguished from "tool crashed" [S82]; frob's TOOL001 already does this per parser, qlty shows the
   data-driven form.
6. Result cache keyed by tool version plus config digest (`affects_cache`) [S82].
7. `--sample N` to onboard a new rule set by trying it on N files first [S83].

Things not to copy: Docker-image-as-version-pin (MegaLinter, super-linter [S90,S91]) fights frob's
sub-second scoped run and Windows story; AGPL/BSL code cannot be embedded in an MIT workspace (qlty is BSL
1.1 [S80], MegaLinter and codacy-analysis-cli AGPL-3.0 [S99]); data formats and ideas are fine to learn from,
code is not.

## 2. Embeddable Rust linters and parsers

Publication and stability facts, from crates.io JSON and each repo's own files.

| Tool / crates | Published on crates.io? | API stability and cadence | Licence | Compile cost proxy (direct non-optional deps; NOT measured) | Verdict |
|---|---|---|---|---|---|
| ruff: `ruff_linter` 0.16.10, `ruff_python_parser` 0.0.16, `ruff_python_ast` 0.0.16, `ruff_python_semantic` 0.0.16, `ruff_db` | Yes, but only since 2026-06-23 (crate `created_at`), first real version 0.15.19 on 2026-06-24 [S1,S2]. All described "This is an internal component crate of Ruff" [S1] | Weekly releases [S1]. Docs: only `ruff`, `ruff_linter`, `ruff_wasm` follow Ruff's version scheme and "The Rust interfaces of these crates do not follow semantic versioning"; all others "provide no stability guarantees" and are `0.0.x` [S6]. Parser README: "The Rust API exposed here is unstable and will have frequent breaking changes" [S5]. Maintainer on publishing: "big disclaimers that the crates could change at any time" [S4] | MIT [S1] | ruff_linter 52, ruff_python_parser 16, ruff_python_ast 13 [S10,S1] | Linter: subprocess (JSON). Parser/AST: not now; embed only if a Python-specific fact needs it, exact-pinned (see section 6) |
| ty: `ty_python_semantic` 0.0.16 (+ `ty_python_core`, `ty_module_resolver`, `ty_site_packages`, `ty_combine`, `ty_vendored`, `ty_static`) | Yes since 2026-06-24 [S1,S3]. `ty_ide`, `ty_project`, `ty_server`, `ty` itself are `publish = false` [S2,S3,S18]. "red_knot" crate names do not exist on crates.io (404 for `red_knot_python_semantic`) [S1]; history of rename not sourced [unsourced] | Same ruff policy: no stability guarantees [S6]. The CLI is `0.0.x`: "ty does not yet have a stable API; breaking changes, including changes to diagnostics, may occur between any two versions"; latest 0.0.85, 2026-10-06, five releases in three weeks [S11,S16]. It does expose `HasType::inferred_type` on a `SemanticModel` (per-expression types) [S17] | MIT [S1,S99] | ty_python_semantic 37 direct deps, plus ruff_db and salsa [S1] | Subprocess / LSP for now. In-process would need frob to rebuild project discovery and config that live in unpublished `ty_project` [S18]; revisit when ty leaves 0.0.x |
| Oxc: `oxc_parser`, `oxc_semantic`, `oxc` 0.153.0 | Yes; 8.3M downloads (parser), 214 versions, created 2023-03-30, last 2026-10-05 [S19]. `oxc_linter` and `oxlint` are NOT on crates.io (404) and are `publish = false` in the repo [S19,S20] | 0.x, frequent breaking bumps expected (214 versions) [S19]. Documented as libraries: oxc_parser README and oxc_semantic README describe symbol tables, scope tree, control-flow graph [S20b]. Oxlint's own semver policy covers CLI and config, not the Rust crates [S24] | MIT [S19,S99] | oxc_parser 15, oxc_semantic 15 [S19] | oxlint: subprocess. oxc_parser/oxc_semantic: the only plausible in-process JS/TS facts engine; not adopted now because D96 already commits to tree-sitter (see 6.3) |
| Biome: `biome_js_parser`, `biome_analyze`, `biome_js_analyze` | Stale: last crates.io version 0.5.7 on 2024-03-12; repo has `publish = false` on `biome_js_analyze` [S32,S33]. `biome_cli` not on crates.io [S32] | Not offered as a library | MIT OR Apache-2.0 [S32,S99] | n/a | Neither (embed); subprocess optional (section 5) |
| swc: `swc_ecma_parser` 46.0.0, `swc_ecma_ast` 29.0.2 | Yes; 732 versions, last 2026-10-06 [S40] | Major version bumps nearly every release (46.0.0) [S40]; a parser and transform toolkit, not a linter | Apache-2.0 [S40] | 12 deps (parser) [S40] | Neither: no lint rules, churn higher than Oxc |
| rust-analyzer: `ra_ap_hir`, `ra_ap_ide`, `ra_ap_syntax` 0.0.357 | Yes, weekly (299 versions of ra_ap_syntax) [S41] | Repo `ide` crate is `version = "0.0.0"`; architecture doc marks `syntax`, `hir`, `ide` as "API Boundary" but says nothing about semver [S42,S43]; `ra_ap_*` are mirrors of those [S41] | MIT OR Apache-2.0 [S41] | `ra_ap_ide` 27 direct deps (and it pulls the rest of the workspace) [S41] | Neither for now. Only candidate for Rust-language type facts for D119; costs a huge dependency tree. Rust types for D119 can come from `cargo check --message-format=json` + rustdoc JSON later [S49,S50,S56] |
| clippy | `clippy` crate stale at 0.0.302 (2018-10-05); `clippy_lints` 0.0.212 on crates.io is 2018 [S44]; repo `clippy_lints` is 0.1.101 and `clippy_utils` "only guaranteed to build with" `nightly-2026-10-01` [S46,S47,S45b] | Requires rustc_private on a pinned nightly (rust-toolchain components include `rustc-dev`) [S46]; `clippy-driver` is the non-cargo entry [S45] | MIT OR Apache-2.0 [S45b] | needs a compiler | Subprocess only: `cargo clippy --message-format=json` [S45,S50] |
| ast-grep: `ast-grep-core` 0.45.3 | Yes; 182 versions, last 2026-08-31, MIT [S51] | 0.x, docs link "guide/introduction" only [S51]. Already adopted: D42 pins it as "compatible" with tree-sitter 0.27.0 [repo:README D42] | MIT | 3 direct deps [S51] | Embed (already decided, gob-pattern) |
| tree-sitter 0.27.0 | Yes, 44M downloads, MIT [S52] | Pure-C11 runtime "can be embedded in any application" [S52b] | MIT | small | Embed (already) |
| Semgrep | Not a Rust crate. Core is OCaml (20.6 MB OCaml vs 428 MB C in GitHub language stats, the C being vendored parsers) [S54]; LGPL-2.1 [S54] | n/a | LGPL-2.1 | n/a | Neither embed. Subprocess only if a user binds it (it emits `--json` / `--sarif` [S53]) |

Corrections to the owner's phrasing: "oxidized versions" exist and ARE the answer for JavaScript (Oxc),
but the lint engines (`oxc_linter`, Biome's analyzer) are deliberately not published as libraries [S19,S20,
S33]; the "can we hook into the ruff and ty crates" answer is "technically yes since June 2026, with an
explicit no-stability contract" [S1,S2,S3,S6].

## 3. Structured output per tool

Table. Sources in brackets. "-" means the fetched docs say nothing [unsourced].

| Tool | Machine formats | Exit codes | Version probe | Config discovery | Native suppression | Fix |
|---|---|---|---|---|---|---|
| ruff 0.16.10 | `json`, `json-lines`, `junit`, `github`, `gitlab`, `pylint`, `azure`, `rdjson`; no SARIF value in `DiagnosticFormat` [S8,S9] | 0 clean or all fixed, 1 violations, 2 abnormal; `--exit-zero`, `--exit-non-zero-on-fix` [S7] | `ruff version` (qlty plugin) [S81] | `ruff.toml`, `pyproject.toml` [S81,S8] | `# noqa: F841`, `# ruff: noqa`, block `# ruff: disable[CODE]` / `enable` [S7] | `--fix` safe; `--unsafe-fixes` for unsafe; `lint.fixable/unfixable` [S7] |
| ty 0.0.85 | `full`, `concise`, `gitlab`, `github`, `junit` (no JSON, no SARIF) [S12] | 0 none, 1 warning-or-higher, 2 invalid CLI/config/IO, 101 internal; `--exit-zero`, `--error-on-warning` [S13] | `ty version` (text or json) [S12] | `ty.toml`, `--config KEY=VALUE`, `--python` [S12] | `ty: ignore` comments (`--add-ignore` adds them) [S12] | `--add-ignore` only; no rule fixes documented here [S12] |
| pyright 1.1.414 | `--outputjson` (generalDiagnostics with file, severity error/warning/information, message, rule, range) [S65] | 0 none, 1 errors, 2 fatal, 3 config unreadable, 4 bad CLI [S65] | `--version` [S65] | `pyrightconfig.json` or `pyproject.toml`, `-p` [S65] | `# type: ignore`, `# pyright: ignore[rule,...]`; `reportUnnecessaryTypeIgnoreComment` [S66] | none |
| mypy 2.4.0 | `-O json` / `--output json` [S70] | - [unsourced] | `-V/--version` [S70] | `mypy.ini`, `.mypy.ini`, `pyproject.toml`, `setup.cfg` [S70] | `# type: ignore[code]` [S74] | none; `dmypy suggest` drafts signatures (experimental) [S69] |
| tsc (TypeScript 7.0.2) | text diagnostics (`--pretty` toggle) [S61b]; no JSON format flag in the compiler-options page [S61b] | - [unsourced] | `--version` [S61b] | `tsconfig.json`, `--showConfig` [S61b] | - [unsourced] | none |
| oxlint 1.87.0 | `default`, `agent`, `checkstyle`, `github`, `gitlab`, `json`, `junit`, `sarif` (2.1.0), `stylish`, `unix` [S21,S22] | `--deny-warnings`, `--max-warnings` change status; numbers - [unsourced] [S22] | `-V, --version` [S22] | `.oxlintrc.json` / `oxlint.config.ts`; `@oxlint/migrate` ports ESLint flat config [S23,S28] | `eslint-disable`-style and oxlint inline comments (page 404 on fetch for the oxlint-specific syntax) [unsourced] | `--fix`, `--fix-suggestions`, `--fix-dangerously` [S29] |
| ESLint | `stylish` (default), `json`, `json-with-metadata`, `html` built in [S61]; SARIF via third-party `@microsoft/eslint-formatter-sarif` 3.1.0 (MIT) [S64] | exit 2 on fatal error (flag text) [S62]; 0/1 - [unsourced] | `-v, --version` [S62] | flat config `eslint.config.js` (example in formatters doc), `--print-config` [S61,S62] | `// eslint-disable-line`, `eslint-disable-next-line rule`, block comments; `--report-unused-disable-directives` [S62,S63] | `--fix` [unsourced: not seen in fetched excerpt] |
| Biome 2.5.15 | `--reporter=`: `default`, `concise`, `summary`, `json`, `json-pretty` (experimental, may change in patch releases), `github`, `gitlab`, `junit`, `checkstyle`, `rdjson`, `sarif`; repeatable with `--reporter-file` [S34] | `--error-on-warnings`; numbers - [unsourced] [S34] | - [unsourced] | `biome.json`; `biome migrate eslint` reads legacy and flat config [S37] | `// biome-ignore lint/group/rule: reason`, `biome-ignore-all`, `-start/-end` ranges [S35] | `--write/--fix` safe; `--unsafe` [S34] |
| clippy / rustc | `--message-format=json` (cargo) / `--error-format=json` (rustc), one JSON object per line, `$message_type` field, spans with `suggested_replacement` and `suggestion_applicability` such as `MachineApplicable` [S49,S50] | non-zero on denied lints, `-D clippy::perf` [S48]; precise codes - [unsourced] | `cargo clippy --version` [unsourced] | `clippy.toml`, `Cargo.toml [lints]` [S48 mentions clippy.toml only by grep context: unsourced] | `#[allow(clippy::x)]`, `-A clippy::x` ("generous sprinkling of #[allow(..)]") [S48] | `cargo clippy --fix` [S48] |
| cargo-semver-checks 0.51.0 | text; reads rustdoc JSON (unstable format, supports a range of format versions) [S56] | 0 ok, 100 deny-level SemVer violation, 101 could not complete [S56] | - [unsourced] | `--baseline-version`, `--baseline-rev` etc. [S56] | - [unsourced] | none |
| Roslyn analyzers (dotnet build) | `ErrorLog` writes SARIF; versions 1, 2, 2.1 (default 1) [S57] | build exit - [unsourced] | `dotnet --version` [unsourced] | `.editorconfig` / ruleset [S57 mentions ruleset only] | `#pragma warning disable`, `[SuppressMessage]`, `DiagnosticSuppressor` API used by Microsoft.Unity.Analyzers [S58] | `dotnet format` [unsourced] |
| Microsoft.Unity.Analyzers | rides on Roslyn ErrorLog (SARIF); NuGet package and in-box with Visual Studio; needs .NET 10 to build [S58] | as Roslyn | NuGet version | - | `DiagnosticSuppressor` (USP ids) [S58] | - |
| stylelint | `--formatter` (json etc.), `--fix`, `--compute-edit-info` [S59] | 1 fatal, 2 lint problem, 64 bad CLI, 78 bad config file [S59] | `--version` [unsourced] | stylelint config; `--config` [S59] | `/* stylelint-disable ... */` [S59] | `--fix` [S59] |
| golangci-lint | `text`, `json`, `tab`, `html`, `checkstyle`, `code-climate`, `junit-xml`, `teamcity`, `sarif`, each with a path (stdout, stderr or file) [S60] | `issues-exit-code` default 1 [S60] | - [unsourced] | `.golangci.yml` [S60] | `//nolint` [unsourced] | `--fix` [unsourced] |
| typos 1.51.1 | `--format json` = JSON lines; exit 0 no errors, 2 typos, other = error [S55] | as left | - [unsourced] | `_typos.toml` / `typos.toml` [S55 reference] | `extend-ignore-*` config; inline `typos:ignore` - [unsourced] | `--write-changes` [unsourced: seen only as grep line] |

Cross-cutting observations:

- SARIF 2.1.0 is available directly from oxlint [S21], Biome [S34], golangci-lint [S60], Roslyn [S57] and
  (via a MIT formatter) ESLint [S64]. It is NOT available from ruff [S9], ty [S12], pyright [S65] or
  mypy [S70]; those four need native JSON parsers (ruff json, pyright outputjson, mypy json) or the
  GitLab / JUnit forms. Priority order for the parser enablers: N01 SARIF, N03 ruff JSON, then pyright
  JSON, mypy JSON, N02 cargo JSON.
- Exit codes are not uniform: ruff exits 1 when it finds violations, pyright 1 on errors only, ty 1 on
  warnings and above, cargo-semver-checks 100/101, stylelint 2 for problems, typos 2 for typos [S7,S65,S13,
  S56,S59,S55]. This is the reason tool_parse.rs declares per-parser "normal" statuses; each new parser
  must carry its table.
- Native suppression syntax differs for every tool (`noqa`, `# pyright: ignore`, `ty: ignore`,
  `eslint-disable`, `biome-ignore`, `#[allow]`), so EXC017 needs one scanner pattern per bound tool; the
  data-driven plugin definition (section 1, idea 1) should hold that pattern.

## 4. Type facts for D119: realistic sources of resolved types per site

D119 asks for a checker-exact type per site under whole-program closure, or a flag for provenance
[repo:cohesion.md s2.1-2.2]. The candidates, with what each really returns:

### 4.1 Python

| Source | Interface | What you get | Granularity / cost | Stability |
|---|---|---|---|---|
| mypy daemon `dmypy inspect` | CLI: `dmypy inspect path/file.py:line:col[:end_line:end_col]`, `--show type|attrs|definition`, `--include-span`, `--include-kind`, `--limit`, `--force-reload`, `-v` for verbosity [S71]; server side `cmd_inspect` returns a dict and errors unless a `check` has run [S72]; `--export-types` on `check/recheck/run` keeps expression types in memory "to speed up future calls" (more memory) [S69] | A type STRING per expression (or all enclosing expressions at a point), via `InspectionEngine.get_type` [S72,S73]; if the type is unknown it returns an error message instead, flagged False [S73] | One query per location; position-only queries return all enclosing expressions, which is a cheap way to batch by line. Needs a prior `dmypy check` of the project | mypy 2.4.0 docs [S69]; the daemon's documented experimental parts are following imports and `suggest` [S69]; `inspect` is documented only in the client help text [S71] |
| pyright | No type-dump CLI. `--outputjson` has `information` severity diagnostics [S65]; `reveal_type(expr)` is documented as a typing construct [S75b] (that `reveal_type` surfaces as an information diagnostic in JSON is [unsourced]); `--verifytypes` checks public API completeness of a package only [S65]. Language server provides hover with type info [S67] | LSP hover returns markdown strings; reveal_type needs source edits | per-site LSP request, or per-file source rewriting | pyright 1.1.414 weekly [S68]; Node required [S76b] |
| ty | `ty server` over stdio [S12]; LSP features hover ("see its type") and inlay hints for unannotated variables [S14]; `reveal_type` in checks [S15]; no JSON type dump in the CLI [S12]. In-process: `HasType::inferred_type` in unpublished-API surface of `ty_python_semantic` [S17] | hover markdown; `textDocument/inlayHint` returns hints for a whole range in ONE request (LSP 3.17 method exists [S79]) | one process, no Node, fast | `0.0.x`, "breaking changes ... may occur between any two versions" [S11] |
| ruff | No type information (lint only; its `ruff_python_semantic` is name binding, not types) | n/a | n/a | n/a |

D119 strictness: pyright `strict` and mypy `--strict` exist; ty "has no strict flag" [repo:cohesion.md s2.2]
(ty rules are levelled, config reference [S12]).

Recommendation, Python: bind ONE checker per repo as D119 already says, and use an LSP client for the
fact fetch.
- Primary: ty over LSP (`ty server`), exact-version pinned, because it is a single native binary (no Node
  or Python runtime), supports hover and range-wide inlay hints [S14], and the same LSP client code serves
  TypeScript. Treat every ty answer as `provenance = checker` only when the closure condition holds, else
  annotation-grade. Because ty is `0.0.x` with diagnostics and behaviour changing between any two versions
  [S11], the pack must carry a fidelity corpus and the version pin (packs.md already has the mechanism)
  and a version bump must fail closed into Unresolved, not silently change answers.
- Fallback / alternative for repos that already run mypy: `dmypy inspect` over `--export-types` [S69,S71].
  It is the only one with a documented, purpose-built "type at location" command, strings are mypy's own
  `format_type` text [S73] so a normaliser to frob's type-term is required. Cost: one daemon, N queries.
- Do not use pyright's CLI for per-site types (no dump; would require rewriting source with reveal_type).
- Not measured: latency for any of these. A spike (one ticket) should time 1,000 sites on the owner's
  platform repo for ty hover vs inlayHint vs dmypy inspect before committing.

### 4.2 TypeScript

State of the world (decisive): TypeScript 7.0 is the native port, released 2026-07-08, 10x faster, and
"does not ship with an API"; "We expect TypeScript 7.1 to ship with a new (and different) API" [S75].
The `typescript@7.0.2` npm package exposes only `tsc` in `bin` and exports under `./unstable/*`
(`unstable/ast`, `unstable/sync`, `unstable/async`, `unstable/proto`) [S77]. `typescript@6.0.3` still has
`main = ./lib/typescript.js` and `tsc` + `tsserver` bins [S77b]. A compatibility package
`@typescript/typescript6` re-exports the 6.0 API for tools like typescript-eslint [S75]. The typescript-go
README lists "API: not ready" and "Language service (LSP): in progress, nearly all features implemented"
[S76]. The compiler-API wiki page says: "describe[s] TypeScript 6.0 and earlier. TypeScript 7.1 will have a
completely different API" [S76c]; `getTypeAtLocation(node)` and `typeToString(type)` are the documented
primitives [S76c].

| Source | What you get | Cost | Stability |
|---|---|---|---|
| TS 6.0 compiler API via `@typescript/typescript6`, driven by a small Node helper that walks the nodes frob asks for (`getTypeChecker().getTypeAtLocation` + `typeToString`) [S75,S76c] | exact checker types for arbitrary nodes in one process and one program build; JSON out | Node required; one program build per run (type-check cost of project) | Mature API, but explicitly end-of-life as the TS 7.1 API will replace it [S76c] |
| TS 7 language server over LSP (hover, inlayHint) [S75,S76] | hover markdown; inlay hints for ranges | native binary, no Node for TS itself; start command not captured [unsourced] | LSP "in progress" per typescript-go README (which also says the repo is closed and moves to microsoft/TypeScript) [S76] |
| tsserver (TS <= 6) quickinfo | the same as editors use | Node | being superseded [S75,S77b]; protocol file path moved so not re-verified [unsourced] |
| tsc diagnostics | errors only, no types [S61b] | | |
| typescript-eslint type-aware rules, or oxlint `--type-aware` (tsgolint) | rule findings that already used the types; 59 of 61 typescript-eslint type-aware rules [S23,S30] | oxlint-tsgolint extra npm package, Go binary on typescript-go | "Type-aware linting" is explicitly exempt from oxlint semver [S24] |

Recommendation, TypeScript: for D119 now, run a pinned Node helper on `@typescript/typescript6` (TS
6.0 API) that answers a batch of (file, span) -> type string / "any" flag in one JSON round trip, behind the
same `TypeFactSource` trait as the Python LSP client. Plan the swap to the TS 7.1 API when it ships (the
exact API is unknown today [S75]). The LSP route for TS 7 is the long-term candidate once its language
service is out of "in progress" [S76]. For findings that merely need type-aware rules (floating promises,
unsafe any), do not rebuild: bind oxlint `--type-aware` or typescript-eslint and consume their findings [S23].

### 4.3 Comparison summary

| | Python | TypeScript |
|---|---|---|
| Recommended now | ty via `ty server` LSP (pinned) | Node helper on `@typescript/typescript6` |
| Alternative | `dmypy inspect` (mypy repos) | TS 7 LSP once stable |
| Output | hover markdown or inlay-hint labels / type strings | `typeToString` strings |
| Main risk | ty 0.0.x churn [S11] | TS 7.1 API replacing 6.0 [S75] |
| Unmeasured | latency per 1,000 sites | same |

## 5. JavaScript / TypeScript default binding: oxlint vs Biome vs ESLint

Evidence matrix.

| Axis | oxlint 1.87.0 | Biome 2.5.15 | ESLint (flat config) |
|---|---|---|---|
| react-hooks | `rules-of-hooks` and `exhaustive-deps` present; plus `set-state-in-effect`, `set-state-in-render`, `rule-suppression` (v1.79.0 rules, mirroring React Compiler lints) [S25]; blog banner "Announcing React Compiler Support" 2026-08-18 [S21 page chrome] | React domain exists (`useExhaustiveDependencies`, hook rules not captured here) [S36b: domains page lists a React domain with activation, dependencies and rules; rule names unsourced] | eslint-plugin-react-hooks (the canonical implementation; catalogue W02 [repo]) |
| jsx-a11y | 36 rule files under `rules/jsx_a11y` in the repo; rules list shows `alt-text`, `anchor-is-valid`, `aria-activedescendant-has-tabindex`, etc. [S25,S26] | HTML accessibility added in v2.4 per blog index [S36b] | eslint-plugin-jsx-a11y (catalogue W01 [repo]) |
| TypeScript type-aware | `--type-aware` via `tsgolint` (typescript-go): 59 of 61 typescript-eslint type-aware rules [S23,S30]; exempt from semver [S24] | Biotype: own type inference without the TS compiler; `noFloatingPromises` "detects floating promises in about 75% of the cases that would be detected by using typescript-eslint" (June 2025 claim) [S36] | typescript-eslint, needs the TS API (TS 6 compat package or wait for 7.1) [S75] |
| Speed | claimed 10-20x faster than ESLint + typescript-eslint for type-aware (tsgolint README benchmark claim) [S30]; not measured here | "fraction of the performance impact" claim [S36] | JS, `--concurrency` multithreading option exists [S62] |
| Node dependency | Binary delivered through npm per-platform packages incl. `win32-x64-msvc`, `win32-arm64-msvc`; type-aware adds `oxlint-tsgolint` npm package [S31,S23]; Node only needed to run npm/JS plugins (JS plugins alpha [S27]) | per-platform binary packages (`@biomejs/cli-win32-x64` etc.) [S38] | Node required (npm package) [S62] |
| ESLint config compatibility | `@oxlint/migrate` converts ESLint v9/v10 flat config; keeps severities, options, overrides [S28]; JS plugin API "compatible with ESLint v9+", alpha [S27] | `biome migrate eslint --write` reads legacy and flat config, follows extends [S37]; not the same rule semantics | native |
| Windows | win32 x64/arm64/ia32 binaries [S31] | win32 x64/arm64 binaries [S38] | via Node |
| Output formats | json, sarif, github, gitlab, junit, checkstyle, unix, stylish, agent [S22] | json (experimental), sarif, rdjson, github, gitlab, junit, checkstyle [S34] | json, json-with-metadata, html, stylish; SARIF third-party [S61,S64] |
| Fixes | safe / suggestions / dangerous tiers [S29] | `--write` safe, `--unsafe` [S34] | `--fix` |
| Semver policy | CLI, config, renamed/removed rules are breaking; new rules and default changes are not; nursery, JS plugins, type-aware exempt [S24] | json reporters experimental [S34]; policy page not fetched [unsourced] | stable |
| Release cadence | 1.87.0 current [S31] (oxc crates weekly-ish [S19]) | 2.5.15 on 2026-09-30, patch releases every 1-2 weeks [S39] | n/a |
| Scope | linter only (formatter is Oxfmt, separate) [S21 nav] | linter + formatter + assists in one binary [S34,S37] | linter |

Recommendation (default JS/TS binding): oxlint, with ESLint as the escape hatch.
- oxlint covers the catalogue's heaviest JS bind rows with one native binary: W01 jsx-a11y (36 rule files
  [S26]), W02 react-hooks (rules-of-hooks, exhaustive-deps and the new compiler-style rules [S25]), and K17/K23
  type-aware rules through `--type-aware` (59/61 [S23]). It emits SARIF 2.1.0 [S21], so frob needs no oxlint-
  specific parser if N01 (SARIF) exists; an oxlint JSON parser is a second option [S21].
- Biome is the right choice only when the repo already uses Biome (migration path both ways exists
  [S37]); it also formats, but its type-aware rules are self-built inference with an admitted ~75% recall
  on one rule [S36]. Bind it as an alternative profile with its SARIF reporter [S34].
- ESLint stays supported for repos with ESLint-only plugins (oxlint JS plugins are alpha [S27]); bind with
  `-f json` (built-in) via N04, or the MIT SARIF formatter [S61,S64].
- Do not make type-aware lint a gate by default: it is exempt from oxlint's semver promise [S24] and needs
  an extra package [S23]; keep it as an opt-in profile with the precision ledger (N16).
- Risk: oxlint rule parity gaps vs ESLint are not enumerated in a source I fetched [unsourced]; the
  migration page says "Stay on ESLint if a specific missing behavior still blocks migration" [S28].

## 6. Boundary statement, in-process justifications, and risks

### 6.1 Proposed boundary statement (one paragraph, for the design)

frob does not re-implement language-specific lint rules that a maintained community tool already ships; it
binds them. A rule is native to frob (gob/grimble/crunk, running in-process over U) only when it is
architectural, cross-file, cross-language, ticket- or evidence-bound, or needs a fact the tools cannot give
(for example reachability over the resolved graph, layering, PAIR, taint, DUP, GRL packs). Every other
single-language rule (unused imports, idiom, naming, formatting, typos, a11y, hooks, correctness groups) is
a bound tool stage: frob selects the tool, pins its version, discovers but never rewrites its native config,
runs it as a subprocess through gob-exec, parses SARIF 2.1.0 or the tool's JSON natively, maps its rule ids
to frob ids with `source_rule` retained, and applies baseline, ratchet, severity, exceptions and the report
uniformly. Tools are subprocesses, not linked libraries: the Rust crates of ruff and ty are published only
with a no-stability contract and Oxc's and Biome's lint engines are unpublished, so the process boundary is
the only API with a compatibility promise (stable CLI plus structured output). A tool's fixer owns its fixes
(frob orchestrates them as fix tier A/B, never re-implements them), and a tool's own suppression comment
stays the tool's, audited by EXC017.

### 6.2 Where in-process embedding IS justified

Embedding is justified only for facts about what is written that every product needs and that a subprocess
cannot give at the speed or granularity frob needs (rules.md s4 target: warm scoped run under 1s):
1. Language facts for universal rules: syntax, scopes, imports, calls, markup, style (D96) via tree-sitter +
   ast-grep-core, both stable-enough, MIT, small [S51,S52,repo:D42]. Already decided.
2. Pattern matching for declarative rules: ast-grep-core (3 direct deps) [S51].
3. Machine formats: SARIF types. `serde-sarif` 0.8.0 (MIT, 2.8M downloads, last 2025-05-09) exists
   [S99b]; writing a small parser for the fields frob needs may be cheaper than depending on a possibly
   stale crate (decision for the N01 ticket).
4. Candidate, not recommended now: `oxc_parser` + `oxc_semantic` for exact JS/TS scope resolution if the
   tree-sitter adapter cannot meet Must/May honesty on scopes [S19,S20b]. Gate: a spike showing tree-sitter
   scope resolution is wrong on the owner's TSX repo, plus an exact version pin and an upgrade ticket per
   Oxc release (214 versions so far, weekly [S19]).
5. Candidate, not recommended now: `ruff_python_parser` / `ruff_python_ast` for Python parse fidelity (full
   expression AST incl. f-strings and match) [S5]; gate and pinning as above. The ruff linter and ty
   semantic crates are not embed candidates [S6,S18].

### 6.3 Why not embed the linters (summary)

Ruff and ty crates exist since 2026-06 with `0.0.x` and "no stability guarantees" [S1,S6]; ty's IDE and
project layers are unpublished [S18]; oxc_linter is `publish = false` [S20]; Biome's analyzer is
`publish = false` and the published copy is from March 2024 [S32,S33]; clippy needs a pinned nightly
`rustc-dev` [S46]. Embedding would fuse frob's release train to weekly breaking churn and enlarge the
build (ruff_linter alone has 52 direct dependencies [S10]).

### 6.4 Risks and mitigations

| Risk | Evidence | Mitigation |
|---|---|---|
| Duplicate findings (two tools or tool + frob native rule say the same thing: ruff F401 and a frob DEAD rule; ruff + pyright; oxlint + ESLint) | No aggregator source documents dedup [unsourced]; Trunk and qlty do per-tool presentation [S84,S85] | One owner per catalogue row (the "Owner (own or bind)" column already does this [repo:lint-catalogue]); frob id map is many-to-one so equal ids on the same span collapse; cross-tool collapse key = (frob id, file, span, normalised message hash); refuse to enable two bound tools for the same frob id unless declared `alias` |
| Version drift (flag renames, JSON field changes, rule renames) | ruff flag history in Trunk plugin (`--format` -> `--output-format`) [S85]; ty "breaking changes, including diagnostics" [S11]; rustdoc JSON unstable [S56]; Biome json reporter experimental [S34]; oxlint type-aware exempt from semver [S24] | Pin exact versions in the stage; `version_args` probe + range check (exists [repo:tools.rs]); per-parser fixture corpus (golden JSON per tool version) run in CI; unknown version or unparsable output -> TOOL001 Unresolved (exists); optional Trunk-style version-range command variants [S85]; nightly canary job against `latest` |
| Fix ownership (two fixers, conflicting edits; unsafe fixes) | Safe/unsafe tiers exist per tool [S7,S29,S34]; qlty makes unsafe opt-in [S83]; super-linter fixes opt-in per linter [S91] | The tool owns its fixes; frob never merges edits across tools; apply one tool at a time in a deterministic order inside tier B (apply, re-run, verify); safe-only by default, unsafe only on explicit `--fix-all`; formatter last |
| Missing Node / .NET / Python / Go toolchains | pyright and ESLint need Node [S76b,S62]; Roslyn needs .NET [S58]; ruff/ty are native binaries (ty via `uvx` or standalone installer [S11]); oxlint ships per-platform binaries [S31]; Trunk and qlty install runtimes themselves [S81,S86] | Prefer native-binary tools as defaults (ruff, ty, oxlint, Biome, typos, clippy); declare the runtime in the stage; missing binary -> TOOL001 (required) unless `optional = true` (exists [repo:rules.md s4]); optional hermetic download of native binaries later (copy qlty/Trunk) rather than requiring system installs |
| Windows | oxlint and Biome ship win32 packages [S31,S38]; qlty documents Windows support [S80]; ruff/ty - [unsourced]; dmypy on Windows [unsourced]; shell quoting / path separators in `${target}` | Never go through a shell (gob-exec already spawns directly); normalise paths in parsers (PATH family); a Windows leg in CI for each bound-tool fixture; avoid designs that need a Unix daemon socket (dmypy) as the only type route |
| Tool output not covering the diff (whole-file findings in changed files) | reviewdog filter modes show the trade-off [S92] | Implement `added` and `file` filter modes in the tool stage post-processor; default to baseline-by-identity (rules.md s6) |
| Suppression fragmentation | each tool has its own syntax (section 3) | Table of native-suppression patterns in the stage definition; EXC017 reads it |
| Licence contamination | qlty BSL 1.1, MegaLinter/codacy AGPL-3.0, Semgrep LGPL-2.1 [S80,S99] | Learn formats and ideas only; invoke GPL-family tools only as subprocesses at the user's choice |
| Type-fact source breaks (ty 0.0.x, TS 7.1 API change) | [S11,S75] | `TypeFactSource` trait, per-language, pin + fidelity corpus; failure yields `Unknown(reason=checker-unavailable)` never a guess (honesty theorem) |

### 6.5 Suggested next tickets (not filed; research only)

1. N01 SARIF 2.1.0 parser first (unlocks oxlint, Biome, golangci-lint, Roslyn, ESLint formatter) [S21,S34,
   S57,S60,S64]; then N03 ruff JSON, pyright JSON, mypy JSON, N02 cargo JSON.
2. Data-driven tool definitions (plugin.toml analogue) with version ranges, exit-code classes and the
   native-suppression pattern.
3. Spike: ty LSP vs dmypy inspect vs TS-6 helper latency on 1,000 sites; decide `TypeFactSource`.
4. Spike: tree-sitter vs oxc_semantic scope accuracy on the owner's TSX repo.
5. Decision record: ruff/ty/oxc crates are subprocess-only until ty leaves `0.0.x` and Oxc publishes a lint
   engine; revisit on those two events.

## 7. [unsourced] register (14)

1. qlty cross-tool dedup behaviour.
2. Trunk dedup behaviour.
3. MegaLinter caching, dedup and diff-only behaviour.
4. super-linter `VALIDATE_ALL_CODEBASE` semantics (name seen, text not).
5. Sonar fix semantics for imported issues.
6. pyright `reveal_type` appearing as an `information` diagnostic in `--outputjson`.
7. mypy exit codes; tsc exit codes and suppression syntax.
8. oxlint inline-ignore syntax page (404) and numeric exit codes.
9. Biome version probe, exit codes, and react-hook rule names.
10. clippy exit-code numbers and `clippy.toml` discovery text; Roslyn build exit codes; Roslyn `dotnet format`.
11. golangci-lint `//nolint` and `--fix`; typos inline ignore and `--write-changes`; ESLint `--fix` text.
12. TS 7 language-server start command; tsserver protocol location in TS 7.
13. ruff / ty / dmypy Windows support statements.
14. History of the `red_knot` to `ty` rename (only the crates.io absence of `red_knot_python_semantic` was
    fetched).

## 8. Sources (all fetched 2026-10-08)

Format: id | URL | title / publisher / date | claim supported. Ids with a letter suffix (S20b etc.) are a
second document under the same id family. "n/d" = no date shown.

| id | URL | Title, publisher, date | Supports |
|---|---|---|---|
| S1 | https://crates.io/api/v1/crates/ruff_linter (and /ruff_python_parser, /ruff_python_ast, /ruff_python_semantic, /ty_python_semantic, /ruff_db, /ruff, /red_knot_python_semantic, /ty) | crates.io API JSON, 2026-10-08 | versions, created_at 2026-06-23/24, MIT, description "internal component crate of Ruff"; red_knot crate 404; 0.0.x numbering; `/dependencies` endpoints for direct-dep counts |
| S2 | https://github.com/astral-sh/ruff/pull/26271 (API) | "Publish Ruff crates to crates.io", astral-sh, 2026-06-23 | 32 packages published; remaining ty_* excluded |
| S3 | https://github.com/astral-sh/ruff/pull/26323 (API) | "[ty] Publish semantic crates to crates.io", astral-sh, 2026-06-24 | ty_python_semantic, ty_python_core, ty_vendored, ty_combine publishable |
| S4 | https://github.com/astral-sh/ruff/issues/17970 (API + comments) | "Ruff as a rust crate / API?", 2025-05-08; MichaReiser comment 2025-05-09 | maintainer would publish "with big disclaimers that the crates could change at any time" |
| S5 | https://raw.githubusercontent.com/astral-sh/ruff/main/crates/ruff_python_parser/README.md | ruff_python_parser README, astral-sh, n/d | "unstable and will have frequent breaking changes" |
| S6 | https://docs.astral.sh/ruff/versioning/ | Versioning (crate versioning policy), Astral, n/d | ruff/ruff_linter/ruff_wasm not semver; others no stability guarantees |
| S7 | https://docs.astral.sh/ruff/linter/ | The Ruff Linter, Astral, n/d | exit codes 0/1/2, safe/unsafe fixes, noqa forms |
| S8 | https://docs.astral.sh/ruff/settings/ | Settings, Astral, n/d | `output-format` value list; config files |
| S9 | https://raw.githubusercontent.com/astral-sh/ruff/main/crates/ruff_db/src/diagnostic/render.rs | ruff_db render.rs, astral-sh, n/d | DiagnosticFormat variants (json, json_lines, rdjson, pylint, junit, gitlab, github, azure, concise, full); no sarif |
| S10 | https://raw.githubusercontent.com/astral-sh/ruff/main/crates/ruff_linter/Cargo.toml | ruff_linter Cargo.toml, astral-sh, n/d | dependency list |
| S11 | https://raw.githubusercontent.com/astral-sh/ty/main/README.md | ty README, Astral, n/d | beta, 0.0.x, breaking changes incl. diagnostics, uvx install |
| S12 | https://docs.astral.sh/ty/reference/cli/ | ty CLI reference, Astral, 2026-10-06 | formats full/concise/gitlab/github/junit; `ty server`, `ty version`, `--config`, `--add-ignore`; no type dump |
| S13 | https://docs.astral.sh/ty/reference/exit-codes/ | ty Exit codes, Astral, 2026-10-06 | 0/1/2/101 |
| S14 | https://docs.astral.sh/ty/features/language-server/ | ty Language server, Astral, n/d | hover and inlay hints |
| S15 | https://docs.astral.sh/ty/reference/typing-faq/ | ty Typing FAQ, Astral, n/d | `reveal_type` usage, Unknown/Todo types |
| S16 | https://api.github.com/repos/astral-sh/ty/releases | ty releases, GitHub, latest 0.0.85 2026-10-06 | release cadence |
| S17 | https://raw.githubusercontent.com/astral-sh/ruff/main/crates/ty_python_semantic/src/semantic_model.rs | semantic_model.rs, astral-sh, n/d | `HasType::inferred_type`, `SemanticModel` |
| S18 | https://raw.githubusercontent.com/astral-sh/ruff/main/crates/ty_ide/Cargo.toml and .../ty_project/Cargo.toml | Cargo.toml, astral-sh, n/d | `publish = false` |
| S19 | https://crates.io/api/v1/crates/oxc_parser (and oxc_semantic, oxc, oxc_linter, oxlint) | crates.io API JSON, 2026-10-08 | versions 0.153.0, 214 versions, MIT; oxc_linter/oxlint 404 |
| S20 | https://raw.githubusercontent.com/oxc-project/oxc/main/crates/oxc_linter/Cargo.toml (and apps/oxlint/Cargo.toml, crates/oxc_parser/Cargo.toml) | Cargo.toml, oxc-project, n/d | oxc_linter/oxlint `publish = false`; oxc_parser `publish = true` |
| S20b | https://raw.githubusercontent.com/oxc-project/oxc/main/crates/oxc_parser/README.md and crates/oxc_semantic/README.md | READMEs, oxc-project, n/d | parser and semantic are documented libraries |
| S21 | https://oxc.rs/docs/guide/usage/linter/output-formats.html | Output formats, VoidZero / Oxc, n/d (page chrome 2026-08-18 banner) | json, sarif 2.1.0, github, gitlab, junit, unix |
| S22 | https://oxc.rs/docs/guide/usage/linter/cli.html | CLI reference, Oxc, n/d | `--format` values, `--version`, `--deny-warnings` |
| S23 | https://oxc.rs/docs/guide/usage/linter/type-aware.html | Type-aware linting, Oxc, n/d | tsgolint, 59 of 61, config |
| S24 | https://oxc.rs/docs/guide/usage/linter/versioning.html | Versioning policy, Oxc, n/d | semver scope; type-aware, nursery, JS plugins exempt |
| S25 | https://oxc.rs/docs/guide/usage/linter/rules.html | Rules reference, Oxc, n/d | jsx-a11y, react rules-of-hooks, exhaustive-deps, set-state-in-effect |
| S26 | https://api.github.com/repos/oxc-project/oxc/contents/crates/oxc_linter/src/rules/jsx_a11y (and /react, /rules) | GitHub contents API, 2026-10-08 | 36 jsx_a11y files; hooks files; rule plugin directories |
| S27 | https://oxc.rs/docs/guide/usage/linter/js-plugins.html | JS plugins, Oxc, n/d | ESLint v9+ compatible API, alpha |
| S28 | https://oxc.rs/docs/guide/usage/linter/migrate-from-eslint.html | Migrate from ESLint, Oxc, n/d | `@oxlint/migrate`, flat config |
| S29 | https://oxc.rs/docs/guide/usage/linter/automatic-fixes.html | Automatic fixes, Oxc, n/d | fix tiers |
| S30 | https://raw.githubusercontent.com/oxc-project/tsgolint/main/README.md | tsgolint README, oxc-project, n/d | typescript-go based, 59/61, 10-20x claim, MIT |
| S31 | https://registry.npmjs.org/oxlint | oxlint npm packument, npm, 2026-10-08 | 1.87.0, MIT, win32 binding packages |
| S32 | https://crates.io/api/v1/crates/biome_js_parser (and biome_analyze, biome_js_analyze, biome_cli) | crates.io API JSON, 2026-10-08 | 0.5.7 2024-03-12; biome_cli 404 |
| S33 | https://raw.githubusercontent.com/biomejs/biome/main/crates/biome_js_analyze/Cargo.toml | Cargo.toml, biomejs, n/d | `publish = false` |
| S34 | https://biomejs.dev/reference/cli/ | CLI reference, Biome, n/d | reporters, `--write`, `--unsafe`, `--error-on-warnings` |
| S35 | https://biomejs.dev/analyzer/suppressions/ | Suppressions, Biome, n/d | `biome-ignore` forms |
| S36 | https://biomejs.dev/blog/biome-v2/ | Biome v2 codename Biotype, Biome Core Team, 2025-06-17 | type-aware without tsc; ~75% claim |
| S36b | https://biomejs.dev/linter/domains/ | Domains, Biome, n/d | React domain; blog index lists v2.4 HTML accessibility |
| S37 | https://biomejs.dev/guides/migrate-eslint-prettier/ | Migrate from ESLint and Prettier, Biome, n/d | `biome migrate eslint` reads flat config |
| S38 | https://registry.npmjs.org/@biomejs/biome | @biomejs/biome packument, npm, 2026-10-08 | 2.5.15, MIT OR Apache-2.0, win32 CLI packages |
| S39 | https://api.github.com/repos/biomejs/biome/releases | Biome releases, GitHub, 2026-09-30 | cadence |
| S40 | https://crates.io/api/v1/crates/swc_ecma_parser (and swc_ecma_ast) | crates.io API JSON, 2026-10-08 | 46.0.0, 732 versions, Apache-2.0 |
| S41 | https://crates.io/api/v1/crates/ra_ap_ide (and ra_ap_hir, ra_ap_syntax) | crates.io API JSON, 2026-10-08 | 0.0.357, weekly, MIT OR Apache-2.0 |
| S42 | https://raw.githubusercontent.com/rust-lang/rust-analyzer/master/docs/book/src/contributing/architecture.md | rust-analyzer architecture, rust-lang, n/d | hir/ide/syntax "API Boundary" |
| S43 | https://raw.githubusercontent.com/rust-lang/rust-analyzer/master/crates/ide/Cargo.toml | ide Cargo.toml, rust-lang, n/d | version 0.0.0 |
| S44 | https://crates.io/api/v1/crates/clippy (and clippy_lints) | crates.io API JSON, 2026-10-08 | stale 2018 versions |
| S45 | https://raw.githubusercontent.com/rust-lang/rust-clippy/master/README.md | Clippy README, rust-lang, n/d | `clippy-driver`, `cargo clippy --fix` |
| S45b | https://raw.githubusercontent.com/rust-lang/rust-clippy/master/clippy_lints/Cargo.toml | Cargo.toml, rust-lang, n/d | 0.1.101, MIT OR Apache-2.0 |
| S46 | https://raw.githubusercontent.com/rust-lang/rust-clippy/master/rust-toolchain.toml | rust-toolchain.toml, rust-lang, n/d | pinned nightly, rustc-dev |
| S47 | https://raw.githubusercontent.com/rust-lang/rust-clippy/master/clippy_utils/README.md | clippy_utils README, rust-lang, n/d | "only guaranteed to build with this nightly toolchain" |
| S48 | https://doc.rust-lang.org/clippy/usage.html | Clippy usage, rust-lang, n/d | `#[allow]`, `-A/W/D`, `--fix` |
| S49 | https://doc.rust-lang.org/rustc/json.html | rustc JSON output, rust-lang, n/d | JSON schema, suggestion_applicability |
| S50 | https://doc.rust-lang.org/cargo/reference/external-tools.html | External tools, Cargo book, n/d | `compiler-message`, `--message-format` |
| S51 | https://crates.io/api/v1/crates/ast-grep-core | crates.io API JSON, 2026-10-08 | 0.45.3, MIT, 182 versions |
| S52 | https://crates.io/api/v1/crates/tree-sitter | crates.io API JSON, 2026-10-08 | 0.27.0, MIT |
| S52b | https://tree-sitter.github.io/tree-sitter/ | Tree-sitter docs, n/d | C11 runtime embeddable |
| S53 | https://semgrep.dev/docs/cli-reference | Semgrep CLI reference, Semgrep, n/d | `--sarif`, `--json`, `--baseline-commit`, `--autofix` experimental |
| S54 | https://api.github.com/repos/semgrep/semgrep/languages and /repos/semgrep/semgrep and README | GitHub API / README, 2026-10-08 | OCaml core, LGPL-2.1 |
| S55 | https://raw.githubusercontent.com/crate-ci/typos/master/docs/reference.md and README.md | typos docs, crate-ci, n/d | `--format json`, exit codes |
| S56 | https://raw.githubusercontent.com/obi1kenobi/cargo-semver-checks/main/README.md | cargo-semver-checks README, n/d | exit 0/100/101; rustdoc JSON unstable; baseline flags |
| S57 | https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/errors-warnings | C# compiler options: errors and warnings, Microsoft, n/d | ErrorLog SARIF versions |
| S58 | https://raw.githubusercontent.com/microsoft/Microsoft.Unity.Analyzers/main/README.md | Analyzers for Unity README, Microsoft, n/d | NuGet, DiagnosticSuppressor, .NET 10 |
| S59 | https://stylelint.io/user-guide/cli/ | Stylelint CLI, n/d | exit codes, formatter, fix |
| S60 | https://golangci-lint.run/docs/configuration/file/ (and /cli/) | golangci-lint configuration, n/d | output formats incl. sarif; issues-exit-code |
| S61 | https://eslint.org/docs/latest/use/formatters/ | Formatters reference, ESLint, n/d | built-in formatters |
| S61b | https://www.typescriptlang.org/docs/handbook/compiler-options.html | Compiler Options, Microsoft, n/d | `--pretty`, `--version`, `--showConfig`, `--noEmit` |
| S62 | https://eslint.org/docs/latest/use/command-line-interface | ESLint CLI, n/d | `-f`, `-v`, exit 2, `--concurrency`, unused disable directives |
| S63 | https://eslint.org/docs/latest/use/configure/rules | Configure rules, ESLint, n/d | disable comments |
| S64 | https://registry.npmjs.org/@microsoft/eslint-formatter-sarif | npm packument, 2026-07-16 modified | SARIF formatter, MIT, 3.1.0 |
| S65 | https://raw.githubusercontent.com/microsoft/pyright/main/docs/command-line.md | Pyright command-line, Microsoft, n/d | `--outputjson`, exit codes, `--verifytypes`, `--version` |
| S66 | https://raw.githubusercontent.com/microsoft/pyright/main/docs/comments.md | Pyright comments, Microsoft, n/d | `# pyright: ignore[...]` |
| S67 | https://raw.githubusercontent.com/microsoft/pyright/main/docs/features.md | Pyright features, Microsoft, n/d | hover with type info |
| S68 | https://api.github.com/repos/microsoft/pyright/releases | Pyright releases, 1.1.414 2026-09-09 | cadence |
| S69 | https://mypy.readthedocs.io/en/stable/mypy_daemon.html | Mypy daemon, mypy 2.4.0 docs | `--export-types`, experimental parts, `suggest` |
| S70 | https://mypy.readthedocs.io/en/stable/command_line.html | mypy command line, 2.4.0 docs | `-O json`, config files, `-V` |
| S71 | https://raw.githubusercontent.com/python/mypy/master/mypy/dmypy/client.py | dmypy client.py, python/mypy, n/d | `inspect` subcommand and flags |
| S72 | https://raw.githubusercontent.com/python/mypy/master/mypy/dmypy_server.py | dmypy_server.py, python/mypy, n/d | `cmd_inspect` |
| S73 | https://raw.githubusercontent.com/python/mypy/master/mypy/inspections.py | inspections.py, python/mypy, n/d | InspectionEngine returns type strings |
| S74 | https://mypy.readthedocs.io/en/stable/error_codes.html | mypy error codes, 2.4.0 docs | `# type: ignore[code]` |
| S75 | https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/ | Announcing TypeScript 7.0, D. Rosenwasser, Microsoft, 2026-07-08 | no API in 7.0, 7.1 API, typescript6 compat, LSP |
| S75b | https://raw.githubusercontent.com/microsoft/pyright/main/docs/type-concepts-advanced.md | Pyright type concepts, Microsoft, n/d | `reveal_type` examples |
| S76 | https://raw.githubusercontent.com/microsoft/typescript-go/main/README.md | typescript-go README, Microsoft, n/d | API not ready; LSP in progress; repo closed |
| S76b | https://raw.githubusercontent.com/microsoft/pyright/main/docs/installation.md | Pyright installation, Microsoft, n/d | Node required |
| S76c | https://raw.githubusercontent.com/microsoft/TypeScript-wiki/master/Using-the-Compiler-API.md | Using the Compiler API, TypeScript wiki, n/d | TS 6 and earlier; 7.1 different API; getTypeAtLocation |
| S77 | https://registry.npmjs.org/typescript/7.0.2 and /typescript | npm packument, 2026-10-08 | tsc only bin, `unstable/*` exports, dist-tags |
| S77b | https://registry.npmjs.org/typescript/6.0.3 | npm packument, 2026-10-08 | main + tsc + tsserver |
| S79 | https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/ | LSP 3.17 spec, Microsoft, n/d | textDocument/hover, inlayHint |
| S80 | https://raw.githubusercontent.com/qltysh/qlty/main/README.md | Qlty CLI README, qltysh, n/d | 70+ tools, git-aware, caching, BSL 1.1, Windows |
| S81 | https://raw.githubusercontent.com/qltysh/qlty/main/qlty-plugins/plugins/linters/ruff/plugin.toml | qlty ruff plugin, n/d | plugin-as-data example |
| S82 | https://raw.githubusercontent.com/qltysh/qlty/main/qlty-config/src/config/plugin.rs | qlty plugin schema, n/d | DriverDef / PluginDef fields |
| S83 | https://raw.githubusercontent.com/qltysh/qlty/main/qlty-cli/src/commands/check.rs | qlty check args, n/d | `--upstream`, `--sample`, `--fix`, `--unsafe`, `--no-cache` |
| S84 | https://api.github.com/repos/qltysh/qlty/git/trees/main?recursive=1 | qlty repo tree, GitHub, 2026-10-08 | parser files; 70 linter dirs |
| S85 | https://raw.githubusercontent.com/trunk-io/plugins/main/linters/ruff/plugin.yaml | Trunk ruff plugin, n/d | version-range commands, SARIF via converter, known_good_version |
| S86 | https://raw.githubusercontent.com/trunk-io/docs/main/code-quality/overview/cli/getting-started/caching.md | Trunk caching, n/d | hermetic management, cache folder |
| S87 | https://raw.githubusercontent.com/trunk-io/docs/main/code-quality/overview/getting-started/configuration/lint/output-parsing.md | Trunk output parsing, n/d | parser execution model |
| S88 | https://raw.githubusercontent.com/trunk-io/docs/main/code-quality/overview/getting-started/commands-reference/code-quality.md | Trunk commands reference, n/d | `--upstream`, hold-the-line, `--show-existing` |
| S89 | https://raw.githubusercontent.com/trunk-io/plugins/main/README.md | Trunk plugins README, n/d | hermetic tools |
| S90 | https://raw.githubusercontent.com/oxsecurity/megalinter/main/README.md | MegaLinter README, n/d | Docker flavors, SARIF reporter, apply fixes |
| S91 | https://raw.githubusercontent.com/super-linter/super-linter/main/README.md | super-linter README, n/d | container, linterVersions.txt, FIX_* flags, *_FILE_NAME |
| S92 | https://raw.githubusercontent.com/reviewdog/reviewdog/master/README.md | reviewdog README, n/d | errorformat, rdjson, SARIF, filter modes |
| S93 | https://pre-commit.com/ | pre-commit docs, n/d | env reuse, `--from-ref`, hook fields |
| S94 | https://raw.githubusercontent.com/evilmartians/lefthook/master/README.md | Lefthook README, Evil Martians, n/d | dependency-free binary |
| S95 | https://raw.githubusercontent.com/aspect-build/rules_lint/main/README.md and docs/linting.md | rules_lint, Aspect, n/d | hermetic Bazel, changes-only, fixes as patches |
| S96 | https://docs.sonarsource.com/sonarqube-server/latest/analyzing-source-code/importing-external-issues/generic-issue-import-format/ | SonarQube Server 2026.5 docs | generic import and SARIF import |
| S97 | https://raw.githubusercontent.com/codacy/codacy-analysis-cli/master/README.md | Codacy Analysis CLI README, legacy notice, n/d | Docker + Java, legacy |
| S98 | https://raw.githubusercontent.com/danger/danger/master/README.md | Danger README, n/d | CI PR checks, MIT |
| S99 | https://api.github.com/repos/{qltysh/qlty, oxsecurity/megalinter, codacy/codacy-analysis-cli, semgrep/semgrep, astral-sh/ruff, astral-sh/ty, oxc-project/oxc, biomejs/biome, microsoft/pyright, ...} | GitHub repo API, 2026-10-08 | licences (BSL via NOASSERTION + README; AGPL-3.0; LGPL-2.1; MIT; Apache-2.0), pushed_at |
| S99b | https://crates.io/api/v1/crates/serde-sarif | crates.io API JSON, 2026-10-08 | serde-sarif 0.8.0, MIT, last 2025-05-09 |

Fetched-source count: 108 rows (S1-S99 minus S78, plus 10 letter-suffixed companions); some rows cover several closely related URLs.
Local repo files read (not counted): docs/design/{rules,plugins,language-engines,cohesion,monorepo}.md,
notes/research/lint-catalogue-2026-10-08.md, crates/gob-check/src/{tools,tool_parse}.rs.
