# How mature Rust linters test rules, versus frob-v2

Method: shallow clones (depth 1) of the five repos taken 2026-10-06, read directly, then deleted.
Citation form is path:line@sha. Short shas used:

- RUFF = ruff repo (ruff and ty), sha 57a6e86
- CLIPPY = rust-lang/rust-clippy, sha fcffb58
- BIOME = biomejs/biome, sha f0f82425
- OXC = oxc-project/oxc, sha 80840ac
- RA = rust-lang/rust-analyzer, sha ce37b24
- FROB = frob-v2 primary checkout, sha eb988cf85 (HEAD later moved to 3044e2fd2; `git diff --stat`
  of crates/gob-mdtest, docs/design/build-test-ci.md and crates/gob-dev/src/ci.rs between the two
  is empty, so citations hold)

Frontier accounting (Phase 0/2): universe = 6 source nodes (ruff linter, ty, clippy, biome, oxc,
rust-analyzer) + frob-v2 code + 4 named tickets + 2 landed tickets = 13 nodes. All 13 explored, 0
pending, 0 blocked. Things I looked for and did NOT find are listed in section (e).

## Headline finding that changes the framing

Ruff itself has moved its RULE tests onto mdtest. The ruff repo now has a shared `crates/mdtest`
crate (parser, matcher, assertion) used by `ty_test` AND by a new `crates/ruff_mdtest`
(crates/ruff_mdtest/Cargo.toml:18 `mdtest = { workspace = true }`; crates/ty_test/Cargo.toml:17).
CONTRIBUTING.md:264-280 says: "To test rules, Ruff uses the mdtest framework, initially developed for
ty", one directory per linter, one file per rule, `# error` for the bulk and `# snapshot` for
diagnostic/fix detail. The migration is partial: 56 rule mdtest files under
crates/ruff_linter/resources/mdtest versus 1740 legacy fixture files under
crates/ruff_linter/resources/test/fixtures and 2203 `.snap` files under crates/ruff_linter/src/rules
(counts by `find`, RUFF). So "closely follow ruff and ty" now means ONE model (mdtest), with the
fixture+snapshot layer as the legacy and the big-input layer.

---------------------------------------------------------------------------------------------------
## (a) Comparison table

Rows are dimensions; cells are short and cited. "mdt" = ruff/ty shared mdtest.

### a1. Primary harness and layout

| Dim | ruff (legacy) | ruff (new) / ty | clippy | biome | oxc | rust-analyzer | frob-v2 |
|---|---|---|---|---|---|---|---|
| Primary harness | per-linter `mod.rs` with `#[test_case(Rule::X, Path::new("F401_0.py"))]` calling `test_path` then `assert_diagnostics!` (crates/ruff_linter/src/rules/pyflakes/mod.rs:35,189-197@RUFF) | markdown files, one test per `.md` via `datatest_stable::harness!` (crates/ty_python_semantic/tests/mdtest.rs:82-85@RUFF; crates/ruff_mdtest/tests/mdtest.rs:35-37@RUFF) | `ui_test` crate, `tests/ui/*.rs` + `.stderr` + `.fixed` (tests/compile-test.rs:274-287@CLIPPY) | `gen_tests!` macro globs `tests/specs/**/*.{js,ts,json,...}` into one `#[test]` per file (crates/biome_js_analyze/tests/spec_tests.rs:22-25@BIOME) | per-rule `#[test] fn test()` building `Tester::new(NAME, PLUGIN, pass, fail).expect_fix(fix).test_and_snapshot()` in the rule file (crates/oxc_linter/src/rules/eslint/no_debugger.rs:83-100@OXC) | `check_diagnostics(r#"..."#)` / `check_fix(before, after)` helpers in each handler file (crates/ide-diagnostics/src/handlers/unresolved_module.rs tests@RA) | `mdtest!` macro: ONE `#[test]` per corpus dir, walks `*.md` at run time (crates/gob-mdtest/src/lib.rs:14-21,51-71@FROB) |
| File layout | fixtures `resources/test/fixtures/<linter>/<CODE>_<n>.py` (164 entries in pyflakes dir), snapshots `src/rules/<linter>/snapshots/*.snap` (253 in pyflakes) | `resources/mdtest/<linter>/<rule-name>.md` (ruff, 56 files) ; `ty_python_semantic/resources/mdtest/**.md` (362 files) + `resources/mdtest/snapshots/*.snap` (178) | `tests/ui/<lint>.rs/.stderr/.fixed` (2588 entries in tests/ui; 1000 `.rs`; 981 `.stderr`; 580 `.fixed` top-level), plus `tests/ui-toml`, `tests/ui-cargo`, `tests/ui-internal` | `tests/specs/<group>/<rule>/{valid,invalid}*.{js,jsonc,...}` + `.snap` beside each (crates/biome_js_analyze/tests/specs/suspicious/noDebugger/invalid.js{,.snap}@BIOME); `*.options.json` per-case config (style/useConst/invalidFixUnsafe.options.json) | cases inline in the Rust rule file; snapshot `crates/oxc_linter/src/snapshots/<plugin>_<rule>.snap` (851 snaps) | cases inline in handler file; `expect![[...]]` inline literals | `crates/*/tests/mdtest/<rule>.md` (23 files), `crates/gob-mdtest/tests/{mdtest,mdtest_snap,mdtest_fail}` ; no fixture dirs yet |
| Multi-file / config | fixtures dir; settings in Rust `LinterSettings` | multi-file via `` `b.py`: `` label lines, `toml` blocks per section with inheritance (crates/ty_test/README.md:207-232,309-323@RUFF) | `//@aux-build:`, `//@revisions:`, `clippy.toml` per dir in `ui-toml` (writing_tests.md:170-183; 161x `//@aux-build` in tests/ui) | `.options.json` per case | `rule_config` JSON per case in `TestCase` (tester.rs:495-520@OXC) | `//- /path crate:x deps:y` fixture mini-language (docs/book/src/contributing/testing.md:~95-110@RA) | none: one text per case, inline `config="toml"` attr in info string (crates/gob-mdtest/src/parse.rs:234; run.rs:16-27@FROB) |

### a2. Assertion style

