# How widely-used repositories generate and single-source their documentation

Date: 2026-10-03. Purpose: inform frob's doc-consistency design (include regions with a check, paired
sections that must be re-read together, checked fact references, single canonical definitions with
near-duplicate detection). Companion to `notes/research/docs-survey.md` (which measured layout and
freshness gates); this file measures the generation, transclusion, testing and checking layers.

Everything below is measured from public GitHub data unless it says INFERENCE or UNVERIFIED. All
percentages carry their denominator. Nothing was cloned, built or run; no frob or cargo commands.

## 0. Honest scope and coverage (read first)

Universe (denominator): the 1254 repositories of the earlier survey (`sample.json`): 284 "tools" and 970
"libraries/apps"; 117 Rust, 100 Go, 95 Python, 80 TypeScript, 70 JavaScript, 61 C++, 60 C, 59 Ruby, 56
Java, 53 C#, 53 Haskell, 52 each Scala, Swift, Elixir, Zig, 51 each Kotlin, OCaml, 50 PHP, 32 Dart, rest
under 25. The sample is curated plus language-bucketed by stars, so it over-represents famous projects and
(in the top stars) a few very new AI-agent repositories; prevalence is for THIS sample, not for GitHub.

What was read (all fetched through `raw.githubusercontent.com`, resumable, no API quota used except
search):

| Source | Count | Notes |
|---|---|---|
| Recursive file trees | 1254 | reused; 18 truncated |
| Config files (Makefile, justfile, Cargo.toml, package.json, pyproject.toml, mkdocs.yml, book.toml, docusaurus config, conf.py, .pre-commit-config, lychee/vale/typos/cspell/codespell/markdownlint/cliff/towncrier/release-please configs, CODEOWNERS ...) | 5785 files, 862 repos | root to depth 2, max 25 per repo |
| Generator/check scripts (xtask sources, tidy, scripts/tools/ci names matching doc/gen/check/lint/schema/man/sync) | 2235 files | max 12 per repo |
| `src/lib.rs` files | 858 files, 171 repos | max 8 per repo, first 25 KB |
| Workflows | 7425 files, 1074 repos | max 15 per repo, first 60 KB |
| READMEs | 1214 | |
| Markdown sample (up to 12 docs-dir files + 6 others per repo) | 12780 files | random, seeded |
| Deep pass over repos with a site generator config (mdBook, MkDocs, Docusaurus, Sphinx, Antora, VitePress) | 9277 files, 164 repos | up to 100 doc files per repo |
| Duplicate-text sample (60 repos with docs sites, 24 tools and 36 libraries) | 7146 files | up to 160 doc files per repo |
| Union used for in-markdown patterns | 27154 distinct repo-file reads; every repo has at least 1, 1118 have at least 5, 162 have at least 20 | |
| GitHub code search (global file counts, not repo counts) | 55 queries | approximate, includes tutorials that merely mention the syntax |
| Repo-scoped commit/issue searches | about 90 queries | evidence for "what goes wrong" |
| Hand-read exemplar sources (ruff, uv, rust-analyzer, cargo, rust-lang/book, cpython, mermaid, helix, cilium, rust, jj, django, clippy, rclone, tigerbeetle, nlohmann/json) | 35 files | to verify mechanisms, not guess them |

What was NOT sampled or cannot be measured with this method (these are blind spots, not zeros):
- Go `cobra/doc` generators, Go `Example*` function bodies, Elixir `doctest Module` lines, OCaml `(mdx)`
  dune stanzas, Kotlin `knit` Gradle config: the source files that hold these were not fetched (only
  path-level or config-level proxies exist; stated where used). Go cobra measured 0 here and is NOT a real
  zero (global code search: 2408 Go files contain `GenMarkdownTree`).
- In-markdown patterns are a LOWER BOUND per repo: median 8 doc files were read for repos that are not
  site-generator repos, whereas big docs sites have hundreds. For site-generator repos (164) the pass was
  deeper (mean 65 to 130 files read per repo) but capped at 100.
- Workflow and config regexes are approximate (indicative to the first digit). Doctests inside code
  comments (Rust `///`, Python docstrings, Elixir `@doc`) were not counted per se, only the commands that
  run them.
- Quality, not presence, is unmeasured: a lychee job that is allowed to fail counts the same as a gate.
- Global commit search returned nonsense dates for several queries (commits dated 2041, 2056 etc.); those
  were discarded. Only repo-scoped evidence is cited.

Frontier reconciliation (exhaustive-researcher Phase 2): 7 enumerated nodes (denominator, T1 to T5
techniques, evidence), 0 pending, 0 blocked at the end of the run; the report node was the last to close.
The blind spots above are limitations of method, recorded here rather than dropped.

## 1. Headline numbers (all / tools / libraries)

Presence of mechanisms (sampled repos; one line each; see section 3 for definitions):

| Mechanism | All (of 1254) | Tools (of 284) | Libs (of 970) |
|---|---|---|---|
| Any include/transclusion directive found in sampled docs | 8.5% (106) | 22.9% (65) | 4.2% (41) |
| ...among the 164 site-generator repos | 45.7% (75/164) | | |
| Generated-by comment/marker in a doc file | 3.6% (45) | 8.5% (24) | 2.2% (21) |
| Clean-tree assertion in CI (`git diff --exit-code` and kin) | 19.8% (248) | 29.6% (84) | 16.9% (164) |
| ...with docs/schema/CLI/changelog words near it | 7.3% (91) | 12.3% (35) | 5.8% (56) |
| Docs built in CI | 18.7% (235) | 32.0% (91) | 14.8% (144) |
| Docs build with warnings-as-errors/strict | 6.8% (85) | 20.1% (57) | 2.9% (28) |
| Any link checker (lychee, mlc, linkcheck, htmlproofer ...) | 9.1% (114) | | |
| Any spell checker (typos, codespell, cspell, misspell, aspell ...) | 13.0% (163) | | |
| Any markdown linter (markdownlint, mdformat, rumdl, dprint ...) | 10.2% (128) | | |
| Prose linter (vale, textlint, alex, write-good) | 2.4% (30) | | |
| Custom "check/verify/lint docs" command by name | 11.0% (138) | 25.0% (71) | 6.9% (67) |
| Docstring/API-doc lint (missing_docs, interrogate, jsdoc rules ...) | 8.1% (101) | 19.4% (55) | 4.7% (46) |
| CODEOWNERS present (depth 2) | 21.5% (269) | | |
| ...of those, one or more lines naming docs paths | 38.3% (103/269) | | |
| Markdown code blocks with test markers (`>>>`, `iex>`, `rust,ignore`, `scala mdoc`) | 5.2% (65) | 12.3% (35) | 3.1% (30) |
| CLI transcript/test crates (trycmd, snapbox, assert_cmd, rexpect) | 2.7% (34) | 8.5% (24) | 1.0% (10) |
| Changelog from fragments/tools (changesets, cliff, release-please, towncrier, changie) | 6.9% (87) | 16.5% (47) | 4.1% (40) |

Mechanism-count score (12 groups: include, generated marker, generated reference, markdown tests, CLI
tests, link check, prose/spell/mdlint, strict build, clean-tree, custom check, docs CODEOWNERS, changelog
tooling): 540 repos (43%) have none, 262 have one, 151 two, 105 three, 82 four, 55 five, 59 have six or
more (4.7%). So the typical widely-used repository has zero or one mechanism that keeps docs consistent
with code; the tail is tools, and within tools the Rust and Python ecosystems.

