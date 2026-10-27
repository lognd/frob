# Documentation strategy research for frob v2

Scope: how mature Rust (and Rust-built Python) tools document themselves,
what the rustdoc conventions actually are, where rationale and incident
narrative should live, and an opinionated recommendation for the frob v2
workspace (frob, grimble, crunk over shared gob-* crates).

Driving problem from v1: source files carried multi-paragraph ticket
narrative (T-#### incidents, rationale, history). It rotted, bloated code,
and was never read. The fix is structural: give each kind of knowledge one
home, generate what can be generated, and lint the boundary.

## 1. rustdoc conventions

### 1.1 Shape of a doc comment

| Element | Convention | Source |
|---|---|---|
| First line | One-sentence summary, third person, no trailing "This function..." boilerplate; rustdoc uses it in item listings | https://doc.rust-lang.org/rustdoc/how-to-write-documentation.html |
| Then | Blank line, then free-form detail (what it does, invariants, when to use) | same |
| Section headers | Top-level `#` headings, canonical names: `# Examples`, `# Panics`, `# Errors`, `# Safety`, plus `# Aborts`, `# Undefined Behavior` | RFC 1574: https://rust-lang.github.io/rfcs/1574-more-api-documentation-conventions.html |
| Section order | Examples first is std practice; Panics/Errors/Safety after | std convention, RFC 1574 |
| Examples | Almost every public item; they compile and run as doc tests | C-EXAMPLE: https://rust-lang.github.io/api-guidelines/documentation.html |
| Errors/Panics/Safety | Required when applicable, including on trait methods that permit the behavior | C-FAILURE, same page |
| Links | Prose links to related items via intra-doc links (`[`Foo`]`, `[`Self::bar`]`, `[`crate::x::Y`]`) | C-LINK, same page; https://doc.rust-lang.org/rustdoc/write-documentation/linking-to-items-by-name.html |
| Crate docs | Thorough crate-level `//!` with an example and a map of modules | C-CRATE-DOC |
| Metadata | `Cargo.toml` has `documentation`, `repository`, `readme`, `keywords`, `categories` | C-METADATA |
| Release notes | Every release documented | C-RELNOTES |

Checklist view of all C-DOC items: https://rust-lang.github.io/api-guidelines/checklist.html

### 1.2 Doc tests

Reference: https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html

| Need | Mechanism |
|---|---|
| Run them | `cargo test --doc` (included in plain `cargo test` for lib crates) |
| Hide setup lines | Prefix with `# ` (render-hidden, still compiled) |
| Use `?` | Hidden `# fn main() -> Result<(), E> {` / `# Ok(()) }` or trailing `# Ok::<(), E>(())` |
| Network/FS examples | ` ```no_run ` compiles but does not execute |
| Negative examples | ` ```compile_fail ` and ` ```should_panic ` |
| Pseudocode | ` ```ignore ` (avoid; prefer `no_run`) |

Note: binary crates do not get doc tests run. For CLI products, put
testable examples on the library crate (`frob-core`-style `lib.rs`), and
keep `main.rs` thin.

### 1.3 Lints and attributes

| Item | Use |
|---|---|
| `#![warn(missing_docs)]` | Every public item must have docs. Bevy ratcheted this crate by crate: https://github.com/bevyengine/bevy/issues/3492 |
| `#![deny(rustdoc::broken_intra_doc_links)]` | Fail `cargo doc` on a dead `[`Foo`]` link. Set workspace-wide in `[workspace.lints.rustdoc]` |
| `rustdoc::private_intra_doc_links`, `rustdoc::bare_urls`, `rustdoc::missing_crate_level_docs` | Also worth enabling; see https://doc.rust-lang.org/rustdoc/lints.html |
| `#[doc = include_str!("../README.md")]` | Crate README is the crate doc; one source. README code blocks become doc tests, so write them to compile |
| `cargo-rdme` | Inverse direction: generate README from `lib.rs` docs, `cargo rdme --check` in CI. https://github.com/orium/cargo-rdme |
| `cargo-sync-rdme` | Same idea plus intra-doc link resolution via rustdoc JSON. https://lib.rs/crates/cargo-sync-rdme |
| `#[doc(hidden)]` | Public-for-macros or semver-exempt items; keeps them out of rendered docs |
| `#[doc(alias = "...")]` | Search aliases (e.g. `#[doc(alias = "gitignore")]` on an exclude option) |
| `#[cfg_attr(docsrs, doc(cfg(feature = "x")))]` | Feature badges; nightly-only via `#![cfg_attr(docsrs, feature(doc_cfg))]`. Tokio's pattern: https://github.com/tokio-rs/tokio/issues/4163 |
| `[package.metadata.docs.rs] all-features = true; rustdoc-args = ["--cfg", "docsrs"]` | Tells docs.rs to build with all features and the `docsrs` cfg. https://users.rust-lang.org/t/how-to-document-optional-features-in-api-docs/64577 |
| Local docs.rs parity | `cargo +nightly docs-rs` (cargo-docs-rs); Bevy adopted it for dev docs: https://github.com/bevyengine/bevy/pull/14350 |
| `cargo doc --no-deps --document-private-items` | For internal crates (gob-*), private items matter to contributors; build them in CI |

Decision for frob v2: include_str the README into `lib.rs` (README is
the human-written front page; rustdoc follows) rather than cargo-rdme (the
reverse). Reason: READMEs are read on GitHub and crates.io far more than
lib docs, and `include_str!` needs no extra tool in CI.

## 2. How the reference projects document

### 2.1 Site generators and structure

| Project | Generator | Written pages | Generated pages | Where architecture lives | Source |
|---|---|---|---|---|---|
| ruff | mkdocs-material, `mkdocs build --strict`; README transformed into index by `scripts/generate_mkdocs.py` | tutorial, configuration prose, FAQ, formatter docs | `docs/rules/*.md` (one per rule from `#[derive(ViolationMetadata)]` + doc comment), `docs/settings.md` (OptionsMetadata), CLI help section via `generate_cli_help`, `ruff.schema.json` | `CONTRIBUTING.md` + `docs/contributing.md`; crate-level `//!` docs | https://docs.astral.sh/ruff/contributing/ ; https://github.com/astral-sh/ruff/tree/main/crates/ruff_dev/src |
| uv | mkdocs-material; same `docs/` + `reference/` split (Commands, Settings) | concepts, guides | `docs/reference/cli.md`, `docs/reference/settings.md`, `uv.schema.json` | `docs/reference/` + in-crate `//!` | https://docs.astral.sh/uv/reference/ ; https://github.com/astral-sh/uv/blob/main/mkdocs.yml |
| ty | mkdocs-material (docs.astral.sh/ty), sources in the ruff monorepo | | `generate_ty_cli_reference`, `generate_ty_options`, `generate_ty_rules`, `generate_ty_env_vars_reference`, `generate_ty_schema` | | ruff_dev listing above |
| cargo | mdbook: The Cargo Book (`src/doc`), man pages from markdown via `mdman`, Contributor Guide (`src/doc/contrib`) published separately | all three | man pages -> markdown -> also embedded in `cargo help` | `src/doc/contrib/src/architecture/` | https://doc.crates.io/contrib/ ; https://github.com/rust-lang/cargo/blob/master/CONTRIBUTING.md |
| rust-analyzer | mdbook (`docs/book`), was `docs/dev/*.md` | `contributing/{architecture,style,syntax,guide,debugging,testing,setup,lsp-extensions}.md` | `*_generated.md` for assists, configuration, diagnostics, features via `cargo xtask codegen` / sourcegen tests | `contributing/architecture.md` (the canonical ARCHITECTURE.md) | https://rust-analyzer.github.io/book/contributing/architecture.html ; https://github.com/rust-lang/rust-analyzer/tree/master/docs/book/src/contributing |
| rustc | mdbook rustc-dev-guide, separate repo synced in | everything | none | whole book is architecture | https://rustc-dev-guide.rust-lang.org/ |
| tokio | docs.rs only (no site for API); tokio.rs is a tutorial site | tutorial on tokio.rs | API on docs.rs with feature badges | module-level `//!` essays (e.g. `runtime`, `sync`) | https://docs.rs/tokio |
| bevy | docs.rs + dev-docs.bevy.org (every main commit), bevy.org book | Bevy Book, examples README generated from `Cargo.toml` metadata | `examples/README.md`, release notes and migration guides compiled from fragments | `docs/` folder in repo + CONTRIBUTING | https://bevy.org/learn/contribute/helping-out/writing-docs/ |

Key ruff detail (verified in `generate_all.rs`): a single `Mode` enum
`{ Write, Check, DryRun }` shared by every generator; `Check` "doesn't
write to the file, checks if the file is up-to-date and errors if not".
Generators invoked by `cargo dev generate-all`: `generate_json_schema`,
`generate_ty_schema`, `generate_cli_help`, `generate_docs`,
`generate_ty_options`, `generate_ty_rules`, `generate_ty_cli_reference`,
`generate_ty_env_vars_reference`. Rule docs and options tables come from
derive macros (`ViolationMetadata`, `OptionsMetadata` in
https://docs.rs/ruff_options_metadata). The `#[deprecated]` attribute on
an option flows into schema, docs, and `ruff config` output
(https://github.com/astral-sh/ruff/pull/8035). This is exactly the
derive-first model frob v2 already has.

rust-analyzer detail: config docs are generated from the doc comments on
the `config!` macro fields; feature docs are generated by scanning
`// Feature: Name` comment blocks in source; a test fails if the generated
file differs (sourcegen pattern), so "docs drift" is a red test, not a
separate CI job. https://github.com/rust-lang/rust-analyzer/blob/master/docs/book/README.md

### 2.2 Where rationale lives

| Project | Code comments | Commit / PR | Docs | Notes |
|---|---|---|---|---|
| rust-analyzer | "Style inline code comments as proper sentences." Style guide entries each carry a `**Rationale:**` paragraph; architecture.md states "Architecture Invariant:" sentences | PR title from the user's perspective ("Make goto definition work inside macros", not "Use original span for FileId"); `feat:`/`fix:`/`internal:`/`minor:` prefix drives the weekly changelog | `style.md` is the ADR substitute: durable rules + why | https://rust-analyzer.github.io/book/contributing/style.html |
| matklad ARCHITECTURE.md | none | | Bird's-eye overview, codemap naming important files/types, "Architecture Invariant" sentences (often absences: "X never imports Y"), cross-cutting concerns; do not link to code lines, name symbols instead; revisit a few times a year | https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html |
| cargo | Short `// Note:` comments; `FIXME(#issue)` | Detailed PR descriptions; unstable features link tracking issue | `src/doc/contrib/src/architecture/*.md`, `unstable.md` lists each feature with its tracking issue | https://doc.crates.io/contrib/ |
| rustc | `// FIXME(#NNNN)` and `// FIXME(feature_name)`; stabilization requires clearing them | Tracking issue per feature/breaking change holds the narrative | rustc-dev-guide chapters | https://rustc-dev-guide.rust-lang.org/bug-fix-procedure.html |
| Google style | `TODO: crbug.com/192795 - Investigate cpufreq optimizations.` -- a link to a tracked bug, never a name or prose-only; enforced by clang-tidy `google-readability-todo` | bug tracker holds history | | https://google.github.io/styleguide/pyguide.html#312-todo-comments ; https://clang.llvm.org/extra/clang-tidy/checks/google/readability-todo.html |
| Oracle Javadoc | Doc comment = contract/spec, not implementation history; `@deprecated` with pointer | | | https://www.oracle.com/technical-resources/articles/java/javadoc-tool.html |
| Microsoft | Writing Style Guide governs docs prose (plain language, task-oriented), not code comments | | docs.microsoft style | https://learn.microsoft.com/en-us/style-guide/welcome/ |

Pattern across all of them: the code comment carries the local, durable
*why* in one or two sentences and a *pointer* (issue URL / ticket id).
The incident story lives behind the pointer. Nobody keeps paragraphs of
history next to the code.

### 2.3 CHANGELOG mechanisms

| Mechanism | Who | Shape | Fit for a Rust workspace |
|---|---|---|---|
| Hand-written Keep a Changelog | tokio (per-crate `CHANGELOG.md`), cargo (`src/doc/src/CHANGELOG.md`) | `## [1.2.0] - 2026-01-01` / `### Added` ... | Simple; merge conflicts at scale; curated prose quality |
| PR-title driven | rust-analyzer weekly changelog from `feat:`/`fix:`/`internal:` prefixes or a changelog comment | Script collects merged PRs by label | Needs a bot; no per-crate split |
| Fragments compiled at release | towncrier (Python), Bevy `release-content/{release-notes,migration-guides}/*.md`, frob v1 `changelog.d/T-####.md` | One file per change, named by issue/ticket; compiled by a release step; no conflicts | Best fit when every change already has a ticket id. https://towncrier.readthedocs.io/en/stable/markdown.html |
| Conventional commits -> git-cliff | many crates; orhun's write-up | `cliff.toml` template over commit history | Only as good as commit discipline; workspace path filtering is finicky. https://blog.orhun.dev/automated-rust-releases/ |
| release-plz | release PR with version bumps + changelog (uses git-cliff + cargo-semver-checks) | CI opens the release PR | Good for library crates with semver; pre-filters commits by package path, so cross-crate work can produce empty changelogs. https://github.com/release-plz/release-plz |

### 2.4 Anti-rot CI checks observed

| Check | Used by | Command |
|---|---|---|
| Generator in check mode | ruff (`Mode::Check`), uv (same model) | `cargo dev generate-all --mode check` |
| Generate-then-`git status --porcelain` | ruff `scripts` job for AST/formatter codegen | `test -z "$(git status --porcelain)"` |
| Sourcegen test | rust-analyzer | `cargo test` fails when `*_generated.md` differ |
| Strict site build | ruff, uv | `mkdocs build --strict` (broken nav/link = failure) |
| mdbook build + link check | cargo, rustc-dev-guide, rust-analyzer | `mdbook build`; `mdbook-linkcheck` backend or `lychee` over output |
| Doc tests | all | `cargo test --doc` |
| Doc build with lints | all | `RUSTDOCFLAGS="-D warnings" cargo doc --no-deps --all-features` |
| Spelling | ruff (pre-commit), uv, many | `typos` (https://github.com/crate-ci/typos) |
| Markdown format/lint | ruff | `mdformat`, `markdownlint` |
| Fragment presence | towncrier adopters, Bevy | PR touching shipped code must add a fragment |

## 3. Code-comment hygiene

### 3.1 One home per kind of knowledge

| Knowledge | Home | Why there | Lifetime |
|---|---|---|---|
| Contract of a public item (what, inputs, errors, panics, example) | rustdoc on the item | Rendered, tested, next to the signature | As long as the item |
| Local non-obvious *why* (why this ordering, why this constant, why not the obvious approach) | `//` comment, 1-3 sentences, optionally `(T-####)` pointer | Only place the next editor will see it | As long as the code |
| Invariant the code relies on | `// Invariant:` comment or `frob:invariant` directive + test | Must be visible at the point of reliance | As long as the code |
| Deferred work | `// TODO(T-####): short imperative` ; never bare TODO | Tracked, searchable, closable | Until the ticket closes |
| Incident narrative, what broke, who found it, what was tried | Ticket, PR description, commit body | History is append-only and timestamped; code is not | Forever, outside the tree |
| Why an architectural choice was made among alternatives | ADR in `docs/decisions/` | Durable, dated, supersedable | Forever, status changes |
| How the system is shaped (codemap, layers, invariants) | `docs/architecture.md` | One place to read before contributing | Revised a few times a year |
| How to use the product | `docs/<product>/` (Diataxis) | User-facing | Per release |

Rules of thumb drawn from the sources:

- A comment that explains *what* the code does is a smell; rename or
  restructure instead (Google C++ style, "Comments" section:
  https://google.github.io/styleguide/cppguide.html#Comments).
- A comment that explains *history* ("this used to be X until T-2311")
  belongs in `git blame` and the ticket; put the ticket id in the commit
  trailer and the comment keeps only the surviving constraint.
- Comments are proper sentences (rust-analyzer style.md).
- Comments wrap narrower than code so they read as prose (matklad,
  https://matklad.github.io/2026/02/21/wrapping-code-comments.html).
- A durable rule plus its rationale belongs in `style.md`/an ADR, with
  the code comment linking to it, not restating it.

### 3.2 ADR practice

| Format | Fields | Source |
|---|---|---|
| Nygard (2011) | Title, Status, Context, Decision, Consequences | https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions |
| MADR 4.0 (2024) | Title, Status, Date, Deciders, Context and Problem Statement, Decision Drivers, Considered Options, Decision Outcome (+ Consequences, Confirmation), Pros and Cons of the Options, More Information | https://adr.github.io/madr/ |
| Tooling | `adr-tools` (shell, Nygard numbering `NNNN-title.md`), `adr-log` for index, templates list | https://adr.github.io/adr-templates/ ; https://adr.github.io/adr-tooling/ |

Operational norms: ADRs are immutable once accepted; a change is a new
ADR with `Supersedes: ADR-000N`; status vocabulary `proposed | accepted |
deprecated | superseded`; keep an index. One ADR per decision, not per
feature.

### 3.3 Diataxis

| Quadrant | Serves | Form | frob example |
|---|---|---|---|
| Tutorial | learning, by doing | ordered lesson with a guaranteed outcome | "Your first frob-enforced repo in 10 minutes" |
| How-to | a goal, for a competent user | task recipe, no teaching | "Waive a rule for one file" |
| Reference | information, while working | dry, complete, generated where possible | rules, CLI, config schema |
| Explanation | understanding | discursive, why | "Why obligations are a graph" |

Source: https://diataxis.fr/ . Adopters: Django (Procida is a Django
core dev), Canonical/Ubuntu, Cloudflare developer docs (Diataxis as the
IA "north star"), Gatsby's docs reorganisation, LangChain
(https://romain-clement.net/articles/diataxis/ ; https://diataxis.fr/).
Practical consequence: never mix "how to" steps into reference pages, and
never let a tutorial branch.

## 4. Doc-gen tooling for Rust CLIs

| Need | Tool | Notes | Source |
|---|---|---|---|
| Man pages | `clap_mangen` | ROFF from `clap::Command`; run in `build.rs` or an xtask; nested subcommands supported | https://docs.rs/clap_mangen ; https://rust-cli.github.io/book/in-depth/docs.html |
| Markdown CLI reference | `clap-markdown` | `help_markdown::<Cli>()`; one page, all subcommands; limited layout control | https://crates.io/crates/clap-markdown |
| Custom CLI reference | ruff `generate_cli_help.rs`, uv `generate-cli-reference` | Walk `Command` tree yourself; emit one section per subcommand with anchors; lets you inject examples per subcommand | ruff_dev listing |
| Shell completions | `clap_complete` | Same xtask | https://docs.rs/clap_complete |
| Config schema | `schemars` `#[derive(JsonSchema)]` -> `*.schema.json` | Publish to SchemaStore for editor support (ruff, uv do) | https://docs.rs/schemars ; https://www.schemastore.org/ |
| Config reference page | `OptionsMetadata`-style derive: field doc comment + default + example + deprecation -> markdown table per section | ruff's `ruff_options_metadata` crate; rust-analyzer's `config!` macro does the same | https://docs.rs/ruff_options_metadata |
| Rule reference | derive carrying code, name, summary, fix availability, doc comment body | ruff `ViolationMetadata` + `generate_docs` -> `docs/rules/<code>.md` | ruff_dev listing |
| Site | mdbook (Rust-native, single binary, `mdbook test` runs Rust blocks) or mkdocs-material (nicer, Python dep) | ruff/uv chose mkdocs for search and theme; cargo/ra chose mdbook to stay in-toolchain | https://rust-lang.github.io/mdBook/ |
| mdbook plugins | `mdbook-admonish` (callouts), `mdbook-mermaid` (diagrams), `mdbook-linkcheck` (0.4 line) or `lychee` over built HTML (0.5), `mdbook-toc` | `action-mdbook` installs them in CI | https://github.com/jontze/action-mdbook ; https://github.com/badboy/mdbook-mermaid ; https://lib.rs/crates/mdbook-linkcheck |
| Link checking | `lychee` | Checks markdown and HTML, offline mode for local links, cache for remote | https://github.com/lycheeverse/lychee |
| Spelling | `typos` | Fast, low false positives, `_typos.toml` allowlist | https://github.com/crate-ci/typos |
| Rustdoc links | `cargo doc` with `rustdoc::broken_intra_doc_links` = deny; `cargo-deadlinks` is largely superseded by the built-in lint plus lychee | https://doc.rust-lang.org/rustdoc/lints.html |
| README sync | `#[doc = include_str!]` or `cargo-rdme --check` | pick one direction | section 1.3 |
| docs.rs vs site | docs.rs: API of gob-* crates; site: product docs for frob/grimble/crunk | Do not duplicate; site links to docs.rs for API | |

## 5. Recommendation for frob v2

### 5.1 Directory layout

```
docs/
  README.md                 index; links the three products and shared pages
  architecture.md           matklad-style: overview, codemap (gob-* crates), invariants
  style.md                  code and comment rules, each with Rationale (ra pattern)
  decisions/
    README.md               ADR index (generated by xtask)
    0001-record-decisions.md
    0002-derive-first-docs.md
    ...
  frob/
    tutorial.md
    howto/*.md
    reference/              GENERATED: cli.md, config.md, rules/*.md, schema.json
    explanation/*.md
  grimble/    (same shape)
  crunk/      (same shape)
  design/                   existing design notes; explanation quadrant, cross-product
CHANGELOG.md                compiled; never hand-edited between releases
changelog.d/                fragments: T-####.<added|changed|fixed|removed|deprecated|security>.md
```

Each gob-* crate: `README.md` pulled in by `#![doc = include_str!("../README.md")]`.
Product crates: thin `main.rs`, everything documented in the lib.

### 5.2 Generated vs written

| Page | Source of truth | Generator |
|---|---|---|
| `reference/cli.md` | clap derive doc comments | `cargo xtask gen cli` (custom walker, ruff style; also emits man pages via clap_mangen and completions) |
| `reference/config.md` + `schema.json` | config struct derive (`OptionsMetadata`-like) + schemars | `cargo xtask gen config` |
| `reference/rules/<ID>.md` + rules index | rule derive + doc comment | `cargo xtask gen rules` |
| `decisions/README.md` | ADR front matter | `cargo xtask gen adr-index` |
| `CHANGELOG.md` | `changelog.d/` fragments | `cargo xtask changelog --version X` at release |
| tutorial, howto, explanation, architecture, style, ADR bodies | humans | none; linted only |

Single `Mode { Write, Check }` across all generators; `cargo xtask gen
--check` is the CI gate. A doc-comment rule body is the only place a
rule's prose exists; the markdown page is a build artifact that is
committed (so GitHub browsing and diffs work) and checked.

### 5.3 The comment rule (what the lint enforces)

Policy, in `style.md`, enforced by a frob policy rule over tree-sitter
comment nodes:

| Rule | Check |
|---|---|
| No bare `TODO`/`FIXME`/`XXX`/`HACK` | Must be `TODO(T-####):` (existing TODO001) |
| No ticket narrative | A comment block (consecutive `//` lines, or one `/* */`) in a `.rs` file may mention at most one `T-####` and must be <= 6 lines; longer blocks must be rustdoc (`///`, `//!`) or a `// Invariant:` block |
| No history words in comments | Regex on `//` comments for `(used to|previously|was changed|regression|incident|hotfix|see discussion|as of 20\d\d)`; allow in `///` only when under a `# History`-free section (i.e. forbid everywhere, waive with `frob:waive`) |
| Ticket ids in rustdoc | Forbidden in `///`/`//!` (public docs must not leak internal tracker ids); allowed in `//` only as `(T-####)` suffix or `TODO(T-####)` |
| Rationale pointer, not rationale | A `//` comment containing "because" or "rationale" longer than 3 lines must reference `docs/decisions/NNNN` or `docs/style.md#anchor` |
| Public items documented | `#![warn(missing_docs)]` promoted to `deny` in CI via `RUSTFLAGS` |
| Doc sections present | `clippy::missing_errors_doc`, `clippy::missing_panics_doc`, `clippy::missing_safety_doc` = warn (deny in CI) |

Where the narrative goes instead: the ticket (`frob ticket`) body, the
PR description, and the commit body (`Refs: T-####` trailer). The comment
keeps only the surviving constraint plus the pointer.

### 5.4 ADR format

MADR 4.0, trimmed. Required fields: title, `status`, `date`, `ticket`,
Context, Decision, Consequences, Alternatives considered (one line each).
Optional: Supersedes/Superseded-by. File name `NNNN-kebab-title.md`,
numbering never reused. Index generated. An ADR is required when a
change touches an item listed under "Architecture Invariants" in
`architecture.md`; the frob doc-drift gate (`frob ack`) binds those
sections to the gob-* crate roots.

### 5.5 CHANGELOG mechanism

Keep the v1 fragment model (it maps 1:1 onto tickets) but make it
towncrier-shaped: `changelog.d/T-####.<type>.md`, one or two user-facing
sentences, type set = Keep a Changelog categories, per-product prefix in
the first line (`frob:`, `grimble:`, `crunk:`, `gob:`). `cargo xtask
changelog` compiles into `CHANGELOG.md` sections per product under one
version heading and deletes fragments. Gate: a PR that changes a
product crate or a gob-* public item must add a fragment (frob rule, not
a GitHub bot). Do not adopt git-cliff/release-plz: commit history is not
the user-facing voice, and release-plz's path filtering misreports
cross-crate work in this workspace.

### 5.6 CI checks (all behind `frob check`)

| Gate | Command |
|---|---|
| Generated docs current | `cargo xtask gen --check` |
| Rustdoc clean | `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps --all-features --document-private-items` |
| Doc tests | `cargo test --doc --workspace` |
| Missing docs / sections | `cargo clippy --workspace -- -D missing_docs -D clippy::missing_errors_doc -D clippy::missing_panics_doc` |
| Site builds | `mdbook build docs` (strict via `[output.html] ... ` plus `lychee --offline docs/book`) |
| Links (remote, weekly) | `lychee docs/**/*.md --cache` on a schedule, not per PR |
| Spelling | `typos` |
| Markdown style | `markdownlint` with sentence-per-line disabled, line length off for tables |
| Comment hygiene | frob policy rules from 5.3 |
| Fragment present | frob rule: touched product/public item implies `changelog.d/T-####.*.md` exists |
| ADR present | frob rule: touched invariant anchor implies new or updated `docs/decisions/*.md` |
| Doc drift | existing `frob ack` binding of `docs/` pages to crate roots |

### 5.7 Opinions, stated plainly

- Prose that cannot be generated is explanation or tutorial; everything
  else (CLI, config, rules, schema, ADR index, changelog) is generated.
- A code comment is at most a paragraph and at most one ticket pointer.
  If it needs more, it is an ADR or a ticket.
- Ticket ids never appear in rustdoc. Users do not have the tracker.
- mdbook over mkdocs: zero Python in the Rust toolchain, `mdbook test`
  executes Rust blocks in the docs, single binary in CI. Revisit only if
  search quality becomes a user complaint.
- One `architecture.md` for the workspace, not one per product; products
  are thin over gob-*, and the invariants are about gob-* boundaries.