| Dim | ruff legacy | ruff new / ty | clippy | biome | oxc | rust-analyzer | frob-v2 |
|---|---|---|---|---|---|---|---|
| Assertion | whole-output snapshot only | BOTH: inline `# error: [rule] "msg"` with optional column (README.md:69-88@RUFF) and `# snapshot` + fenced `snapshot` block (README.md:143-191@RUFF) | BOTH: inline `//~^ lint_name` annotations (writing_tests.md:44-60@CLIPPY) AND whole-stderr `.stderr` file | whole-output snapshot only; valid vs invalid by file name + magic comment | pass/fail vectors (booleans) + fix vector (source, expected) + whole-output snapshot of failing diagnostics | inline `//^^^^ error: msg` range+message annotations (tests.rs:220-250@RA) | inline marker `// error: RULE` (rule+severity+line only) (parse.rs:108-137@FROB) ; optional insta snapshot |
| Unexpected extra diagnostics | fail via snapshot diff | fail: "unexpected error:" (crates/mdtest/src/matcher.rs:243-248@RUFF); unmatched assertion also fails (matcher.rs:225-234) | fail: `require_annotations = true` for tests/ui (tests/compile-test.rs:216-220@CLIPPY) ; `//@check-pass` for clean files (137+22 uses in tests/ui) | snapshot diff; plus valid-named file must carry `// should not generate diagnostics` (crates/biome_test_utils/src/lib.rs:1065-1128@BIOME) | `expect_pass` entries must produce zero diagnostics (tester.rs:test_pass@OXC) | panic with false positives/negatives lists (tests.rs:279@RA) | PARTIAL: findings of other rules are filtered out and ignored (crates/gob-mdtest/src/run.rs:174-178@FROB) |
| Message text | `contains` assertion `"msg"` on mdtest; exact via snapshot | contains-match (matcher.rs:415-417@RUFF) or exact via snapshot | exact via `.stderr` | exact via snap | exact via snap (`GraphicalReportHandler`, tester.rs run()@OXC) | exact in annotation text | NOT asserted except via optional snapshot |
| Span / column | whole range via snapshot | column of span start (matcher.rs:412-414@RUFF); exact range via snapshot | exact via `.stderr` (`^^^^` carets) | exact via snap | exact via snap | exact range via `^^^` | start LINE only (run.rs:136-150@FROB) |
| Clean/negative control | none enforced | none enforced (ty); ty snapshot requires >=1 diagnostic (crates/mdtest/src/lib.rs:~711-716@RUFF) | `//@check-pass` | `valid*` files | `pass` vector | `check_no_fix`, empty annotation set | REQUIRED fire+clean per rule per file (run.rs:215-240@FROB) |

### a3. Snapshot practice

| Dim | ruff legacy | ruff new / ty | clippy | biome | oxc | rust-analyzer | frob-v2 |
|---|---|---|---|---|---|---|---|
| Tool | insta (`insta::assert_snapshot!` via `assert_diagnostics!`, crates/ruff_linter/src/test.rs:521-545@RUFF) | insta for external `.snap` (crates/mdtest/src/lib.rs:728-739@RUFF) + custom in-markdown rewriter for inline blocks (lib.rs:508-526) | `ui_test` own `.stderr/.fixed` | insta (spec_tests.rs:196@BIOME; insta.yaml `update: force`) | insta, `INSTA_REQUIRE_FULL_MATCH: 1` in CI (.github/workflows/ci.yml:19@OXC) | `expect-test` inline literals | insta (run.rs:291-307@FROB) |
| Content | rendered diagnostic WITH source excerpt AND fix diff, `[*]` fixable marker, "unsafe fix" note (see snapshots/ruff_linter__rules__pyflakes__tests__preview_diff__F401_0.py.snap@RUFF) | inline: rendered diagnostic incl. `help:` fix diff and `note: This is an unsafe fix` (resources/mdtest/fixes/imports.md@RUFF); external: frontmatter `mdtest name/path`, numbered source listing, diagnostics (crates/mdtest/src/lib.rs:528-575) | rustc-rendered stderr with `LL` normalised line numbers, suggestions inline (`help: you can reduce it to`) (tests/ui/needless_bool/fixable.stderr@CLIPPY) | `# Input` source + `# Diagnostics` rendered with `FIXABLE` tag and `Unsafe fix:` diff (invalid.js.snap@BIOME) | rendered miette report without color (snapshots/eslint_no_debugger.snap@OXC); fixes NOT in snapshot | n/a (hand/auto-updated literals) | rendered text of gob-diagnostics; fix shown only as `fix: <title>` (crates/gob-diagnostics/src/text.rs:163-164@FROB), no edits |
| Granularity | per-fixture-file | inline: per code block; external: per test section (name contracted + hash, crates/mdtest/src/parser.rs:93-136) | per-file | per-file | per-rule (all failing cases concatenated) | per-assertion | per-block (run.rs:267-285@FROB) |
| Update workflow | `cargo insta review` (CONTRIBUTING.md:118-122@RUFF) | `MDTEST_UPDATE_SNAPSHOTS=1` rewrites the markdown (crates/mdtest/src/lib.rs:26,346,436-461,508) | `cargo uibless` / `RUSTC_BLESS` (compile-test.rs:141,168-171@CLIPPY) | `cargo insta accept/reject/review` (CONTRIBUTING.md:225-231@BIOME) | `cargo insta` (justfile:19@OXC) | `UPDATE_EXPECT=1` (docs/book/src/contributing/testing.md:72@RA) | `INSTA_UPDATE=always` or `cargo insta review` (FORMAT.md:28-30@FROB) |
| CI rejects stale/pending | `cargo insta test --all-features --unreferenced reject` (.github/workflows/ci.yaml:443@RUFF) | same step | `cargo test` with ui_test (mismatch fails; blessing is an explicit flag) | not verified (see e) | `cargo test` then `git diff --exit-code # Must commit everything` (ci.yml:36-38@OXC) | `git diff` style tidy; not verified | YES: `snapshots` step greps `.snap.new`/`.pending-snap` (crates/gob-dev/src/ci.rs:273-292@FROB) and nextest runs through `cargo insta` with `INSTA_UPDATE=no` (ci.rs:309-315) |

### a4. Fix testing