## 2. Ranked: what is most often done

Rank by share of the whole sample (a mechanism seen in 5% of repos is rare; "docs exist" is not here):

1. Clean-tree check in CI (19.8%) and docs built in CI (18.7%): the dominant freshness primitive is
   "regenerate, then fail if the tree is dirty" or "build the site, fail on error". Both are one shell
   line, language-agnostic, and need no new tooling.
2. Spell check (13.0%) then markdown lint (10.2%) then link check (9.1%): hygiene tooling, adopted in
   roughly one repository in ten each, mostly as lightweight CI jobs (typos is the Rust favourite, 37 of
   117 Rust repos; codespell the Python one, 23 of 95).
3. Custom named docs check (11.0%) and docstring lint (8.1%): bespoke scripts; this is where the strongest
   "docs mention things that exist" checks live (rust tidy, clippy `update_lints --check`).
4. Include/transclusion in docs (8.5% overall; 45.7% of site-generator repos): the most common
   single-sourcing mechanism by far, mostly Sphinx `include`/`literalinclude` and mdBook `include`.
5. Snapshot/golden update mechanisms (8.2%) and `.snap` files (7.7%): generated artifacts maintained by the
   test runner (insta, jest snapshots, go `-update`, rust `--bless`).
6. Generated-reference producers: Make docs/gen targets (8.6%), package.json docs/gen scripts (9.3%),
   xtask crates (1.4% overall, 13.7% of Rust repos), justfile (1.1%).
7. Changelog tooling (6.9%), doctests in markdown (5.2%), CLI transcript tests (2.7%).
8. Rare (each under 2%): prose linters (vale 0.9%), cspell (1.4%), include-region tools such as cog (0 of
   1254), markdown-magic (0), embedme (0), mdsh (0), cargo-rdme/cargo-readme (3 repos), Docusaurus
   raw-loader (3 repos).

Global code search shows the tail tools exist but are niche: files containing `[[[cog` 1,328; markdown-magic
`AUTO-GENERATED-CONTENT:START` 4,912; `<!-- embedme` 513; `<!-- cargo-rdme start` 2,504; cargo-sync-readme
400; mdsh 82; versus `{{#include` 41,920; `--8<--` 161,280; `.. include::` (rst) 847,872.

## 3. Technique by technique

Each subsection: prevalence, three named examples with paths, how freshness is enforced, what goes wrong.
Numbers in brackets are repos; "applicable" denominators are stated.

### 3.1 Inclusion and transclusion

Prevalence (union of README, sampled md, deep pass; all / tools / libs):

| Directive | All | Tools | Libs | Among repos with that generator |
|---|---|---|---|---|
| mdBook `{{#include}}` | 1.0% (13) | 2.1% (6) | 0.7% (7) | 30.8% (8/26 mdBook repos) |
| mdBook `{{#rustdoc_include}}` | 0.2% (2) | 0.7% | 0.0% | 7.7% (2/26) |
| MkDocs snippets `--8<--` | 0.7% (9) | 1.8% (5) | 0.4% (4) | 19.6% (9/46 MkDocs repos) |
| `pymdownx.snippets` enabled in mkdocs.yml | 2.2% (27) | 4.2% | 1.5% | |
| MkDocs `include-markdown` | 0.2% (3) | 0.7% | 0.1% | 6.5% (3/46) |
| mkdocs-macros plugin | 0.6% (7) | | | |
| Jinja/Liquid `{% include %}` | 0.8% (10) | 2.1% | 0.4% | |
| Docusaurus MDX import of `.md/.mdx` partial | 1.1% (14) | 1.4% | 1.0% | 41.7% (10/24 Docusaurus repos) |
| Docusaurus `raw-loader` | 0.2% (3) | 0.0% | 0.3% | |
| Sphinx `literalinclude` | 1.7% (21) | 5.3% (15) | 0.6% (6) | 28.8% (19/66 Sphinx repos) |
| Sphinx `include` / MyST `{include}` | 3.0% (37) | 9.2% (26) | 1.1% (11) | 51.5% (34/66) |
| AsciiDoc `include::` | 0.6% (7) | 1.1% | 0.4% | 2/4 Antora repos |
| Hugo `include`/`readfile` shortcode | 0.3% (4) | 1.4% | 0.0% | |
| VitePress `<<<` / `<!-- @include:` | 0.4% (5) | 1.4% | 0.1% | |
| cog (`[[[cog`) | 0.0% (0) | | | global: 1,328 md files |
| markdown-magic (`AUTO-GENERATED-CONTENT`) | 0.0% (0) | | | global: 4,912 files |
| embedme, mdsh | 0.0% (0) | | | global: 513, 82 files |
| Kotlin knit (`<!--- KNIT`, `TEST`) | 0.1% (1) | | | kotlinx.coroutines only |
| README copied/included into a docs site | 1.8% (22) | 5.3% (15) | 0.7% (7) | |

Examples (verified paths):
- mdBook include with generated source: `helix-editor/helix` `book/src/commands.md` contains
  `{{#include ./generated/typable-cmd.md}}` and `static-cmd.md`; those files are written by
  `cargo xtask docgen` (`xtask/src/docgen.rs`) and gated in `.github/workflows/build.yml` (see 3.2).
- mdBook `rustdoc_include` of real compilable listings: `rust-lang/book`
  `src/ch13-02-iterators.md` uses `{{#rustdoc_include ../listings/ch13-functional-features/listing-13-10/src/main.rs:here}}`
  (each listing is a Cargo project; the anchor is the name `here`). `FuelLabs/fuels-rs`
  `docs/src/` pages include named regions of compiled examples, e.g.
  `{{#include ../../../examples/contracts/src/lib.rs:add_custom_inputs_outputs}}`.