| Dim | ruff | clippy | biome | oxc | rust-analyzer | frob-v2 |
|---|---|---|---|---|---|---|
| Assertion | snapshot shows fix diff + applicability + `[*]`; plus harness panics (below) | `.fixed` file compared to rustfix output (`RustfixMode::Everything`, compile-test.rs:223@CLIPPY; writing_tests.md:211-228) | each code action printed into the snapshot as diff with Safe/Unsafe label (spec_tests.rs:313,324@BIOME) | `expect_fix(vec![(src, expected)])`, also per `FixKind` (tester.rs test_fix@OXC) | `check_fix(before, after)` with cursor-in-fix-range assertion (tests.rs:69-112@RA) | none yet (~G4WAFJT todo; gob-fix ~29MKDDF todo) |
| Convergence | YES: re-lint fixed source until no fixes, `MAX_ITERATIONS = 10`, panic "Failed to converge" (crates/ruff_linter/src/test.rs:232-240,305-316@RUFF) | partial: ui_test also compiles `.fixed` (not read from source here: UNVERIFIED) | NO fixpoint | NO fixpoint (single application) | NO | none |
| No-new-syntax-error | YES: panic if fixed source has a syntax error that original lacked (test.rs:354-366) | `.fixed` must compile (UNVERIFIED mechanics) | YES: reparse each action output, bogus-node and missing-child checks (spec_tests.rs:356-400) | partial | n/a | none |
| Metadata coherence | YES: rule declared never-fixable but fixes -> panic; always-fixable but none -> panic; fixable without help text -> panic (test.rs:395-433) | `//@no-rustfix` opt-out (88 uses in tests/ui) | tree/edit equivalence: `assert_eq!(new_tree.to_string(), output)` (spec_tests.rs:379) | rule that `has_fix()` MUST provide `expect_fix` cases (tester.rs test_fix@OXC) | n/a | none |
| Idempotence | implied by convergence loop | n/a | n/a | n/a | n/a | design doc 6 mentions formatter idempotence only for fmt (build-test-ci.md:325) |

### a5. Docs-as-tests

| Codebase | What runs | Cite |
|---|---|---|
| ty | EVERY lint doc is a markdown file `resources/lint_docs/<rule>.md` run as an mdtest with a default rule: a bare `# error` means "this rule"; the same file is `include_str!`-ed into the lint's doc comment (so docs and test cannot diverge) | crates/ty_python_semantic/tests/mdtest.rs:26-42,84@RUFF; crates/mdtest/src/assertion.rs:296-307@RUFF; crates/ty_python_semantic/src/types/diagnostic.rs:219 (include_str!) ; 138 of 141 `declare_lint!` use it (counts by grep) |
| ruff | docs only checked for being FORMATTED (`check_docs_formatted.py`, ci.yaml:1094); a unit test requires every rule to HAVE an explanation (crates/ruff_linter/src/registry.rs:484-493) and a naming-convention test (registry.rs:495-). Doc examples are not executed (by grep; see e) | |
| biome | `cargo run -p rules_check` runs every ``` code block in rule docs: `expect_diagnostic` blocks must emit EXACTLY one diagnostic, plain blocks zero, `ignore` skips, parse errors fail (xtask/rules_check/src/lib.rs:285-346@BIOME); CI workflow lint_rule_docs.yml:45; contributor rules crates/biome_analyze/CONTRIBUTING.md:1339-1404 | |
| clippy | lint docs are not executed (no doctest wiring found; see e) | |
| oxc | docs are not executed (declare_oxc_lint doc blocks); website generator asserts structure only (tasks/website_linter/src/rules/doc_page.rs:433) | |
| rust-analyzer | doc-comment blocks harvested by codegen (xtask/src/codegen/diagnostics_docs.rs:1-30) into docs; not executed | |
| frob-v2 | design only: "rule docs executable" row (build-test-ci.md:106) ; ticket ~D3ZK8NM acceptance 3 | |

### a6. Coverage meta-tests and end-to-end layers

| Dim | ruff | ty | clippy | biome | oxc | rust-analyzer | frob-v2 |
|---|---|---|---|---|---|---|---|
| Every rule has tests | NOT found as a registry test (grep, e); has `documentation` test (registry.rs:484) | `snapshot-diagnostics` non-empty guard only | `tests/missing-test-files.rs:10-40@CLIPPY`: every file in tests/ needs a sibling `.rs` | `spec_tests.rs:116-135` panics if a spec file is not in `<group>/<rule>/` for a real rule, and `///! lint/group/rule` enable comment must name a real rule (spec_tests.rs:492-511) | `find_rule()` panics if the rule is not registered; fix-capable rule must have fix cases | tidy: unpaired cov_mark hit/check fail (xtask/src/tidy.rs:312-335@RA) | YES and stronger: registry-driven `assert_product_coverage` with ticketed allowlist that may only shrink (crates/gob-mdtest/src/coverage.rs:279-340,361-369@FROB) |
| Message hygiene | rule naming test | | `tests/lint_message_convention.rs:67-116@CLIPPY` scans every `.stderr`: no capital start, no trailing period | | | | none |
| Generated artifacts current | `ruff_dev generate-all` with `Mode::Check` (crates/ruff_dev/src/generate_all.rs:23-28) | same | `cargo dev update_lints --check` (.github/workflows/clippy_dev.yml:29-30) | codegen tasks | `git diff --exit-code` after tests | `xtask codegen --check` for parser inline tests (xtask/src/codegen/parser_inline_tests.rs:21-32) | `cargo dev gen --check` / GEN001 step (ci.yml:`Generated files are current`) |
| Preview vs stable | `preview_rules` test fn per linter with `LinterSettings::with_preview_mode()`, and `preview_diff__*` snapshots showing stable-vs-preview delta (mod.rs:263-271; snapshots dir) | `status` field on lint | n/a (`nursery` group) | `nursery` dir under specs | n/a | n/a | not applicable yet (no preview concept found) |
| Ecosystem / E2E | `ruff-ecosystem check base head` over pinned repos, markdown report (ci.yaml:724-793) | `ty-ecosystem-analyzer.yaml` on PRs (workflow:1-12); mypy_primer is only referenced from scripts/setup_primer_project.py, no workflow (grep) | `lintcheck` crate over crates.io + `lintcheck.yml` workflow | e2e-tests dir | `tasks/coverage` conformance snapshots | slow-tests tidy | design only (~9HS3VP7 todo) |
| Fuzz | daily parser fuzz workflow (daily_fuzz.yaml:1-30) | py-fuzzer | n/a | fuzz/ dir | n/a | n/a | ~9N8G5S2 todo |
| Inline parser tests | `// test_ok NAME` / `// test_err NAME` extracted by an ordinary `#[test]` (crates/ruff_python_parser/tests/generate_inline_tests.rs:1-34; 123 ok, 256 err in resources/inline) "derived from rust-analyzer and biome" | | | | | `// test NAME` blocks + `xtask codegen` (crates/parser/src/grammar/items.rs:14; 503 ok, 116 err in test_data/parser/inline) | ~2GG2KXR todo |

---------------------------------------------------------------------------------------------------
## (b) Feature diff: gob-mdtest versus ruff/ty mdtest

Legend: [ty-only] ty has it, we lack it. [frob-only] we have it, ty lacks it. [diff] both, done differently.

### b1. ty has, gob-mdtest lacks

1. Strict "no unexpected diagnostics" at file level. ty fails any diagnostic not matched by an
   assertion ("unexpected error:", crates/mdtest/src/matcher.rs:243-248@RUFF). gob-mdtest keeps only
   findings whose rule equals the block rule or is named in a marker and silently drops the rest
   (crates/gob-mdtest/src/run.rs:174-178@FROB). A rule that starts also firing a second rule on its
   fixtures is invisible. (Possibly intentional because the product runner emits findings from the
   whole ruleset; but then a `rules=` select knob in the Case is the ty/ruff answer: ruff mdtests
   pin `select = ["F401"]` in a toml block, resources/mdtest/pyflakes/unused-import.md:3-7@RUFF.)
2. Message and column assertions: `# error: 8 [rule] "text"` (README.md:69-88@RUFF; matcher.rs:411-418).
   Ours: rule + severity + line only (parse.rs:25-34@FROB).
3. Next-line and stacked assertion comments (README.md:92-116@RUFF). Ours: same line only
   (parse.rs:111-134).
4. Multi-file tests with explicit paths (README.md:207-232). Ours: Case carries a single `text`
   and `file_name` (run.rs:16-27). frob rules that need cross-file context (links, imports, ticket
   ledger) work around it in the runner (crates/frob-obligations/tests/corpus.rs:12-30@FROB: `SIDE_FILES`,
   `{{OPEN}}` placeholders).
5. Section-scoped TOML config blocks with parent-to-child inheritance (README.md:309-323). Ours:
   `config="..."` on each fence (parse.rs:234) and a suite-level default rule only
   (parse.rs:259-278); no nesting beyond `#`/`##` (parse.rs:251-255), no inheritance.
6. Nested sections of arbitrary depth with the rule "a section is a test OR a group, never both"
   enforced (crates/mdtest/src/parser.rs:809). Ours: two heading levels flattened into a name
   string; deeper headings are ignored (parse.rs:251-255).
7. Literate merge: multiple blocks in a section concatenate into one file (README.md:118-141;
   parser.rs:898-953). Ours: every fence is an isolated case.
8. Failure reports point at markdown file:line of the failing assertion line
   (crates/mdtest/src/lib.rs:95-125, via `EmbeddedFileSourceMap`), optionally as GitHub annotations
   (`MDTEST_GITHUB_ANNOTATIONS_FORMAT`, lib.rs:31,159; ci.yaml:434-441@RUFF), and print a rerun
   command (lib.rs:137-146). Ours: block-relative line in a table, with only the fence line in the
   case name (run.rs:136-170, parse.rs:225).
9. Test filter env var `MDTEST_TEST_FILTER` selects one section inside a file (lib.rs:23,65-69).
   Ours: none; granularity is the whole corpus directory (lib.rs:14-21@FROB).
10. One cargo test per markdown file via datatest_stable (mdtest.rs:82-85) => nextest isolates and
    retries per file; ours reports all files in one test.
11. Panic containment: `attempt_test` wraps the checker in `catch_unwind` and reports the panic
    against the markdown (lib.rs:597-605); `<!-- expect-panic: msg -->` turns a known panic into a
    regression test (README.md:193-205; parser.rs:594; lib.rs:673-700). Ours: runner called bare
    (run.rs:339) so one panic aborts the whole corpus test with no case attribution.
12. Inline snapshots: `# snapshot` marker plus a fenced `snapshot` block in the markdown itself,
    auto-inserted/updated/removed by `MDTEST_UPDATE_SNAPSHOTS=1` (lib.rs:357-470,508-526). Ours:
    only external insta files per block (run.rs:291-307). Staleness checks: "snapshot block but no
    `# snapshot`" fails (lib.rs:~420-440).
13. Fix display in snapshots (ruff): the inline snapshot carries `help:` + diff + applicability note
    (resources/mdtest/fixes/imports.md@RUFF). Ours renders only `fix: <title>` (text.rs:163-164@FROB).
14. Strict parser hygiene: unknown HTML comments are errors (parser.rs:639-647), code blocks must be
    preceded by a blank line (parser.rs:683), file extension must match language (parser.rs:855-870),
    `data-mdtest="ignore"` and `ignore`/`pycon` langs for non-test blocks (parser.rs:714,843). Ours:
    silent skip for anything without `expect=` (parse.rs:198-201) and unknown `<!-- -->` ignored
    (parse.rs:256-278): a typo such as `expect=fires` errors, but `<!-- mdtets: -->` is invisible.
15. Extra invariant passes per test: ty runs a pull-types pass (lib.rs:322-400) and a module
    resolution consistency check (lib.rs:486-525) on every case; `<!-- pull-types:skip -->` opts out
    (parser.rs:593). Ruff mdtest runs `test_contents`, i.e. the SAME convergence and syntax-error
    checks as the legacy harness (crates/ruff_mdtest/src/lib.rs:117-134@RUFF) so fix invariants ride
    on every mdtest case for free. This is the model for ~G4WAFJT.
16. `RunOptions.default_error_rule`: a bare `# error` in rule docs means the doc's rule
    (assertion.rs:296-307; mdtest.rs:26-42). Needed for executable docs (~D3ZK8NM).