- MkDocs snippets with named sections: `pola-rs/polars` (`--8<-- "python/user-guide/expressions/folds.py:mansum"`
  under `docs/source/src/python/...`); `nlohmann/json` `docs/mkdocs/docs/api/*.md` (`--8<-- "examples/parse_event_t.cpp"`
  plus the program's `.output` file beside it); `astral-sh/uv` `docs/reference/contributing.md`
  (`--8<-- "CONTRIBUTING.md"`).
- Sphinx: `libuv/libuv` `docs/src/guide/processes.rst` (`literalinclude:: ../../code/spawn/main.c`, with
  `docs/code/CMakeLists.txt` building the examples); `numpy/numpy`
  `doc/source/reference/random/examples/numba.rst`; `pytest-dev/pytest` `doc/en/contributing.rst`
  (`.. include:: ../../CONTRIBUTING`).
- Docusaurus partials: `immich-app/immich` `docs/docs/guides/custom-locations.md` imports
  `/docs/partials/_compose-builder.mdx`; `reduxjs/redux` imports `../../components/_FundamentalsWarning`;
  `langflow-ai/langflow` imports `@site/docs/_partial-hidden-params.mdx`.
- README into site by include (not by script): `mkdocs/mkdocs`, `pdm-project/pdm`, `astral-sh/uv`
  (`--8<-- "CONTRIBUTING..."`), `celery/celery`, `pytest-dev/pytest`, `twisted/towncrier`, `fish-shell/fish-shell`
  (`.. include:: ../CONTRIBUTING`), `jj-vcs/jj` `docs/changelog.md` (include-markdown of `../CHANGELOG`),
  `juanfont/headscale` `docs/about/contributing.md`, `aria2/aria2` `doc/manual-src/en/README.rst`.
- Script-based README copies into docs: 0 verified. The 5 regex hits (`cp README.md ... doc/`) are all
  packaging (install README to `share/doc`), e.g. `sharkdp/bat` workflow, `aristocratos/btop` Makefile.
  README into a docs site is done by include directive or not at all in this sample.

How granular are includes? (counted over all fetched markdown)
- mdBook: 798 anchor includes, 260 whole-file, 13 line-range (anchors in 8 repos; line ranges in 3).
- MkDocs snippets: 464 named-section includes (2 repos, so heavily concentrated), 320 whole-file, 0 line
  ranges.
- Sphinx `literalinclude`: 216 whole-file, 205 marker-text (`:start-after:`/`:end-before:`), 91 `:lines:`, 13
  `:pyobject:` (symbol), across 18/6/3/2 repos respectively.
So where includes are non-trivial, named anchors or marker text dominate line numbers, with whole-file the
other common case. Line ranges survive mostly in Sphinx.

Freshness: transclusion makes the quoted text current by construction; what can go stale is the path or
anchor, and the prose around the quote. The only enforcement seen is the site build (broken path fails or
warns depending on the tool and strict flags: 6.8% of repos build with warnings-as-errors; tools 20.1%).
No surveyed mechanism ties the PROSE around an included snippet to the snippet's change.

What goes wrong (from issue trackers; titles quoted):
- pymdown-extensions: "Allow snippets to only show certain user defined lines from the included file"
  (#1462), "Snippets Notation does not work when inserting into a table using the `--8<--` syntax" (#2156),
  "Snippets support relative paths" (#1275): include resolution rules (base path, relative path, tables)
  are a recurring source of confusion.
- mdBook: "Be able to create runnable, editable snippets and include portions of the file" (#2643);
  "Show hidden lines functionality for non-rust files" (#1502): partial-file inclusion needs more than
  line numbers and hidden-line conventions.
- Docusaurus: "TOC does not work when importing one MDX into another" (#3915): included content is
  invisible to the including page's structure.
- Sphinx: "ROI: strip lines in literalinclude" (#2029), "Add an option in literalinclude to skip comments in
  code" (#7692): fragments need post-processing options that grow without bound.
- INFERENCE (no direct count): line-number includes break silently when the source file is edited; the
  near-absence of line ranges where an anchor option exists (13 of 1071 mdBook includes) is consistent
  with maintainers learning this.

### 3.2 Splice regions, generated markers, and single-sourcing README to crate docs

Region and marker prevalence (union md; denominators 1254/284/970):
- Generated-by/DO-NOT-EDIT comment in a doc file: 3.6% (45) / 8.5% / 2.2%.
- Begin/end splice regions other than TOC and contributors: 1.5% (19). TOC markers (doctoc and kin) 2.0%
  (25). all-contributors regions 0.6% (7).
- `cargo-rdme`/`cargo-sync-readme` start markers: 1 repo (`linera-io/linera-protocol`,
  `linera-storage-runtime/README.md`); cargo-readme template `README.tpl`: 3 repos (`nextest-rs/nextest`
  `cargo-nextest/README.tpl` and `nextest-filtering/README.tpl`; the other two are vendored `nodejs/node` deps and
  `istio/istio` `operator/cmd/mesh/readme.tpl`).
- Rust `#![doc = include_str!(...)]`: 17.0% of Rust repos with a lib.rs sampled (18/106); README specifically
  12.3% (13/106). Target mix over 55 occurrences: `README.md` 35, others are error-code docs
  (`B0001.md`...) and svg/xml assets.

Examples (verified):
- Spliced region inside a hand-written page: `astral-sh/ruff` `docs/configuration.md`
  (`<!-- Begin auto-generated command help. -->`, written by `crates/ruff_dev/src/generate_cli_help.rs`);
  `npm/cli` `docs/lib/content/commands/npm-whoami.md` (`<!-- AUTOGENERATED USAGE DESCRIPTIONS -->`);
  `rclone/rclone` `docs/content/swift.md` (`<!-- autogenerated options stop -->`, produced by the Makefile
  `backenddocs` target running `bin/make_backend_docs.py`; `commanddocs` runs `rclone gendocs`).
- Whole-file generated docs with a header: `cilium/cilium` `Documentation/cmdref/cilium-dbg_bpf_sha.md`
  ("autogenerated via cilium-dbg cmdref, do not edit"); `sveltejs/svelte`
  `documentation/docs/98-reference/.generated/server-errors.md`; `jdx/mise` `docs/cli/doctor.md`
  (`@generated by usage-cli from usage spec`); `moby/moby`
  `integration/network/bridge/iptablesdoc/generated/swarm-portmap.md`.
- Splice region in SOURCE code for a docs/lint list: `rust-lang/rust-clippy` uses
  `// begin lints modules, do not remove this comment, it's used in update_lints` and
  `<!-- begin autogenerated links to lint list -->` in `clippy_dev/src/generate.rs`; CI
  (`.github/workflows/clippy_dev.yml`) runs `cargo dev update_lints --check`.
- README to crate docs: `clap-rs/clap` `clap_builder/src/lib.rs`, `nushell/nushell` `crates/nu-cli/src/lib.rs`,
  `biomejs/biome` `crates/biome_cli/src/lib.rs` (all `include_str!("../README.md")`).
- Generated READMEs kept fresh by a TEST: `tigerbeetle/tigerbeetle` `src/clients/ruby/README.md`, generated
  by `src/scripts/client_readmes.zig` whose header says "Code generation is written as a test that checks
  that generated READMEs are fresh."

Freshness (the four patterns found, in decreasing frequency):
1. Generator with a check mode run in CI: ruff (`Mode::{Write,Check,DryRun}` in
   `crates/ruff_dev/src/generate_all.rs`, plus a `REGENERATE_ALL_COMMAND` constant reused in the error
   message); uv (`.github/workflows/check-generated-files.yml`: `cargo dev generate-all --mode dry-run`,
   `generate-json-schema --mode check`, `generate-sysconfig-metadata --mode check`);
   clippy (`update_lints --check`); rust-analyzer (`ensure_file_contents(cg, file, contents, check)` in
   `xtask/src/codegen.rs`, message "... was not up-to-date").
2. Regenerate then assert clean tree: helix (`cargo xtask docgen` then
   `git diff-files --quiet || (echo "Run 'cargo xtask docgen', commit the changes and push again" && exit 1)`,
   `.github/workflows/build.yml`); cargo (`ci/validate-man.sh`: require a clean `git status --porcelain` for
   `doc crates/mdman/doc etc/man`, run `cargo build-man`, fail with "Please run `cargo build-man` to rebuild
   the man pages and commit the changes").
3. Generator is itself a test that snapshots: `jj-vcs/jj` `cli/tests/test_generate_md_cli_help.rs` writes
   `cli/tests/cli-reference@.md.snap` (insta); the snapshot description says "AUTO-GENERATED FILE, DO NOT
   EDIT ... MkDocs includes this snapshot from docs/cli-reference.md"; tigerbeetle as above.
4. Do not commit the output: `astral-sh/uv` gitignores `/docs/reference/cli.md`, `environment.md`,
   `settings.md` ("use `cargo dev generate-all` to regenerate"), so only generator health is checked.
   `mermaid-js/mermaid` moved a generated page to build time in a 2026-09-29 commit ("docs: leave generated
   event modeling documentation to the build").

What goes wrong:
- Contributors forget; the fix is a follow-up commit. `helix-editor/helix` has repeated commits titled
  "Run 'cargo xtask docgen'" (two on 2026-07-04). The gate converts silent drift to a red CI plus a
  mechanical commit; it does not remove the cost.
- Checks get expensive or flaky: `astral-sh/uv` "Skip `cargo dev generate-all` test case in CI (#14972)".
- Generator defects look like doc defects: `jj-vcs/jj` "docs: Fix CLI reference TOC" (2026-07-30).
- A marker without a gate decays: most of the 45 generated-marker repos have a "do not edit" comment; only
  the subset that also has a check mode, clean-tree step or snapshot test is protected. Among repos with a generated-looking
  reference page (3.3), only 29.3% to 44.1% have a clean-tree CI step (CLI 36.0%, config 33.6%, env 33.3%,
  error index 29.3%, schema files 44.1%).
- Absent gate noticed later: `kestra-io/terraform-provider-kestra` issue #248 "ci: fail the build when
  generated docs are out of date"; `hrsh7th/nvim-cmp` #1018 "README and doc/cmp.txt are out of sync";
  `conda/conda-lock` #138 "Documented basic usage in README out of sync with released pypi version".
- README included as crate docs loses relative links and images on docs.rs: `webern/cargo-readme` #55
  "Support for intra-doc links"; skeptic: "Skeptic fails to find dependencies starting with Rust 1.77"
  (#141); doc-comment: "Skip/Exclude code block while checking" (#26).

### 3.3 Generated reference documentation

Prevalence of the reference TYPE (page exists) and of a producer signal (all / tools / libs):

| Reference | Page or artifact exists | Of those, a generator signal | Notes |
|---|---|---|---|
| CLI reference (strict path match: docs/.../cli, commands, command-line) | 9.1% (114); tools 17.3% (49) | 47.4% (54/114); tools 63% (31/49) | loose match 23.5% (295) |
| Config / settings reference | 12.1% (152); tools 25.7% (73) | 53.9% (82/152) | |
| Env var reference | 4.8% (60); tools 10.9% (31) | 55.0% (33/60) | |
| JSON Schema files committed | 12.8% (161); tools 19.7% (56) | 55.3% (89/161) | schema-generator signal in config 7.8% (98) |
| Rule/lint pages (dir of at least 5 doc files named rules/lints/checks/cops...) | 2.0% (25) | | lint/linter tools only |
| Error-code per-code pages | 0.4% (5) | | angular, nuxt, next.js, rust-lang/rust |
| Error index / reference page | 4.6% (58) | | noisy name match |
| Man pages in tree | 3.2% (40); tools 7.0% (20) | | |
| Shell completions dirs | 8.5% (106) | | completions are not docs |

"Generator signal" is a union of weak signals (clap_mangen/clap-markdown, cobra doc, sphinx-click/
argparse/pandoc/help2man/ronn/scdoc, schemars/json-schema tools, xtask crates, `gen-docs`-named scripts or
files, docs-gen commands); it overstates, and misses Go/JS generators that live in source files not
fetched. Read it as "about half of reference pages sit next to something that plausibly generates them".

Producers (how each is produced), all / tools / libs:
- dev xtask crate: 1.4% (18) overall; 13.7% of Rust repos (16/117); `cargo xtask`-style calls or aliases 3.3%
  (41). Examples: `astral-sh/uv` `crates/uv-dev/src/generate_*` (cli reference, env vars, options
  reference, preview features, json schema, sysconfig); `astral-sh/ruff` `crates/ruff_dev/src/generate_*`
  (cli help, options, rules table, docs, schema, and ty variants); `rust-lang/rust-analyzer`
  `xtask/src/codegen/{assists_doc_tests,diagnostics_docs,feature_docs,lints,grammar}.rs`.
- Make target (`docs`, `gen`, `generate`, `man`, `schema`, ...): 8.6% (108). Examples: `yt-dlp/yt-dlp`
  Makefile (`doc:`, man via pandoc), `langflow-ai/langflow` Makefile (`docs:`), `rclone/rclone` Makefile
  (`commanddocs`, `backenddocs`, `rcdocs`).
- package.json docs/gen script: 9.3% (117); justfile task: 1.1% (14; `jesseduffield/lazygit` `generate:`,
  `FuelLabs/sway`, `aaif-goose/goose` `generate-acp-schema:`).
- Snapshot/golden update mechanism (insta, expect-test, jest snapshots, go `-update`, rust `--bless`,
  syrupy): 8.2% (103); 4.7% (59) specifically Rust-style crates; `.snap` files 7.7% (97). Rust Cargo.toml
  (depth 2) dev-deps over 117 Rust repos: insta 26, pretty_assertions 25, assert_cmd 18, trybuild 12,
  snapbox 7, expect-test 4, trycmd 3; schemars 28, clap_mangen 7, clap-markdown 4.
- Doc-site plugin: MkDocs generator plugins (gen-files, mkdocstrings, mkdocs-click, include-markdown,
  macros) 1.4% (18; all MkDocs-config repos 46); Sphinx click/argparse extensions in 2.2% (27) including
  pandoc/man pipelines; Sphinx autodoc/autoapi/mkdocstrings/pdoc 3.7% (47; 33.7% of Python repos).
- CI job: workflows that call a generator then assert a clean tree: 7.3% (91) with docs-ish words nearby,
  14.9% (187) with generation words nearby (this includes lockfiles, format, `go mod tidy`; so it
  overstates doc relevance).

API reference (signal in config or workflows; denominators are per-language where meaningful):
- rustdoc (`cargo doc`, `package.metadata.docs.rs`, `RUSTDOCFLAGS`): 5.3% (66); 53.8% of Rust repos (63/117).
- typedoc/jsdoc/api-extractor: 5.3% (67); TypeScript 31.3% (25/80), JavaScript 18.6% (13/70).
- Sphinx autodoc/autoapi/napoleon, mkdocstrings, pdoc: 3.7% (47); Python 33.7% (32/95).
- Others (doxygen, javadoc, haddock, ex_doc, `mix docs`, dune `@doc`, godoc/pkgsite, dartdoc, docfx, DocC,
  scaladoc): 14.0% (175); Haskell 41.5% (22/53), OCaml 43.1% (22/51), Java 30.4% (17/56), C++ 29.5% (18/61),
  Python 18.9% (18/95). Doxyfile present 2.2% (27); DocC dirs 0.8% (10).

Rules, lints, error codes (hand-verified):
- `rust-lang/rust` `src/tools/tidy/src/error_codes.rs` (module comment): extract every error code from
  `compiler/rustc_error_codes/src/lib.rs`; require a long-form explanation under
  `compiler/rustc_error_codes/src/error_codes/`, whose doctest must fail with that code; require a UI test
  with `Exxxx.rs` and `Exxxx.stderr`; require the code to be emitted by the compiler. That is a full
  four-way consistency check between docs, tests and code.
- `astral-sh/ruff` `crates/ruff_dev/src/generate_rules_table.rs` and `generate_docs.rs` (file names only;
  bodies not read; INFERENCE that rule docs are generated from rule doc comments, consistent with the
  commit titles such as "Document `map`/generator exception behavior (`C417`)" touching docstrings).
- `rust-lang/rust-clippy`: lint list regions generated from lint declarations (3.2).
- `bevyengine/bevy` `errors/src/lib.rs` attaches `B0001.md`-style error docs to error types with
  `#[doc = include_str!("../B0001.md")]`.

Changelog from fragments (all / tools / libs):
- changesets (`.changeset/`): 1.4% (17); TypeScript 10% (8/80). Examples: `mermaid-js/mermaid`, `shadcn-ui/ui`,
  `mattpocock/skills`.
- git-cliff (`cliff.toml`): 1.5% (19); Rust 8.5% (10/117). Examples: `neovim/neovim` `scripts/cliff.toml`,
  `netdata/netdata` `packaging/cliff.toml`, `wezterm/wezterm` `termwiz/CHANGELOG.md`
  (`<!-- generated by git-cliff -->`).
- release-please manifest/config: 1.8% (23): `puppeteer/puppeteer`, `OpenHands/OpenHands`.
- towncrier-style fragment dirs: 2.2% (28, includes name collisions such as `docs/news`); towncrier config
  proper 0.7% (9). Fragment directory naming varies (numpy uses `doc/release/upcoming_changes`), so this is
  an undercount.
- changie/covector `.changes/`: 0.6% (7): `tauri-apps/tauri`, `FuelLabs/fuel-core`.
- union 6.9% (87), tools 16.5% (47); a root changelog file at all: 42.7% (535).

What goes wrong, beyond 3.2:
- Generators proliferate per reference type and each needs its own check wiring (uv's workflow has five
  separate "check" steps; ruff folds them into one `generate-all`).
- Rust nextest trap (INFERENCE from workflows): 31 Rust repos use nextest in CI; 12 of them also run
  `--doc`; 8 have neither plain `cargo test` nor `--doc` in the sampled workflows, so doctests (and README
  doctests via `include_str!`) may not run in CI at all. Workflow coverage is capped at 15 files, so this is
  an upper bound on the gap.

### 3.4 Docs that are tested

Prevalence (denominators per language where applicable):

| Mechanism | Prevalence | Notes |
|---|---|---|
| `cargo test` or nextest in CI | 73.9% of Rust repos with workflows (85/115) | `cargo test` runs doctests by default |
| Explicit `--doc` | 15.7% of those (18/115) | |
| README doctested through `include_str!` | 12.3% of Rust repos (13/106) | |
| skeptic / doc-comment crate / trybuild / mdbook-keeper | 1.9% (24); doc-comment dev-dep 6/117 Rust, trybuild 12/117 | |
| `mdbook test` in CI | 0.5% (6); 19.2% of mdBook repos (5/26) | |
| Markdown blocks with test markers | 5.2% (65): tools 12.3%, libs 3.1% | marker group includes Elixir `iex>` (12/52 Elixir repos for the whole marker group), `>>>` (29 repos; 11/95 Python), `rust,ignore/no_run` 17, `scala mdoc` 4 |
| Python `--doctest-glob/--doctest-modules`, sphinx doctest | 1.4% (18); 13.7% of Python repos (13/95) | |
| Python markdown-test tools (phmdoctest, mktestdocs, pytest-codeblocks, sybil, nbmake) | 0.5% (6) | |
| Go `example_test.go` | 29.0% of Go repos (29/100) | the single best-adopted docs-test convention |
| Go testscript (`.txtar`) | 0.6% (7) | |
| Haskell doctest / cabal-docspec | 17.0% of Haskell repos (9/53) | |
| CLI transcript crates (trycmd, snapbox, assert_cmd, rexpect) | 2.7% (34); 27.4% of Rust repos (32/117 by any signal); Cargo.toml (depth 2): assert_cmd 18, snapbox 7, trycmd 3 | |
| trycmd-style files/dirs (`tests/cmd`, `.trycmd`, `.stdout/.stderr`) | 4.4% (55) | |
| cram `.t` files / bats `.bats` | 1.8% (22) / 1.1% (14) | |
| `examples/` directory exists | 37.3% (468): tools 54.9% | |
| Examples built or tested in CI (explicit `--examples`, `--all-targets`, or "build/test examples") | 9.5% of repos with workflows (102/1074) | `cargo test` also builds examples implicitly |
| Not measurable | OCaml `(mdx)` stanzas (dune files not fetched), Kotlin knit, Go example bodies, Elixir `doctest` lines | |

Examples:
- Doctests over markdown through an include: the 13 Rust repos above (clap, nushell, biome, datafusion,
  ruff, tokio via `tests-integration/src/lib.rs` including `../../README`).
- Markdown executed by the doc build: `rust-lang/book` listings are compiled through `rustdoc_include` of
  real Cargo projects; `kotlin/kotlinx.coroutines` `docs/topics/*.md` use `<!--- TEST` markers (knit).
- CLI transcript tests: `jj-vcs/jj` (insta over `jj util markdown-help`), `rust-lang/cargo`
  `crates/mdman/tests/compare/expected/*.{1,md,txt}` (golden outputs for the man-page generator), cargo
  uses `ci/validate-man.sh` on top.
- Output committed next to example source: `nlohmann/json` `docs/mkdocs/docs/examples/*.cpp` with
  `.output`; the docs `Makefile` in that directory builds outputs and the workflow matrix has
  `ci_test_examples`, `ci_test_build_documentation`, `ci_test_documentation_mermaid`.

Freshness: doctest-style testing makes the CODE in docs executable (true by running) but not the prose;
it fails when an API changes, which is exactly the signal. Output goldens (`.output`, `.stdout`, `.snap`)
make CLI transcripts regenerate-and-review rather than hand-edit.

What goes wrong: skeptic's dependency resolution broke on Rust 1.77 (#141) and needs build.rs plumbing;
doc-comment has no way to skip a block (#26); trycmd/snapbox cannot do per-command cwd or stdin piping
without extra syntax (assert-rs/snapbox #43, #172); insta leaves `.snap.new` files and needs a review
command (insta #621, #886). Every "docs are tests" tool introduces its own ignore/skip dialect
(`rust,ignore`, `no_run`, `skip`) that itself must be audited.

### 3.5 Consistency and quality checks on docs

Prevalence (all / tools / libs; "applicable" where it matters):

| Check | All | Tools | Libs |
|---|---|---|---|
| Docs built in CI | 18.7% (235); 21.9% of repos with workflows (235/1074) | 32.0% | 14.8% |
| Strict/warnings-as-errors docs build (`mkdocs --strict`, sphinx `-W`, `RUSTDOCFLAGS -D`, `onBrokenLinks: throw`, `fail_on_warning`) | 6.8% (85) | 20.1% (57) | 2.9% (28) |
| ...among site-generator repos | MkDocs 32.6% (15/46), Sphinx 31.8% (21/66), Docusaurus 45.8% (11/24), mdBook 11.5% (3/26) | | |
| lychee | 2.1% (26) | 5.6% | 1.0% |
| markdown-link-check | 2.2% (28) | 3.9% | 1.8% |
| other link checkers (sphinx linkcheck, htmlproofer, muffet, linkinator, mdbook-linkcheck ...) | 7.4% (93) | 16.2% | 4.8% |
| ...any link checker | 9.1% (114) | | |
| Sphinx linkcheck among Sphinx repos | 50.0% (33/66) use some link checker | | |
| vale | 0.9% (11; 1.3% with `.vale.ini`/styles) | 3.2% | 0.2% |
| textlint, write-good, alex, remark-lint | 1.2% (15) | 2.8% | 0.7% |
| markdownlint, mdformat, rumdl, dprint, mado | 8.3% (104); config file 6.0% (75) | 16.9% | 5.8% |
| typos | 6.1% (77); `typos.toml` 5.2% | 13.7% | 3.9% |
| codespell | 4.7% (59) | 10.9% | 2.9% |
| cspell | 1.4% (18) | 3.5% | 0.8% |
| other spell tooling (misspell, aspell, pyspelling, hunspell) | 5.7% (71) | 15.5% | 2.8% |
| Custom "check/verify/lint docs" commands by name | 11.0% (138) | 25.0% | 6.9% |
| Custom checker scripts by file name (`scripts/check-docs...`) | 10.8% (136) | 20.1% | 8.1% |
| rust tidy (`src/tools/tidy`) | 0.6% (7) | | |
| Sphinx nitpicky / xref ratchet | 1.8% (22) | 5.3% | 0.7% |
| Docstring/API-doc lint | 8.1% (101) | 19.4% | 4.7% |
| CODEOWNERS with docs lines | 8.2% (103); 38.3% of the 269 repos with CODEOWNERS | 14.8% | 6.3% |
| Pre-commit with docs/gen hooks | 3.7% (47) | 8.1% | 2.5% |
| Freshness by clean-tree assertion | 19.8% (248) | 29.6% | 16.9% |

Docs-mention-things-that-exist checks (the category frob cares most about), verified:
- `rust-lang/rust` tidy `error_codes.rs` (error code docs, tests and emission), plus the unstable-book
  feature check in tidy (`features.rs`; 29 commits mention tidy and the unstable book in a repo-scoped
  search; I did not read the check body beyond its `unstable_book` references).
- `rust-lang/rust-clippy`: lint list files and docs regions checked with `cargo dev update_lints --check`.
- `python/cpython` `Doc/tools/check-warnings.py` and `Doc/tools/.nitignore`: run Sphinx in nit-picky mode
  (unresolved references) and compare to a baseline file. It has `--fail-if-regression` (new warnings in
  files not on the ignore list) AND `--fail-if-improved` ("Congratulations! You improved ... Please remove
  from Doc/tools/.nitignore"), plus `--fail-if-new-news-nit` with a numeric threshold
  (`NEWS_NIT_THRESHOLD = 8550`). A ratchet in both directions.
- `rust-lang/book` `ci/validate.sh` runs `link2print` over every `src/*.md` to verify references;
  `ci/spellcheck.sh` runs aspell with a project dictionary and a CI "list" mode.
- `django/django` `.github/workflows/docs.yml`: `make lint`, `make black` (code in docs) and
  `SPHINXOPTS="-q -W" make spelling`; `docs/spelling_wordlist` is curated by repeated "Removed unused and
  unnecessary words from docs/spelling_wordlist" commits (2021, 2022, 2024).
- `mermaid-js/mermaid`: `pnpm run docs:verify` in `.github/workflows/lint.yml` (docs are generated from
  `packages/mermaid/src/docs` into `docs/`); a dedicated workflow diffs `README.md` against `docs/README.md`
  and fails if they differ ("Make sure that README.md and docs/README.md are in sync"; the workflow cites
  eslint-plugin-userscripts as its model); `.github/lychee.toml` for links.
- `nlohmann/json` `docs/mkdocs/Makefile`: `style_check` (a structure script), `check_mermaid`, `link_check`,
  `link_check_markdowns`; `.github/workflows` matrix runs `ci_test_examples`.
- `cilium/cilium` `Documentation/check-links.sh` (sphinx `-b linkcheck`, with a filtered warning list),
  `Documentation/spelling_wordlist.txt`, `Documentation/update-spelling_wordlist.sh`, and a "docstest"
  contributor page.
- `kubernetes/kubernetes` shared bash helper `kube::verify::generated` used by several verify scripts
  (commits "Make verify-vendor use verify::generated").

"Keep in sync" lives in comments: 164 repos (13.1%; tools 78/284) have a "keep in sync / also update /
must match" style comment in config, scripts or workflows. Docs-specific ones are a smaller subset (loose
regex, up to 23 repos, 1.8%), e.g. `python/cpython` `Doc/conf.py` ("Keep this version in sync with ..."),
`prometheus/prometheus` `CODEOWNERS` ("Please keep this file in sync with the MAINTAINERS.md"),
`jj-vcs/jj` ci.yml ("If you bump the version, also update docs/contributing.md and all other workflows that
install uv"). This is the hand-maintained form of "paired sections that must be re-read together": common,
unchecked, and living in comments.

What goes wrong:
- False positives and noise are the standing cost: `crate-ci/typos` has 172 issues matching "false
  positive"; markdownlint false positives on anchors (MD051, #570, #830) and LaTeX (MD037, #597); lychee
  needs anchor support (#185) and per-host rate limiting (#1605) to stop 429 failures; cspell users ask for
  larger dictionaries (#66). Every project carries a wordlist or ignore file that must be curated
  (django, cilium, rust-lang/book).
- Link checks flake because they depend on the network: this is why the best setups run them on a schedule
  or non-blocking (INFERENCE: not directly measured; lychee cache and rate-limit options exist for it).
- Prose linting is rare (0.9% vale) and mostly in tool projects with a dedicated docs team.
- Baselines drift: cpython needed the double-sided ratchet because a one-sided baseline only grows.

### 3.6 Duplicated text

Method: 60 repositories with docs sites (random, seeded, 24 tools and 36 libraries; 15 Python, 9 TypeScript,
6 Rust, 5 C, 4 Go ...), up to 160 doc files each (7146 files read; 22 repos fully covered, 31 repos have 160
or fewer doc files). Paragraphs: prose blocks (code fences, headings, tables, front matter, comments
removed), at least 100 characters and 15 words, normalized (lowercase, links to text, punctuation removed).
A cluster is the same normalized paragraph in two or more files of the same repository. 74,373 paragraphs
were examined.

Results:
- 54/60 repositories (90%) contain at least one duplicated paragraph cluster outside whole-file mirrors;
  57/60 if mirrors are counted.
- 27/60 repositories (45%) contain at least one whole-file mirror pair (at least 80% of the smaller file's
  paragraphs shared): 467 pairs in total (first 12 per repo categorized below).
- After removing mirror pairs: 923 clusters, covering 2,277 paragraph occurrences (3.1% of paragraphs).
  By class (clusters): hand-copied across directories 418 (36 repos), hand-copied between sibling pages 179
  (38 repos), README-versus-docs copies 142 (22 repos), changelog/release-note repeats 101 (14 repos),
  generated 32 (7 repos), 5+ file template boilerplate 31, versioned snapshot 11, boilerplate (license,
  conduct) 4, translation 5.
- Hand-copied (sibling + cross-dir + README-vs-docs): 739 clusters in 51/60 repos (85%); median 3.5 per
  repo (tools 3.5, libs 3.5), mean 12.3, 16 repos with 10 or more, 4 with 50 or more (max 111), 9 repos
  with none. Of the 22 fully covered repos, 20 have at least one (91%); median 3.5.
- Diverged near-copies (same first 10 and last 6 words, different middle), excluding versioned, translated
  and agent-instruction directories: 196 groups in 39/60 repos. Spot check of four: two true edited copies
  (mkdocs-material `docs/upgrade.md` versus `docs/changelog/index.md`; mocha blog posts), two excerpts or
  parallel text (OPA wasm page versus blog; mermaid gantt versus classDiagram), so precision is about half;
  treat as an upper bound on drift.

Whole-file mirrors, by class (144 recorded pairs; 33 had a copy/sync command mentioning the directory in
the repo's scripts or workflows, a lenient test, so at least 77% have no visible sync mechanism):
- docs versus site/other dir 42 pairs in 11 repos: `mermaid-js/mermaid` `docs/syntax/*.md` versus
  `packages/mermaid/src/docs/syntax/*.md` (generated; verified gate `docs:verify`; sync found);
  `jj-vcs/jj` `docs/*.md` versus `web/docs/src/content/docs/*.md` (no sync mechanism found);
  `delta-io/delta` `docs/src/content/docs/delta-kernel-java.mdx` versus `kernel/USER_GUIDE.md` (sync
  mention found).
- versioned snapshots 29 pairs in 3 repos (jest `website/versioned_docs/version-*`, langflow, SynapseML):
  intentional, by design.
- agent-instruction directories 21 pairs in 2 repos: `coollabsio/coolify` identical
  `.agents/skills/...`, `.claude/skills/...`, `.cursor/skills/...` files; `D4Vinci/Scrapling`
  `agent-skill/Scrapling-Skill/references/*` versus `docs/*` (90% overlap). No sync mention. This is a
  new, fast-growing source of copies.
- changelog/release/blog 20 pairs in 6 repos (`unclecode/crawl4ai` `docs/blog/release-v0.9.2.md` versus
  `docs/md_v2/blog/releases/v0.9.2.md`).
- root file copies 17 pairs in 8 repos (README, CODE_OF_CONDUCT, CONTRIBUTING, SECURITY copied into docs);
  templates/examples 13 pairs in 4 repos (`strapi/strapi` template READMEs); translation 2.
- Generated or included duplicates were excluded by construction (an include is not a copy in the source
  text); the generated class above is paragraphs found in files with a generated marker.

Interpretation: duplicate text is the norm, not the exception, and most of it is hand-copied with no guard.
The single guarded example found in this sample is mermaid (generated tree plus a `docs:verify` gate plus
a README diff workflow). The agent-instruction mirror class did not exist in the earlier decade of docs
practice and is increasing.

## 4. What the best-run projects do

A heuristic score (the 12 mechanism groups above, count of groups present) ranked the sample; the top
(10 of 12: `astral-sh/ruff`, `cilium/cilium`; 9: `zeroclaw-labs/zeroclaw`, `apache/datafusion`; 8:
`astral-sh/uv`, `python/cpython`, `traefik/traefik`, `apache/airflow`, `DioxusLabs/dioxus`, `pnpm/pnpm`,
`linera-io/linera-protocol`, `jj-vcs/jj`, `ankitects/anki`). The score is crude (it counts presence), so
the shared practices below come from reading the verified sources, not from the score alone.

Common to the best-run (ruff, uv, jj, helix, rust-analyzer, cargo, clippy, rust, tigerbeetle, mermaid):
1. A SINGLE canonical source per fact and a generator, not a hand copy: CLI help (clap definitions), option
   docs (struct doc comments and a schema), lint docs (lint doc comments), error docs (code registry).
2. ONE entry point that regenerates everything (`cargo dev generate-all`, `cargo xtask codegen`,
   `cargo build-man`, `cargo dev update_lints`) with three modes: write, check/dry-run, print. The error
   message names the exact command to run (ruff `REGENERATE_ALL_COMMAND`; cargo "Please run `cargo
   build-man`"; helix "Run 'cargo xtask docgen', commit the changes and push again").
3. Freshness is a CI failure, not a review comment: generator check mode, clean-tree, or a snapshot test.
4. Generated text carries a marker and, where possible, lives in its own file or its own marked region
   (jj snapshot description, cilium `cmdref/`, svelte `.generated/`), so humans do not edit it.
5. Doc examples are real code that compiles or runs: rust-lang/book listings, doctests through
   `include_str!` README, nlohmann `.cpp` plus `.output`, error-code docs with failing doctests (tidy).
6. Baselines are ratchets: cpython `.nitignore` shrinks only (fail on regression and on improvement);
   Rust tidy keeps `EXEMPT_FROM_DOCTEST` / `EXEMPTED_FROM_TEST` lists that only shrink.
7. Optional: do not commit the generated output at all (uv, mermaid moving that way) and verify only that
   the generator succeeds and the site builds strictly.

What the best-run do NOT do: prose linting with style guides (vale appears in 9 tool repos total), include
tools beyond the site generator's own directive, or per-paragraph provenance tracking. None of them check
that prose around an included or generated block is still true.

## 5. Recommendations for frob

Mapping each planned mechanism to evidence. Design numbers are suggestions with the measured basis.

### 5.1 Include regions with a check

- Make the include region a named region, not a line range. Evidence: mdBook 798 anchor versus 13 line-range
  includes; MkDocs snippets 464 sections versus 0 line ranges; Sphinx `:start-after:` 205 versus `:lines:`
  91. Also support whole-file (260 mdBook, 320 snippets, 216 literalinclude).
- Region identity rule: a region name must exist exactly once in its source file, in a recognized comment
  form; `frob check` fails on missing file, missing or duplicate name, or empty region. (The site builders
  mostly warn; only 6.8% of repos run strict builds, so frob supplies the gate the tools lack.)
- Record a content hash of each region in the including document's lockfile entry, so a changed region marks
  the including prose as "needs re-read" (see 5.2). No surveyed tool does this: transclusion keeps quotes
  current but not the prose around them (INFERENCE from absence).
- Do not build a plugin zoo: the same four concepts (include file, include named region, include lines,
  include symbol) cover Sphinx, mdBook, MkDocs, Docusaurus and AsciiDoc. Directives differ but
  semantics do not; frob should read the existing directives (`{{#include}}`, `--8<--`, `literalinclude`,
  `include::`, MDX imports) as pointers and validate them, rather than invent a fifth syntax first. Existing
  directive use is concentrated: 45.7% of site-generator repos have at least one.
- Offer the Rust README/crate-doc case natively: `include_str!` single-sourcing exists in 12.3% of Rust repos
  with a lib.rs, and its relative-link problem (cargo-readme #55) is the failure to design around.

### 5.2 Paired sections that must be re-read together

- Evidence that the need is real: 164 repos (13.1%) already carry "keep in sync / also update" comments in
  config and scripts, e.g. cpython `Doc/conf.py`, prometheus CODEOWNERS, jj ci.yml. They are unchecked and
  scattered.
- Evidence of cheap partial solutions: CODEOWNERS docs lines (38% of CODEOWNERS files have one; ownership
  makes the pairing a review rule), mermaid's README diff workflow (guards one pair), clean-tree checks
  (guards derived pairs).
- Recommendation: a first-class pair declaration (both ends carry a stable id; frob stores the hash of each
  end at the last acknowledged state; if one end changed and the other did not, `frob check` reports the
  pair and `frob ack` records the re-read). This generalizes the comment convention, lets the tool compute
  staleness by hash rather than by hope, and covers the frequent doc-versus-config and doc-versus-workflow
  pairs that no generator can derive.
- Combine with 5.1: a region used by N documents creates N implicit pairs; regenerated regions create a pair
  with their generator's source; so one mechanism covers three situations.

### 5.3 Checked fact references (CLI flags, config keys, rule ids, paths)

- What exists: generators emit reference pages from canonical sources (ruff/uv options and CLI from clap and
  struct docs; jj `docs/config-schema.json`; 28/117 Rust repos use `schemars`; 161 repos commit a JSON
  Schema). The step that is missing everywhere in the sample is the CHECK that hand-written prose which
  mentions a flag, key or rule id mentions one that still exists: the only comparable checks are bespoke
  (rust tidy error codes, clippy lint list, cpython nit-picky references). 11.0% of repos have any
  custom docs check; none of the verified ones validates inline mentions of flags.
- Recommendation: a typed reference syntax in docs (for example a inline marker naming kind and id:
  `cli-flag`, `config-key`, `rule-id`, `path`, `symbol`, `error-code`) and one resolver per kind that reads
  the canonical source frob already knows how to harvest (clap-derived help, JSON Schema, rule registry,
  the file tree). Path references are the cheapest and should ship first (the tree is already indexed).
- Mandatory false-positive control: borrow the cpython ratchet. Unresolved references listed in a baseline
  file; fail on any new unresolved reference AND fail when a baseline entry resolves (so the baseline only
  shrinks). Without this, typos (172 false-positive issues), markdownlint (MD051) and lychee (#185) show
  what unchecked heuristics cost.
- Make "regenerate" the one fix: if the canonical source is a generated artifact, the resolver reads the
  artifact and the error message prints the generation command (ruff, cargo, helix pattern).
- Prefer harvesting from the generator's input rather than its output when both exist (schema over rendered
  page), so a stale generated page cannot launder a stale reference.

### 5.4 Single canonical definitions with near-duplicate detection

- Evidence: 90% of docs-site repos have duplicated paragraphs; 85% have hand-copied clusters (median 3.5,
  mean 12.3 per repo); 45% have whole-file mirrors; at least 77% of mirrors have no visible sync mechanism;
  agent-instruction directories are the newest mirror class.
- Recommendation: normalized paragraph hashing (lowercase, links to text, punctuation stripped; at least
  100 characters and 15 words) over the doc set, plus whole-file similarity (80% paragraph overlap), run in
  `frob check`. In this study the same pass over 7146 files took under a minute in plain Python, so it is cheap enough for every
  check run.
- Triage classes taken from the data, to avoid noisy alarms: exempt versioned-docs directories and
  translation directories; treat generated files (marker or declared output of a generator) as non-
  duplicates; classify agent-instruction mirrors separately with a "declare a canonical file and generate
  the others" fix; report README-versus-docs overlap as "include it" (the include directive exists in every
  site generator and appears in 22 repos already); report diverged near-copies (same head and tail,
  different middle) as drift candidates, with the caveat that precision was about 50% here, so rank them
  below exact duplicates.
- Fix suggestions should be mechanical: replace the second copy with an include of the canonical region
  (5.1), or declare the pair (5.2) when two statements must stay separate.
- Single canonical definition means one place per fact (a glossary term, a flag description, a config key);
  the dedupe check finds where that is violated; the typed references (5.3) point to the canonical place.

### 5.5 Cross-cutting

- Treat "generated" as a first-class state: a region or file declares its producer command and a mode that
  checks without writing. 19.8% of repos assert a clean tree after regenerating but only a minority
  identify what was regenerated; frob can do better by knowing the producer per region.
- Offer both committed and ephemeral generated docs (uv versus ruff/helix patterns): committed requires
  equality; ephemeral requires the generator to succeed.
- Do not ship prose-lint, spell-check or link-check implementations: they are adopted by single-digit
  percentages, are noisy, and are better delegated to typos, codespell, lychee. Do provide the glue
  (hooks, ratchet baselines).
- Expect Rust and tool projects first: 61.6% of tools show a generator signal versus 29.5% of all repos
  (composite signal), and the best-run examples are Rust xtask or dev crates. A frob that fits an
  xtask-style entry point (`generate`, `check`) will match the existing habit.

## 6. Top ten findings

1. The sample's median repository has zero or one doc-consistency mechanism: 43% have none of 12 groups; 4.7% have six or more, and those are tools.
2. Clean-tree-after-regenerate is the dominant freshness primitive: 19.8% of repos (29.6% of tools); a generator check mode is the best form (ruff, uv, clippy, rust-analyzer).
3. Includes are common only where a site generator exists: 45.7% of 164 site-generator repos, 8.5% of all repos; Sphinx include (51.5% of Sphinx repos) and mdBook include (30.8%) lead.
4. Where includes are non-trivial, named anchors win over line numbers: mdBook 798 anchors versus 13 line ranges; MkDocs 464 sections versus 0 line ranges.
5. Marker-region tools (cog, markdown-magic, embedme, mdsh) appear in 0 of 1254 repos; generated-by comments appear in 3.6% (45) and only some have any gate.
6. About half of CLI, config, env and schema reference pages sit next to a generator signal (46.6% to 55.3%); the best repos put all generators behind one command with write, check and print modes and print the regenerate command in the failure.
7. Doctests are the best-adopted docs test in languages that bake them in (Go example files 29% of Go repos; Rust cargo test 74% of Rust repos with workflows; README doctested via `include_str!` 12.3%); 8 of 31 Rust nextest users appear to skip doctests in CI.
8. Hand-copied duplicate text is near-universal in docs sites: 85% of 60 sampled sites have hand-copied paragraph clusters (median 3.5, mean 12.3 per repo), 45% have whole-file mirrors, at least 77% of mirrors have no visible sync; AI agent instruction directories are a new mirror class.
9. Docs-versus-code existence checks are bespoke and rare (11% any custom docs check; rust tidy error codes, clippy lint list, cpython nit-picky ratchet are the models); "keep in sync" pairs live unchecked in comments in 13.1% of repos.
10. Hygiene tools are single-digit adoption and noisy (any link check 9.1%, any spell check 13.0%, vale 0.9%); the one robust noise-control pattern is cpython's baseline that must shrink, which frob should copy for fact references.

## 7. Reproducibility

All under `<scratchpad>/docgen/`:
`10_fetch.py` (configs, scripts, lib.rs, md sample), `11_analyze.py` (feature regexes; the overrides block
after the precision audit is authoritative), `12_stats.py`, `13_codesearch.py` -> `codesearch.json`,
`14_dupfetch.py` -> `full/`, `15_deep.py` -> `deep/`, `16_lang.py` (per-language), `17_deep_analyze.py`,
`18_examples.py`, `19_md.py` -> `mdhits.json` (union markdown features), `20_evidence.py`,
`20b_evidence.py` -> `evidence.json`, `evidence2.json`, `21_final.py` -> `final_stats.txt`, `22_dups.py` ->
`dups.json`, `23_score.py` -> `scores.json`, `24_cross.py`, `getf.sh` and `ex/` (hand-read exemplar files),
`frontier.tsv` (the external frontier store). Earlier data from
`<scratchpad>/docs/`.
Resumable: every fetch step skips files it already has.

Precision notes per feature (audited by sampling matched text): `-update`-style snapshot flags and
`stale`/`up to date` words were noisy and were removed or narrowed before the figures above; `cog`,
`markdown-magic`, `embedme`, `mdsh` had one false positive (`cog-person`) that was discarded; `inc_mdx_import_code`
(`<CodeBlock`) matched at least one planning document and is not quoted as a figure; towncrier fragment
paths collide with `docs/news`; "generator signal" in 3.3 is a union of weak signals.