17. Section directive `<!-- snapshot-diagnostics -->` scoped to the current section (parser.rs:592;
    process_mdtest_directive). Ours: file-level, applies to "every block after the header"
    (FORMAT.md:21-23; parse.rs:256-258) with no way to switch off.
18. Tooling: `mdtest.py` watcher, rebuilds and reruns affected markdown on change
    (crates/ty_python_semantic/mdtest.py:246-261@RUFF). Ours: none.
19. Mdtest self-tests live in the parser (parser.rs `#[cfg(test)]` ~1100-2400) and matcher
    (matcher.rs:646); ours: selftest.rs with three failure corpora (crates/gob-mdtest/tests/selftest.rs:43-68).
    Comparable in spirit, thinner.
20. Mocked environments (`python =`, `<path-to-site-packages>`), external dependencies via uv lockfile
    (README.md:329-445). Not applicable to frob; listed for completeness.

### b2. gob-mdtest has, ty/ruff mdtest lacks

1. REQUIRED positive controls: each rule named in a file needs one `expect=fire` and one
   `expect=clean` block, else `MissingControl` (run.rs:29-46,215-240; FORMAT.md:53-57@FROB). ty and
   ruff require none; clippy has only `check-pass`.
2. Registry-driven rule coverage with a shrink-only, ticket-bound allowlist (coverage.rs:279-369;
   coverage-allowlist.toml 59 `[[gap]]`: 27 frob, 32 grimble). ruff has no equivalent that I could
   find (only `rule.explanation().is_some()`, registry.rs:484-493@RUFF).
3. Severity in the marker (`error:`/`warn:`) compared exactly (parse.rs:116, run.rs:133-211). ty's
   `# error` is one kind plus `# revealed`.
4. Expect-clean marks cases as intentionally silent, so a "clean" snapshot is possible (FORMAT.md:27).
   ty's snapshot refuses an empty diagnostic set (crates/mdtest/src/lib.rs:~711-716@RUFF).
5. Snapshot name stable against block moves: fence line is dropped from the snapshot name
   (run.rs:264-285). ty's name is heading path + hash, also stable.
6. Marker comment styles for non-Python languages (`//`, `#`, `<!--`; parse.rs:112) so Rust, TS,
   markdown and TOML fixtures work. ty's matcher takes Python comments (and ruff_mdtest also TOML via
   toml_parser, assertion.rs:60-77@RUFF), so frob is more language-generic.
7. Insta pending-file hygiene as a separate CI step independent of the unit tests
   (ci.rs:273-292@FROB).

### b3. Done differently

| Aspect | ty/ruff | frob | Judgement |
|---|---|---|---|
| Test unit | section (header path), file-per-test-binary entry | fence block, corpus-per-test-binary | adopt ty's section unit: a section may hold several blocks (literate/multi-file) |
| Case gating | every `py/pyi/toml` fence is test input; `ignore` opts out | `expect=` attr opts in | frob's opt-in is safer for docs-heavy markdown; but keep an error for unknown attr keys |
| Rule under test | implied by config `select` + `[rule-name]` in assertions | `rule=` attr or `<!-- mdtest: rule= -->` | fine; add a `default_error_rule`-like bare `error:` for docs |
| Snapshot opt-in | per-line `# snapshot: code` marker or per-section directive | per-file directive | move to per-section directive plus the per-line marker |
| Snapshot storage | inline in markdown (preferred) or external | external only | inline is the stated preference (README.md:190-191@RUFF); reviewers read it in the diff next to the code |

---------------------------------------------------------------------------------------------------
## (c) Recommended frob-v2 rule-testing model

### c0. Principle

Make mdtest the single primary layer for rule behaviour (as ruff has now decided,
CONTRIBUTING.md:264-280@RUFF), and keep the fixture+snapshot layer only for big real-shaped inputs.
Reason: ruff's legacy layer needs 3 artifacts per case (fixture file, `#[test_case]` line in mod.rs,
`.snap`) and 1740 fixtures; ruff chose to put prose, input, assertion and expected output in one
file because the assertion is then reviewable in the PR diff (README.md:190-191: "inline snapshots
are generally preferred for new tests"). frob already chose mdtest for the same reason (D98).

### c1. Layers and what each asserts

| Layer | Location | Asserts | Cite for the choice |
|---|---|---|---|
| L1 rule mdtest (primary) | `crates/*/tests/mdtest/<family>/<rule-slug>.md`, one file per rule, sections per scenario | `error: RULE` markers: rule, severity, line (have) + optional column and `"message-substring"` (add); strict mode: any finding not matched by a marker FAILS (add); required fire+clean controls (have) | ty README.md:69-88, matcher.rs:243-248@RUFF; frob-only controls run.rs:215-240@FROB |
| L2 diagnostic snapshot, inline | a fenced `snapshot` block after the case, driven by `snapshot:` marker or section directive | full rendering (excerpt, labels, help) AND, for fixable rules, the fix edits rendered as a diff plus tier (safe/unsafe) | ruff resources/mdtest/fixes/imports.md@RUFF; README.md:143-191@RUFF |
| L3 fix invariants, automatic | in the runner for every case that yields a finding with a `Fix` (no per-test code) | apply fixes to fixpoint (<=10 rounds, as ruff `MAX_ITERATIONS`), re-parse after each round, no new parse error, no fixable finding left, rule-declared fixability consistent with findings | crates/ruff_linter/src/test.rs:232-240,305-316,354-366,395-433@RUFF; ruff_mdtest calls `test_contents` so mdtest cases get this free (crates/ruff_mdtest/src/lib.rs:117-134@RUFF) |
| L4 fixtures, large | `crates/*/resources/test/fixtures/<FAMILY>/<RULE>.<ext>` + `<RULE>.snap` (already recognised by coverage.rs:143-164) | whole-output snapshot of rendered diagnostics (and fix diff) for realistic files, with the same L3 invariants | ruff legacy layer; keep only where inputs are big |
| L5 docs examples | the rule's `Example` block is the SAME markdown the runner executes (include_str-style) | bare `error:` means the doc's rule fires; a `Fixed` block (if any) equals the fix result | ty lint_docs (tests/mdtest.rs:26-42@RUFF; diagnostic.rs:219@RUFF); biome rules_check (xtask/rules_check/src/lib.rs:285-346@BIOME) |
| L6 coverage meta-tests | registry-driven, in each `*-check` crate | every rule has L1 pair or L4 fixture (have); every rule has docs sections (add); every fixable rule has an L2 fix snapshot (add) ; allowlist shrink-only (have) | coverage.rs@FROB; registry.rs:484-493@RUFF ; oxc: fixable rule without fix cases panics (tester.rs test_fix@OXC) |
| L7 ecosystem | `cargo dev ecosystem`, non-blocking PR comment | per-rule added/removed/changed deltas, crashes | ruff ci.yaml:724-793; ty-ecosystem-analyzer.yaml |

### c2. Specific choices and why

1. Stay with `<!-- mdtest: ... -->` plus info-string attrs for case metadata, but ADD ty's section
   model underneath: a section = nearest heading; blocks in a section that carry no `file=` merge;
   blocks with `file=` are separate files of one case; `toml` fences configure the section and its
   descendants. Justification: README.md:118-141, 207-232, 309-323@RUFF. Keeps the `expect=` opt-in
   (FORMAT.md) so prose-heavy docs stay safe.
2. Strictness by default, relaxed explicitly. A case fails on any finding not matched by a marker,
   across ALL rules the runner ran, unless the section config selects rules (the ruff pattern
   `select = [...]`, resources/mdtest/pyflakes/unused-import.md:3-7@RUFF). Today's silent filter
   (run.rs:174-178@FROB) hides regressions where a rule fires twice or a neighbour starts firing.
3. Add `snapshot` inline blocks and `FROB_MDTEST_UPDATE=1` (name by analogy to
   `MDTEST_UPDATE_SNAPSHOTS`) that rewrites the markdown in place, with the same three staleness
   failures ty has (missing block, stale block, orphan block; lib.rs:357-470@RUFF). Keep insta
   external snapshots only for the `snapshot-diagnostics` whole-section case (already landed,
   ~7BT4W67). Justification: ruff's own contributor guide prefers inline; review shows the expected
   text in the same diff hunk as the input.
4. Render the fix in the diagnostics text renderer (gob-diagnostics) as a unified diff with tier,
   not only `fix: <title>` (text.rs:163-164@FROB). Without this, L2 cannot assert fix edits at all.
   This is the mechanism ruff uses: the fix is part of the rendered diagnostic, so one snapshot
   covers message, span and fix (snapshots/...preview_diff__F401_0.py.snap@RUFF;
   fixes/imports.md@RUFF).
5. Fix testing = ruff's harness, wired into the runner, not into each test. ruff proved the
   pattern by reusing `test_contents` for mdtest (ruff_mdtest/src/lib.rs:117-134). biome adds one
   more cheap check worth copying: edit-application equals tree-print (spec_tests.rs:379-383), which
   for frob means "applying `Fix.edits` to the text equals the fixer's output" (relevant because
   gob-fix has dry-run diff identical to real run, ~29MKDDF). Clippy's `.fixed` file is rejected as
   the primary model: a separate file per fixable test (580 `.fixed` files) doubles review surface
   and cannot show tier.
6. Docs-as-tests: use ty's design, not biome's. ty makes the doc file the test file and includes it
   into the rule documentation, so there is one source; biome extracts blocks from doc comments at
   a separate xtask. For frob, `#[derive(Rule)]` already takes the doc comment (~D3ZK8NM); the
   least-drift path is to move each rule's long doc to `crates/<crate>/resources/rule_docs/<rule>.md`
   (include_str!) and run that dir as a second `mdtest!` invocation with `default_rule`. Require
   sections What it does / Why it matters / Example (already ~D3ZK8NM).
7. CI rejections (all cheap, all already half there):
   - stale or pending snapshots (have: ci.rs snapshots step + `INSTA_UPDATE=no`);
   - inline snapshot drift (new: mdtest fails unless update env is set, like ci.yaml GitHub
     annotation step runs without update);
   - mdtest parse errors, unknown directive comments, unknown attrs (add: parser.rs:639-647 model);
   - registry coverage gaps and stale allowlist (have);
   - rule without docs sections or non-running Example (~D3ZK8NM);
   - fixable rule without fix snapshot, fix that fails convergence or reparse (~G4WAFJT);
   - generated artifacts (GEN001, have).
8. Test addressing and failure UX: adopt per-file tests or an env filter, and report
   `path.md:LINE` of the failing marker line (lib.rs:95-125@RUFF). With 23 corpus files today
   whole-corpus granularity is tolerable; at ruff scale (362 ty files) it is not, and nextest
   per-file isolation is the reason ty uses datatest_stable (mdtest.rs:82-85).
9. Panics: wrap runner in `catch_unwind` and support `<!-- expect-panic: msg -->` (lib.rs:597-605,
   673-700@RUFF). Rule engines on arbitrary input will panic; ty/ruff treat that as a first-class
   regression test form.
10. Do NOT copy: clippy's lint-message convention test is cheap and worth a small port (scan
    snapshots for capitalised or period-terminated messages, tests/lint_message_convention.rs:67-116);
    biome's `valid`-by-filename magic comment convention is unnecessary because frob has explicit
    `expect=clean`; oxc's pass/fail booleans are weaker than markers.

---------------------------------------------------------------------------------------------------
## (d) Gaps mapped to tickets

Existing tickets and what they cover (brief output at `target/debug/frob ticket brief`):

- ~7BT4W67 (landed): snapshot-diagnostics header + insta per block. Delivered; see b1.12/17 for
  what ty has beyond it.
- ~BGB8V55 (landed): registry coverage + allowlist. Delivered; follow-on umbrella tickets
  ~C5DQ4WJ (frob, todo) and ~QSK0WB1 (grimble, todo) exist.
- ~G4WAFJT (todo, blocked by ~29MKDDF): fix snapshots + fixpoint harness in gob-fix/gob-mdtest.
  Covers c1/L3 and half of L2. Needs two additions listed below (renderer shows fix diff; harness
  runs inside mdtest runner rather than separate fixture loop).
- ~2GG2KXR (todo): inline parser tests test_ok/test_err. Matches ruff_python_parser (generate_inline_tests.rs:1-34@RUFF) and RA (xtask/src/codegen/parser_inline_tests.rs:21-32@RA). One caveat below.
- ~9HS3VP7 (todo): cargo dev ecosystem. Matches ruff ci.yaml:724-793; note ty uses an
  `ecosystem-analyzer` workflow, not mypy_primer, at this sha (the design doc's "ty mypy_primer"
  wording in build-test-ci.md:327 is stale).
- ~D3ZK8NM (todo): rule decl validation + doc sections + Example as executable mdtest. Covers L5
  and L6 docs coverage; needs the mdtest feature `default rule` (below) first.

| # | Gap (source) | Ticket |
|---|---|---|
| 1 | Fix harness: fixpoint <=10 rounds, reparse, no new parse error, fixability consistent (ruff test.rs:232-433) | ~G4WAFJT; add note: run inside the mdtest runner for every case with a fixable finding, as ruff_mdtest does |
| 2 | Fix edits visible in snapshots (renderer shows only title, text.rs:163-164) | ~G4WAFJT acceptance 1 is unsatisfiable without it; fold in or NEW-1 |
| 3 | Inline parser tests | ~2GG2KXR (caveat: 5+5 per parser is a floor; ruff has 123/256, RA 503/116) |
| 4 | Ecosystem | ~9HS3VP7 |
| 5 | Executable rule docs | ~D3ZK8NM (blocked by NEW-3 default-rule bare marker) |
| 6 | Rule coverage umbrella | ~BGB8V55 landed; gaps ~C5DQ4WJ, ~QSK0WB1 |
| 7 | Strict unmatched-finding failure | NEW-2 |
| 8 | Marker columns and message contains | NEW-3 |
| 9 | Sections, multi-file, toml config blocks with inheritance, literate merge | NEW-4 |
| 10 | Inline `snapshot` blocks and update env | NEW-5 |
| 11 | Failure UX: md file:line, rerun hint, GitHub annotations, filter env, per-file tests | NEW-6 |
| 12 | Panic containment and expect-panic | NEW-7 |
| 13 | Parser strictness: unknown directives and attrs are errors | NEW-8 |
| 14 | Message-convention scan over snapshots (clippy) | NEW-9 |
| 15 | Design doc drift: section 2 says `crates/*/tests/md/*.md` and shows a `## repo`/`## expect` format; reality is `tests/mdtest/` and FORMAT.md (build-test-ci.md:100,108-123 vs coverage.rs:132-141) | NEW-10 (docs only) |

### NEW ticket proposals (one paragraph each)

NEW-1 "gob-diagnostics: render Fix edits and tier in the text renderer". The text renderer prints
`fix: <title>` only (crates/gob-diagnostics/src/text.rs:163-164). Render the fix as a unified diff
of the edits with the applicability tier and, for unsafe tiers, a `note:` line, following ruff's
rendered form (resources/mdtest/fixes/imports.md@RUFF) so that one insta or inline snapshot
asserts message, span and fix. Scope gob-diagnostics and the existing snapshots; acceptance: a
fixable toy rule in gob-mdtest self-tests produces a snapshot containing the diff, and a changed
edit fails the snapshot. Blocks ~G4WAFJT acceptance 1; depends on ~DW4RJVG tiers if not landed.

NEW-2 "gob-mdtest: strict mode, unmatched findings fail". Today the runner drops findings from
rules other than the block's rule or marker rules (run.rs:174-178). Add a `rules` selection to
Case (section config, default = the block rule plus rules named in markers) and fail any
finding from the selected set that is not matched by a marker, plus a per-case "unexpected finding"
line in the diff table, mirroring ty's "unexpected error:" (matcher.rs:243-248@RUFF). Include a
migration pass over the 23 existing corpus files; findings that legitimately co-fire get an
explicit marker. Acceptance: self-test where a second rule fires makes the case fail; all
existing corpora pass.

NEW-3 "gob-mdtest: column and message assertions, bare marker with default rule". Extend markers to
`error: 8 RULE "substring"` (column 1-based start, message contains) following README.md:69-88@RUFF,
plus `RunOptions.default_rule` so a bare `error:` in a rule-docs corpus means the doc's rule
(assertion.rs:296-307@RUFF). Also accept a marker on its own line applying to the next non-marker
line and stacked markers (README.md:92-116). Acceptance: parser unit tests for each form, a failing
corpus for each mismatch, FORMAT.md updated. Prerequisite for ~D3ZK8NM acceptance 3.

NEW-4 "gob-mdtest: section tests, multi-file cases, toml config blocks with inheritance". Replace
the h1/h2 name string (parse.rs:251-255) with a header tree; a section is either a test or a group,
enforced (parser.rs:809@RUFF); blocks in a section without `file=` merge in order; blocks with
`file=` become extra files of the same case; a `toml` fence sets config for the section and its
descendants, child overriding parent (README.md:309-323). Case gets `files: Vec<(name,text)>`
instead of one text; keep `expect=` and `rule=` attrs. Frees frob-obligations from its
SIDE_FILES/placeholder workaround (crates/frob-obligations/tests/corpus.rs:12-30). Acceptance:
cross-file corpus for a link rule, inherited-config test, error for a section that is both.

NEW-5 "gob-mdtest: inline snapshot blocks and in-place update". Add a `snapshot` fence directly
after a case and a `snapshot` marker or section directive; `FROB_MDTEST_UPDATE=1` inserts, rewrites
or removes the block (lib.rs:357-470,508-526@RUFF), with three failures (missing, stale, orphan).
Keep external insta only for `snapshot-diagnostics`. Acceptance: self-tests for each of the four
transitions, FORMAT.md section, CI proves update mode is off (env guard in `cargo dev ci`).

NEW-6 "gob-mdtest: failure UX and addressing". Report failures as `path.md:LINE` of the marker
(map block-relative lines through the fence start; ty `EmbeddedFileSourceMap`, lib.rs:95-125@RUFF),
print a rerun command, add `MDTEST_FILTER` (substring of section path, lib.rs:65-69), emit GitHub
annotation format when `MDTEST_GITHUB_ANNOTATIONS_FORMAT` is set (lib.rs:159), and generate one
`#[test]` per markdown file (datatest-style, mdtest.rs:82-85) so nextest isolates and retries per
file. Acceptance: self-test for the line mapping, nextest lists one test per corpus file, the CI
step uses annotations. Low risk; high value once corpora reach hundreds of files.

NEW-7 "gob-mdtest: panic containment and expect-panic". Wrap the runner in `catch_unwind` (use
the repo's panic-to-Result boundary if one exists), attribute the panic to the markdown line, and
support `<!-- expect-panic: substring -->` plus its inverse failure "expected to panic but didn't"
(lib.rs:597-605,673-700@RUFF; resources/mdtest/test-rules/panicy-test-rule.md@RUFF as the
self-test). Acceptance: self-test for panic reported not aborted, expect-panic pass, expect-panic
missing fail.

NEW-8 "gob-mdtest: reject unknown directive comments and attribute keys". Mirror
crates/mdtest/src/parser.rs:639-647@RUFF: any `<!-- ... -->` other than a known directive or an
allowlist (`fmt:on/off`, prettier-ignore, markdownlint) is a parse error; an info-string attribute
key not in {rule, expect, config, file} is a parse error; a fence with `rule=` but no `expect=` is
an error (currently it is silently documentation, parse.rs:198-201). Acceptance: parse tests, and
the 23 corpora pass or are fixed.

NEW-9 "lint snapshot and message convention test". Port tests/lint_message_convention.rs:67-116
@CLIPPY: scan every rendered finding message in snapshots and rule registry for capital start and
trailing period, with the convention taken from the diagnostics style guide. Acceptance: test over
registry messages, with allowlist in the same shrink-only style as coverage.

NEW-10 "design doc: bring build-test-ci.md section 2 in line with FORMAT.md". Fix the path
(`tests/mdtest/`, build-test-ci.md:100 vs coverage.rs:132-141), replace the `## repo`/`## expect`
example (build-test-ci.md:108-123) with the real format, replace "ty mypy_primer" with "ty
ecosystem-analyzer" in section 6 (line 327), and note that ruff now tests rules with mdtest
(CONTRIBUTING.md:264@RUFF). Docs only; run `frob ack` for drift.

Recommended order (smallest unblocking set first): NEW-1 and NEW-3 (unblock ~G4WAFJT and
~D3ZK8NM), NEW-2, NEW-4, NEW-5, NEW-7, NEW-6, NEW-8, NEW-9, NEW-10.

---------------------------------------------------------------------------------------------------
## (e) UNVERIFIED and not-found list

Not found by search (absence claims limited to the greps I ran):

1. ruff: no registry-driven test asserting every rule has a fixture or mdtest. I grepped
   `ruff_linter/src`, `ruff_dev/src`, `ruff/tests` for all_rules/every_rule/has_fixture patterns
   and found only registry.rs:484-493 (documentation) and :495- (naming). Could live elsewhere.
2. clippy: lint doc examples executed as tests. Grepped Cargo.toml, book, workflows for doctest
   wiring: nothing. `cargo dev update_lints --check` checks generated lists, not examples.
3. oxc and RA doc examples executed: not found.
4. ty mypy_primer workflow: only scripts/setup_primer_project.py and memory_report.py mention it;
   ty PR ecosystem job is ty-ecosystem-analyzer.yaml. I did not read the analyzer scripts.
5. biome: CI rejection of stale/pending insta snapshots. `grep insta .github` found nothing;
   `cargo test --workspace` (pull_request.yml:135-138) with insta's default CI behaviour would fail
   on mismatch, but I did not verify INSTA_UPDATE handling or `--unreferenced` use. insta.yaml
   only sets `update: force` for local runs.
6. rust-analyzer: CI rejection of stale expect-test literals (tidy covers cov_mark pairing and
   `should_panic`, tidy.rs:193-218,312-335; no staleness check for `expect![[]]` found).

Not verified from source (relied on docs or inference):

7. clippy ui_test internals: that `//~^` is matched by line offset, that unannotated diagnostics
   fail when `require_annotations` is true, that rustfix output is compiled and diffed against
   `.fixed`. I read clippy's config (compile-test.rs:216-223) and its book (writing_tests.md:211-228)
   but the `ui_test` 0.30.7 crate source was not in the local cargo registry, so the mechanics are
   per documentation, not per code.
8. ruff's `mdtest` snapshot-name hashing: read the contraction + SipHash code
   (parser.rs:93-136) but not its stability guarantee across versions.
9. ty `<!-- snapshot-diagnostics -->` section scoping: parser.rs:592 shows the directive and
   `should_snapshot_diagnostics()` is used (lib.rs:704), but I did not read `process_mdtest_directive`
   to confirm inheritance to sub-sections.
10. Counts (files, snapshots, lints with docs) come from `find`/`grep -c` on the shallow clones.
    `declare_lint!` count 141 includes macro-use sites in tests and may overcount; 138
    `include_str!` of lint_docs is exact for that pattern.
11. biome's `just ci` equivalents and whether the `rules_check` job is required for merge
    (lint_rule_docs.yml:45 runs it on PRs touching rule or doc paths; paths filter not read in full).
12. frob side: I read FORMAT.md, parse.rs, run.rs, lib.rs, coverage.rs, tests, 2 corpora, ci.rs
    snapshot steps. I did not run the suite, nor read the rule runner of every corpus crate
    (frob-pm, frob-release, gob-directives) beyond frob-obligations; the claim "frob's runners
    work around single-file cases" is shown only for frob-obligations (corpus.rs:12-30).
13. The `target/debug/frob` binary used for `ticket brief` may be older than HEAD; ticket text is
    what the binary printed at read time (HEAD advanced from eb988cf85 to 3044e2fd2 during the
    session).
14. Whether frob has a "preview" lifecycle that would need a ruff-style `preview_diff`: not found
    in design docs I read; not searched exhaustively.
15. ruff `ruff_mdtest` is young: only 56 files, one `fixes` file, one `panicy` self-test. Treat the
    exact public API (`ruff_mdtest::run`, crates/ruff_mdtest/src/lib.rs:30-53@RUFF) as unstable.

Clones under <scratchpad>/ref2 are deleted after this file was written.
