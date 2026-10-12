# Documentation survey: how 1254 popular repositories document themselves, and what that means for frob

Date: 2026-10-02. Status: research input for the ticket-branch navigation spec (mirror.md
section 1, open question 3) and for documentation.md. ASCII only. Raw data and scripts live under
`<scratchpad>/docs/`
(never in the repo); they are listed in section 9.

## 0. Honest summary (read this first)

- Universe (denominator): 1254 repositories. 284 are "curated developer tools" (tools), 970 are the
  top-by-stars repositories of 21 languages (libs/apps). 119 of the 1254 look like list/tutorial/book
  repositories (awesome lists, interview guides); results are given with and without them where it matters.
- Done: 1254 of 1254 root-plus-recursive tree listings fetched and analysed (0 left pending, 0 failed
  after retry); 1214 README bodies analysed; 1209 label lists; 1076 repositories' workflow bodies
  (first 15 workflows each); 631 repositories' docs files sampled (5525 files, first 800 bytes) for
  "generated" markers.
- Partial or blocked, stated up front: (a) 18 repositories have truncated recursive trees (GitHub tree
  limit; e.g. kubernetes/kubernetes); for those I have the root plus `docs/`, `.github/` and a few other
  subtrees only, so per-directory-README numbers exclude them and every other item is a lower bound for them.
  (b) Presence is path-based and heuristic; I did not open every doc. Numbers are prevalence of
  "a file or directory with this name exists", not quality. (c) Labels cover only the first 100 labels per
  repository (undercount for the few with more). (d) `gh api rate_limit` reported 5000/5000 before and
  after roughly 3000 calls, so the 5000/hour budget is unverifiable here; planned usage was well under it.
  (e) Search, wiki usage and docs-site traffic are not measurable from trees; wiki is only the "wiki enabled"
  flag. (f) Three claims in section 5 come from memory and were not fetched; they are marked UNVERIFIED.
- Phase-2 verdict: coverage of the declared sample is complete; coverage of "the top ~1000 repositories"
  is by construction (curated plus per-language top by stars, 2026 star counts, which pulls in a
  noticeable number of recent AI-agent repositories), not a census of GitHub.
- Headline numbers (all repos / tools / libs): README 99.1%; CONTRIBUTING 66.6% / 87.0% / 60.6%;
  CODE_OF_CONDUCT 37.0% / 51.8% / 32.7%; SECURITY 35.3% / 52.5% / 30.3%; a `docs/` directory
  54.8% / 67.6% / 51.0%; a doc-site generator 19.6% / 36.6% / 14.6%; ARCHITECTURE.md at root or docs/ only
  4.1% / 5.6% / 3.7% (any depth 14.1%); a changelog file 42.7% / 55.6% / 38.9%; ADR directory 2.5%;
  `linguist-generated` in .gitattributes 10.3% / 21.8% / 6.9%; a good-first-issue-style label 58.5%;
  per-directory READMEs exist for only 29.5% of major directories (workspace members such as crates/*:
  52.2%); Diataxis-named folders (tutorials, how-to, reference, explanation all four) 0.3% of repos with
  docs/ (1.2% on loose synonyms).
- Recommended generated navigation set: section 7. In one line: ticket branch gets a generated root
  README (what/how/where, counts, in-progress, ready, recent), a generated README in every epic
  directory, generated index pages by status, milestone, component, blocked, recent and good-first, a
  generated glossary of fields and states from the schema derive, and an installed (not hand-edited) guide;
  code repo gets hand-written ARCHITECTURE.md plus a generated docs map, generated reference pages, and
  per-crate READMEs; every generated file carries one machine-greppable marker with its regeneration
  command; one `--check` gate (GEN001) fails CI on drift.

## 1. Sample

### 1.1 Construction

The earlier CI/CD survey sample (1069 repositories, `scratchpad/cicd/`) had been wiped by a restart, so I
rebuilt a comparable one. It is larger (1254) because I added PHP, Dart, Shell and Lua buckets and more
curated tools.

- Curated tools: a list of 287 `owner/name` strings (`curated.txt`, written by me) covering the names the
  brief listed (ruff, uv, rust, cargo, tokio, deno, bun, kubernetes, react, django, pytest, numpy,
  terraform, neovim, zed, tree-sitter) plus documentation-relevant projects (mdBook, rustc-dev-guide, rfcs,
  rust-analyzer, mkdocs-material, sphinx, docusaurus, vitepress, typst, jj, git-cliff, towncrier, changesets,
  release-please, lychee, vale, typos, markdownlint, crate-ci/typos, github/docs and similar). Each was
  resolved through `repos/{o}/{r}`: 275 resolved as written, 10 were renamed or redirected (the redirect target
  is used; 1 collapsed into an already-listed repository), 2 not found (`mage/magefile`, `three.js/three.js`,
  both my typos). Result: 284 distinct curated repositories. The label "tool" means "curated developer tool or
  infrastructure project"; it includes frameworks and libraries I curated (react, django, serde, pydantic).
- Language buckets: `search/repositories?q=language:"L" stars:>500&sort=stars`, first N not already in the
  sample (so these are "the next N beyond the curated ones"). N = 50 for Rust, Python, Go, Java, Kotlin, C, C++,
  C#, Ruby, Swift, Zig, Haskell, OCaml, Elixir, Scala, TypeScript, JavaScript, PHP; 30 for Dart; 20 for
  Shell and Lua. 970 repositories, labelled "libs/apps".
- Total: 284 + 970 = 1254. 47 archived. 18 truncated trees. Primary language counts for n >= 50: Rust 117,
  Go 100, Python 95, TypeScript 80, JavaScript 70, C++ 61, C 60, Ruby 59, Java 56, C# 53, Haskell 53,
  Scala 52, Swift 52, Elixir 52, Zig 52, Kotlin 51, OCaml 51, PHP 50.
- Bias to keep in mind: star ranking in October 2026 includes many 2025-2026 AI and agent projects with
  README-heavy, docs-light layouts; and the language buckets exclude the curated giants, so "libs/apps" skews
  slightly toward the mid-popular.

### 1.2 Per repository

One call for `git/trees/{branch}?recursive=1` (every path in the repository: root files, docs/, every
subdirectory README, `.github/`, `.gitattributes`), one for `labels?per_page=100`; for the 18 truncated
trees, one root-tree call plus subtree calls for docs/, doc/, .github/, rfcs/ and similar. Bodies came from
raw.githubusercontent.com: the README, `.gitattributes`, the first 8 KB of the changelog, up to 15 workflow
files, and for the docs-marker pass the first 800 bytes of up to 12 randomly chosen (seeded) Markdown, RST,
MDX, AsciiDoc or text files under docs/, doc/, documentation/, book/src/ and similar.

### 1.3 Definitions used in the tables

- "community file" = present at root, `.github/`, `docs/` or `.gitlab/` (case-insensitive).
- ARCHITECTURE.md: a file named `architecture.*` (the matklad convention); reported at root, in docs/ and at
  any depth, because most "any depth" hits are module-level or per-package files.
- docs/ directory: root directory named docs, doc or documentation.
- Doc-site generator: mdBook (`book.toml`), Docusaurus (`docusaurus.config.*`), MkDocs (`mkdocs*.yml`),
  Sphinx (`conf.py` plus an index), VitePress (`.vitepress/config.*`), Hugo (`hugo.toml` or `config.toml`
  plus `layouts/`), "Starlight" (any `astro.config.*`, so an upper bound for Starlight), Doxygen, Typedoc,
  Antora, Jekyll (`_config.yml`, not counted as a site in "any_site"), Read the Docs config.
- "rustdoc-only" = Cargo.toml at root and no site generator detected; docs.rs then hosts the API docs.
- Diataxis folders: subdirectories of docs/ named (exact) tutorial(s), how-to/howto, reference,
  explanation; (loose) synonyms such as guides, concepts, topics, ref, api, internals, design.
- Docs CI: from workflow bodies and config files; denominators are repositories with at least one workflow
  (1076 / 273 tools / 803 libs).
- Labels: "good first" strict = good first / first-timers / beginner / newcomer / starter; loose also counts
  easy and help wanted.

## 2. Prevalence tables

Columns: all repos (n=1254) / tools (n=284) / libs and apps (n=970). "excl lists" is noted only where it
moves a number by more than two points. Percent of repositories unless a different denominator is stated.

### 2.1 Community and governance files

| Item | all | tools | libs/apps |
|---|---|---|---|
| README | 99.1% | 99.3% | 99.1% |
| LICENSE or COPYING | 94.2% | 97.5% | 93.2% |
| CONTRIBUTING | 66.6% | 87.0% | 60.6% |
| CODE_OF_CONDUCT | 37.0% | 51.8% | 32.7% |
| SECURITY | 35.3% | 52.5% | 30.3% |
| all three (CONTRIBUTING + COC + SECURITY) | 19.1% (239) | 33.1% (94) | 14.9% (145) |
| CODEOWNERS | 21.4% | 32.7% | 18.0% |
| MAINTAINERS or OWNERS or COMMITTERS | 5.3% | 11.6% | 3.4% |
| GOVERNANCE | 2.7% | 6.7% | 1.5% |
| SUPPORT | 4.9% | 7.7% | 4.1% |
| AUTHORS or CONTRIBUTORS | 8.6% | 12.7% | 7.4% |
| CITATION.cff | 3.2% | 9.2% | 1.4% |
| .github/FUNDING.yml | 30.9% | 32.7% | 30.4% |
| development/hacking/building doc (name match) | 64.0% | 76.4% | 60.3% |
| issue template (any form) | 68.7% | 82.0% | 64.7% |
| issue forms (YAML) | 49.1% | 72.9% | 42.2% |
| PR template | 45.5% | 64.4% | 39.9% |
| discussion templates | 3.0% | 4.9% | 2.4% |
| GitHub Discussions enabled | 53.9% | 59.9% | 52.2% |
| homepage URL set on the repo | 75.8% | 88.7% | 72.0% |
| wiki enabled (flag only, not usage) | 52.4% | 33.1% | 58.0% |

Reading: tools document governance far more than libraries; the wiki flag is the default (GitHub turns it
on), and is enabled *less* often by tools (33%) than by libs (58%), which suggests projects with real docs
sites turn it off. Of the 106 repositories with an architecture file or folder at root or docs/ (broader detection than the 4.1% figure in section 4.1), 82% also have CONTRIBUTING.

### 2.2 README shape (1214 repositories whose README was fetched; 282 tools, 932 libs)

| Item | all | tools | libs/apps |
|---|---|---|---|
| length median / p10 / p90 (bytes) | 7756 / 2332 / 29328 | 6202 / 1964 / 21165 | 8271 / 2433 / 31939 |
| length median (lines) | 159 | 125 | 170 |
| fewer than 50 lines | 10.0% | - | - |
| 300 lines or more | 25.0% | - | - |
| heading count median / p90 | 11 / 40 | 9 / 27 | 12 / 45 |
| has install/setup/build heading | 58.9% | 58.5% | 59.0% |
| has quickstart/getting-started/example heading | 39.8% | 41.8% | 39.2% |
| has usage/API/CLI heading | 40.8% | 35.5% | 42.4% |
| has contributing/development/community heading | 61.4% | 72.7% | 57.9% |
| has license heading | 47.8% | 48.6% | 47.5% |
| has documentation/docs/guide/reference heading | 43.7% | 47.5% | 42.6% |
| has features/why/overview/about heading | 44.2% | 35.8% | 46.8% |
| has support/help/community/contact/FAQ heading | 48.4% | 48.9% | 48.3% |
| has security heading | 10.5% | 9.6% | 10.7% |
| table of contents (all READMEs) | 14.3% | 13.5% | 14.6% |
| table of contents (READMEs of 300+ lines) | 34.5% | - | - |
| table of contents (READMEs under 300 lines) | 7.6% | - | - |
| 1 or more badges | 73.0% | 78.7% | 71.2% |
| 4 or more badges | 49.3% | 54.6% | 47.7% |
| badge count median / p90 | 3 / 13 | 4 / 14 | 3 / 12 |
| 1 or more images (logo or screenshot) | 86.8% | 80.5% | 88.7% |
| image or logo in the first 600 bytes | 81.7% | 79.4% | 82.4% |
| 1 or more code fences | 61.4% | 58.2% | 62.3% |
| links to an external docs site | 68.4% | 78.0% | 65.5% |
| has translated-README links | 24.8% | 10.3% | 29.2% |

Reading: the typical README is a banner, badges, a pitch, install, and links out; only 40% have a quickstart
or usage heading, so most READMEs do not themselves answer "how do I use this" - they delegate to a docs site
(68% link to one). Tables of contents appear when READMEs get long (34.5% at 300+ lines), but GitHub renders
an Outline menu for every Markdown file for free (section 5.8), so a generated in-file TOC is not needed.

### 2.3 docs/ directory and doc sites

| Item | all | tools | libs/apps |
|---|---|---|---|
| docs/ (docs, doc, documentation) at root | 54.8% | 67.6% | 51.0% |
| any of docs, doc, documentation, website, book, wiki, guide, manual, handbook, site | 57.3% | 72.5% | 52.9% |
| neither a docs directory nor a site (README is the whole story) | 40.0% | - | - |
| docs/ size, median Markdown/RST files | 23 | 57 | 16 |
| docs/ size, p90 | 299 | 636 | 210 |
| any doc-site generator | 19.6% | 36.6% | 14.6% |
| rustdoc-only (Rust crate, no site) | 6.2% | 16.2% | 3.3% |
| Sphinx | 6.0% | 13.4% | 3.8% |
| MkDocs (incl. Material) | 4.0% | 7.7% | 2.9% |
| mdBook | 2.4% | 6.7% | 1.1% |
| Docusaurus | 2.1% | 2.5% | 2.0% |
| Astro/Starlight (upper bound) | 1.7% | 1.4% | 1.8% |
| VitePress | 1.6% | 3.2% | 1.1% |
| Doxygen | 1.6% | 2.1% | 1.4% |
| Hugo (with layouts/) | 1.5% | 2.5% | 1.2% |
| Jekyll `_config.yml` | 3.3% | 2.5% | 3.5% |
| Read the Docs config | 3.4% | 7.7% | 2.2% |
| dedicated docs/pages workflow | 27.1% | 37.0% | 24.2% |
| versioned docs (versioned_docs, versions.json, mike, docs/vN) | 2.6% | 5.6% | 1.8% |

Count among all sites detected (a repository can have two): Sphinx 75, MkDocs 50, mdBook 30, Docusaurus 26,
Starlight/Astro 21, Doxygen 20, VitePress 20, Hugo 19, Antora 4, Typedoc 4. Sphinx still leads because of the
Python buckets (49.5% of Python repositories have a site); Rust tools lean mdBook and rustdoc.

Among the 362 repositories whose docs/ holds 20 or more documents: 57.5% have an index file in docs/
(README.md, index.*, SUMMARY.md, contents, toc, sidebar), 42.8% have a site generator, 34.8% a FAQ, 20.4% a
glossary, 26.2% contain a path that looks like generated reference (cli-reference, config reference,
api reference, "generated"). Overall (all 687 repositories with docs/), an index file exists in 42.6%.

Language slice (docs/ dir, CONTRIBUTING, site): Rust 63%, 84%, 31%; Go 66%, 70%, 17%; Python 67%, 75%,
50%; TypeScript 66%, 88%, 35%; C++ 72%, 80%, 30%; C 60%, 50%, 22%; Elixir 17%, 48%, 12% (probably because Elixir projects lean on
hexdocs generated from source; not checked); Zig 42%, 35%, 2%; C# 42%, 55%, 2%.

### 2.4 Diataxis and other doc structure (denominator: 687 repositories with docs/)

| Item | exact names | loose synonyms |
|---|---|---|
| tutorials folder | 4.4% | 7.3% |
| how-to folder | 1.7% | 6.8% |
| reference folder | 5.7% | 13.4% |
| explanation folder | 0.6% | 8.6% |
| all four | 0.3% (2 repos) | 1.2% (8 repos) |
| three or more | - | 3.3% (23 repos) |

Tools: all four loose 2.1% (4 of 192). Libs: 0.8% (4 of 495). The four-way split is almost never adopted as
folder names. The projects that do split are the ones with large doc sets: django (intro, howto, topics, ref),
uv (getting-started, guides, concepts, reference), cpython (tutorial, howto, reference), kubernetes website
(tutorials, tasks, concepts, reference). The convention is therefore "a few of the four, under local names",
and Diataxis itself says not to create empty quadrants (section 5.2).

Other structure items (all / tools / libs):

| Item | all | tools | libs/apps |
|---|---|---|---|
| tutorial/quickstart/getting-started/install page or folder | 33.5% | 53.2% | 27.7% |
| how-to/recipes/cookbook page or folder | 11.5% | 17.6% | 9.7% |
| examples directory anywhere shallow | 24.0% | 30.6% | 22.1% |
| examples/ at root | 16.9% | 20.8% | 15.8% |
| FAQ file | 16.6% | 27.5% | 13.4% |
| troubleshooting file | 16.9% | 29.2% | 13.3% |
| glossary file | 7.7% | 16.9% | 4.9% |
| docs index file (docs/README.md, index.*, SUMMARY.md, toc, sidebar) | 23.4% | 37.0% | 19.4% |
| SUMMARY.md anywhere (mdBook map) | 3.8% | 7.0% | 2.9% |
| sidebar/toc config (sidebars.js, _toc.yml, nav files) or mkdocs/mdbook | 11.1% | 19.7% | 8.6% |

### 2.5 Changelogs, ADRs and RFCs

| Item | all | tools | libs/apps |
|---|---|---|---|
| CHANGELOG/CHANGES/HISTORY/NEWS/RELEASES file at root or docs/ | 42.7% | 55.6% | 38.9% |
| changelog file or any changelog tool | 46.4% | - | - |
| Keep a Changelog style (of 535 changelog repos, body checked) | 12.1% (65/535) | - | - |
| towncrier (fragments dir or config) | 1.8% | 4.2% | 1.0% |
| changesets (`.changeset/`) | 1.3% | 3.2% | 0.7% |
| release-please (config or workflow) | 2.1% | 4.2% | 1.4% |
| semantic-release | 1.0% | 1.1% | 0.9% |
| git-cliff | 1.6% | 3.5% | 1.0% |
| release-drafter | 1.8% | 2.1% | 1.8% |
| ADR directory (adr, adrs, decisions, architecture-decisions) | 2.5% | 1.4% | 2.8% |
| RFC/proposal/design-doc/KEP/PEP directory | 2.2% | 3.5% | 1.9% |

Reading: more than half of the sample has no changelog file at all (most use GitHub Releases, not
measurable here), and the fragment-based tools (towncrier, changesets) together are about 3%; frob's
design (changelog.d fragments compiled at release) matches the towncrier model used by pip, pipx, setuptools,
conda, sphinx, ghc, airflow and home-manager in this sample. ADRs and RFC directories are rare (2.5% and
2.2%); the RFC users are the large governance-heavy projects (cockroach, argo-cd, flux2, opa, opentofu,
opentelemetry-collector, minikube, ingress-nginx, openssl, swift). ADR users: airflow, logseq,
react-router, swc.

### 2.6 Generated documents and how they are marked

| Item | all | tools | libs/apps |
|---|---|---|---|
| `.gitattributes` present | 48.8% | 69.7% | 42.7% |
| `linguist-generated` in .gitattributes | 10.3% | 21.8% | 6.9% |
| `linguist-vendored` | 7.3% | 10.6% | 6.4% |
| `linguist-documentation` | 2.3% | 4.6% | 1.6% |
| generated-code paths (`generated/`, `.pb.go`, `*.generated.*`, `_generated.*`) | 20.5% | 28.5% | 18.1% |
| generated-docs-looking path under docs/ (cli/config/api reference, "generated") | 7.9% | 14.1% | 6.1% |
| checked-in schema file (`*.schema.json`, openapi, swagger) | 5.5% | 4.2% | 5.9% |
| pre-commit config | 7.1% | 14.4% | 4.9% |

Docs-file marker pass (631 repositories with sampled docs, 5525 files, 12 per repository maximum, first 800
bytes): 2.7% of sampled files (151) carry a "generated" phrase near the top; 10.9% of repositories (69 of
631) had at least one such file; tools 15.7% (29 of 185), libs 9.0% (40 of 446). This is a lower bound
(12 files per repository) and includes some false positives such as release notes saying "generated by".
Phrases found, by count: "autogenerated" 31, "generated by" 26, "automatically generated" 20, "this file is
auto-generated" 20, "generated with" 12, "generated from" 9, "this page is auto-generated" 6, "generated
file" 5, "@generated" 5, "do not edit" 4, "machine-generated" 2. Style of the marker line: 102 front-matter
or body text, 40 HTML comment, 9 RST or other comment.

Real marker styles seen in fetched files (verbatim, trimmed):

| Project | File | Marker |
|---|---|---|
| astral-sh/ty | docs/reference/cli.md | `<!-- WARNING: This file is auto-generated (cargo dev generate-all). Edit the doc comments in 'crates/ty/src/args.rs' if you want to change anything here. -->` |
| rust-lang/rust-clippy | book/src/lint_configuration.md | HTML comment: "This file is generated by `cargo bless --test config-metadata`. Please use that command to update the file and do not edit it by hand." |
| jj-vcs/jj | docs/cli-reference.md | HTML comment: "The contents of the CLI reference is auto-generated by a Rust test. If `cargo insta` is installed, you can regenerate the CLI reference with: cargo insta test --accept --workspace -- test_generate" |
| rclone/rclone | docs/content/commands/rclone_size.md | in front matter: `# autogenerated - DO NOT EDIT, instead edit the source code in cmd/size/ and as part of making a release run "make commanddocs"` |
| jdx/mise | docs/cli/tasks/validate.md | `<!-- @generated by usage-cli from usage spec -->` |
| mermaid-js/mermaid | docs/config/setup/mermaid/interfaces/*.md | visible blockquote: "THIS IS AN AUTOGENERATED FILE. DO NOT EDIT. Please edit the corresponding file in [path to source]" |
| elastic/elasticsearch | docs/reference/.../_snippets/generated/... | `% This is generated by ESQL's ...Tests. Do not edit it. See docs/reference/query-languages/esql/README.md for how to regenerate it.` |
| npm/cli | docs/lib/content/commands/npm-ping.md | `<!-- AUTOGENERATED USAGE DESCRIPTIONS -->` (a splice region inside a hand-written page) |
| rust-lang/rust-analyzer | docs/book/src/configuration_generated.md | no in-file marker; the file name suffix `_generated` is the marker; the architecture doc says generated code is committed and refreshed by `cargo test` |
| golang/go | all generated Go source | the standardized line `^// Code generated .* DO NOT EDIT\.$` before the first non-comment text (from cmd/go generate docs); GitHub linguist matches `^// Code generated .*` in the first 40 lines |

Two lessons: the good markers (ty, clippy, jj, rclone, elasticsearch, mermaid) all name the regeneration
command or the source of truth in the marker itself; and the visible-versus-hidden choice matters because
GitHub's rendered Markdown hides HTML comments, so only mermaid's blockquote style is visible to a newcomer
who never opens the raw file.

### 2.7 Docs CI (denominator: 1076 repositories with workflows; 273 tools, 803 libs)

| Item | all | tools | libs/apps |
|---|---|---|---|
| link checking, any tool | 5.6% | 12.5% | 3.2% |
| lychee (config or workflow) | 2.3% | 5.9% | 1.1% |
| markdown-link-check | 1.0% | 1.1% | 1.0% |
| markdownlint | 6.6% | 12.8% | 4.5% |
| vale | 1.1% | 3.3% | 0.4% |
| typos (crate-ci) | 6.1% | 13.2% | 3.7% |
| codespell | 3.4% | 6.6% | 2.4% |
| any spell check (typos, codespell, cspell, aspell) | 11.9% | 23.8% | 7.8% |
| docs build or deploy step in CI (mkdocs/mdbook/docusaurus/sphinx/cargo doc/hugo/pages) | 16.2% | 29.7% | 11.6% |
| docs build with warnings as errors (`--strict`, `-W`, `-D warnings`) | 3.9% | 12.1% | 1.1% |
| doc tests explicit (`cargo test --doc`, `--doctest`, `mdbook test`) | 3.7% | 8.8% | 2.0% |
| generated-file freshness gate (git diff --exit-code or `--check` near a generate step) | 9.7% | 17.9% | 6.8% |
| any of link/spell/markdownlint/vale/strict docs | 21.5% | 45.1% | - |

Generated-file gate by language: Go 24.2%, Rust 16.5%, TypeScript 15.0%, JavaScript 12.5%, Python 8.0%,
Ruby 5.7%, C++ 1.9%. Co-occurrence: 32 repositories both mark files `linguist-generated` and run a
freshness gate; 22 have a generated-docs path and a gate. A first, cruder regex counted 28.3% (it matched
any "generate" mention); the numbers above use a 400-character proximity rule and are still approximate
(a `git diff --exit-code` after `cargo fmt` near the word "docs" can match).

### 2.8 Onboarding signals (labels: 1209 repositories; 274 tools, 935 libs)

| Item | all | tools | libs/apps |
|---|---|---|---|
| good-first-issue style label (strict) | 58.5% | 57.3% | 58.8% |
| same, loose (adds easy, help wanted, low hanging) | 78.6% | 71.9% | 80.5% |
| help wanted label | 66.3% | 51.8% | 70.5% |

### 2.9 Per-directory READMEs (1083 untruncated repositories with at least two major directories)

"Major directory" = a top-level directory with at least 5 files, excluding noise names (tests, vendor,
assets, scripts, dist, node_modules, docs-like data dirs and similar).

| Item | all | tools | libs/apps |
|---|---|---|---|
| major directories with their own README | 29.5% (of 7869) | 30.9% (of 1734) | 29.1% (of 6135) |
| repository median share of major dirs with README | 13% | 22% | 9% |
| repositories where at least half the major dirs have one | 19.2% | 22.4% | 18.2% |
| repositories where no major dir has one | 43.8% | 31.5% | 47.5% |
| workspace members (crates/, packages/, apps/, libs/, modules/, plugins/, components/, services/ children with 3+ files) with README | 52.2% (4715 members, 182 repos) | 62.6% (2147, 66) | 43.5% (2568, 116) |
| repositories where at least half the workspace members have one | 56.0% | 72.7% | 46.6% |

Reading: per-directory READMEs are the norm for published packages (workspace members, where the README is
the package page: 62.6% in tools) and the exception for internal source directories (about 30%).

### 2.10 Search and versioning

Search is not measurable from a tree; it is implied by the generator (MkDocs Material, mdBook, Docusaurus,
VitePress, Sphinx and Starlight ship client-side search; Docusaurus usually adds Algolia). 19.6% of the sample
has a generator, so about one repository in five has searchable docs; the remaining 80% rely on GitHub's
own file finder and code search (section 5.8 covers the default-branch limit, UNVERIFIED). Versioned docs:
2.6% (angular, ant-design, apache/arrow, trivy, discourse, eslint, docusaurus, jest, material-ui, node,
pandas, prettier, puppeteer and a few more).

## 3. What the best-documented projects have in common

Ranking method: a transparent composite (README, CONTRIBUTING, COC, SECURITY, architecture, docs/, site,
changelog, issue forms, PR template, glossary, FAQ, troubleshooting, examples, docs index, spell check, link
check, docs build, generated gate, linguist-generated, RFC, ADR, good-first label, CODEOWNERS, governance,
maintainers, versioned docs, tutorial, how-to, development doc, plus Diataxis folders and README TOC; 30
binary features plus partial credit). Top by score: jj, open-policy-agent/opa, cilium, apache/airflow,
opentofu, argo-cd, openssl, ClickHouse, react-router, pytorch, uv, trivy, datafusion, storybook, node,
mermaid, celery, vitest, sphinx, puppeteer, envoy, ruff. Only 9 of 1254 repositories score 20 or more of about 32 possible points,
and 110 score 15 to 19.5: excellence is rare, and the score mostly rewards size (bigger projects have more
files to tick). I therefore chose ten exemplars by hand from the top list plus the projects the brief
named, for lessons that apply to frob rather than for score:

1. astral-sh/uv. Docs split into getting-started, guides, concepts, pip, reference (Diataxis under local names)
   in MkDocs Material; CLI, settings and environment reference are generated by `cargo dev generate-all` and
   are gitignored (built into the site, not committed); the JSON schema is committed and marked
   `linguist-generated=true`; CI has a `check-generated-files` workflow running `generate-all --mode dry-run`
   plus per-generator `--mode check` (schema, sysconfig, scenario tests, dirhash vectors); troubleshooting
   page; CONTRIBUTING tells you which command regenerates what.
2. astral-sh/ruff. Rule pages are generated from the doc comments on the rule definitions
   (`crates/ruff_dev/src/generate_docs.rs`), written to `docs/rules/` which is gitignored together with
   `docs/rules.md`, `docs/settings.md`, `docs/index.md`, `docs/contributing.md` (generated or copied from root files, per its CONTRIBUTING);
   `ruff.schema.json` and `generated.rs` are committed with `linguist-generated=true -diff`; CI job "mkdocs"
   runs the README transform, `generate_mkdocs.py`, a docs-formatting check and `mkdocs build --strict`;
   `generate-all` has `Mode { Write, Check, DryRun }`, a `REGENERATE_ALL_COMMAND` constant, and a unified
   diff truncated at 100 lines so stale files do not flood CI logs.
3. rust-lang/rust with rustc-dev-guide. One source for each error code: `E0xxx.md` written by hand, listed in
   a registry macro, rendered three ways (`rustc --explain`, the online error index via the
   error_index_generator, and doctests run by rustdoc with the code as an attribute, for example
   `compile_fail,E0004`); a tidy check cross-checks registry, explanation file, UI test and actual emission.
   rustc-dev-guide is an mdBook with a hand-kept SUMMARY.md, a glossary appendix, `<!-- date-check -->`
   comments that a bot turns into staleness issues, and a link checker in `book.toml`.
4. rust-lang/rust-analyzer. The ARCHITECTURE document that matklad's post points to: bird's-eye view,
   entry points, a code map per crate, cross-cutting concerns, explicit "Architecture Invariant:" sentences;
   generated code and manual sections (features, assists, config) are committed and refreshed by `cargo test`;
   generated files are named with a `_generated` suffix; manual is an mdBook.
5. jj-vcs/jj. Highest composite score. README (17 KB), CONTRIBUTING, GOVERNANCE, SECURITY, AI_POLICY, CHANGELOG
   at root; docs/ has FAQ, glossary, roadmap, design/ (one design doc per feature), revsets, config with a
   committed `config-schema.json`, and a CLI reference generated by an insta snapshot test whose header names
   the regeneration command; lockfiles marked `linguist-generated=true merge=binary`.
6. django/django. Sphinx; `docs/index.txt` is a hand-curated map by task ("First steps", "The model layer",
   "The view layer"...) rather than an alphabetical dump; folders intro (tutorials), howto, topics
   (explanation), ref (reference), faq, glossary, releases, internals; roughly 677 documents; the
   docs are the product's front door and the README is 2 KB.
7. kubernetes (kubernetes/kubernetes plus kubernetes/website). Website content is concepts, tasks, tutorials,
   reference, setup, contribute; reference holds a glossary of 163 entries, kubectl reference under
   `reference/kubectl/generated`, and a contributor page on generating reference docs; OWNERS files per
   directory give review routing; the code repository carries CONTRIBUTING, COC, SECURITY, MAINTAINERS-like
   OWNERS and issue forms.
8. open-policy-agent/opa. Docusaurus site with 657 documents, GOVERNANCE and MAINTAINERS, an RFC directory,
   lychee and vale in CI, docs build in CI, generated-file freshness gate, issue forms, FAQ and
   troubleshooting pages, a docs index.
9. cilium/cilium. Sphinx with 658 documents, glossary, FAQ, troubleshooting, tutorials and explanation folders,
   CODEOWNERS and MAINTAINERS, linguist-generated marking and a generated-file gate in CI.
10. rclone/rclone. One generated page per command (`docs/content/commands/rclone_*.md`), each carrying
    `autogenerated - DO NOT EDIT, instead edit the source code in cmd/size/ and as part of making a release run
    "make commanddocs"`: the marker names the source and the command, the output is committed, and it is
    refreshed at release. The best small example of the marker style frob needs.

Common traits across the exemplars:

- A hand-written front door that is short and routes (README or `index`), and a long tail of structured
  pages behind it. Django's index is a map by reader task; uv's by Diataxis quadrant; rust-analyzer's by crate.
- Reference is generated from the code (CLI help, config schema, rules, error codes), and the generator is
  the same program the developers run (`cargo dev generate-all`, `cargo bless`, `cargo insta`, `make
  commanddocs`, tidy). Explanation, tutorial and how-to are written.
- Every generated file says it is generated and says how to regenerate it, usually in the file; the
  source of truth is a doc comment or a schema, never the generated page.
- CI proves freshness (`--check`, dry-run, snapshot test, `git diff --exit-code`) and builds the docs
  with warnings as errors (uv, ruff: `mkdocs build --strict`; rustc: tidy).
- A short architecture or "how the code is laid out" document for contributors (rust-analyzer, jj design/,
  rustc-dev-guide), separate from the user docs.
- Layered contributor paths: CONTRIBUTING, issue forms, PR template, labels, CODEOWNERS or OWNERS per
  directory (kubernetes), governance for the large ones.
- Small, named, linked glossary or FAQ where the project invents vocabulary (jj, django, kubernetes, cilium).
- A committed, schema-validated machine-readable output next to the human page (ruff.schema.json,
  uv.schema.json, jj config-schema.json), which is the equivalent of frob's `docs/schemas/`.

## 4. Per-source study notes

### 4.1 matklad, "ARCHITECTURE.md" (2021-02-06, fetched in full)

Claims, in the author's words where short: for a project of 10k-200k lines add an ARCHITECTURE file next to
README and CONTRIBUTING; "it takes 2x more time to write a patch if you are unfamiliar with the project, but
it takes 10x more time to figure out where you should change the code"; keep it short because every
recurring contributor reads it and "the shorter it is, the less likely it will be invalidated"; "only specify
things that are unlikely to frequently change"; "Don't try to keep it synchronized with code. Instead,
revisit it a couple of times a year"; start with a bird's-eye overview of the problem; then a codemap that
answers "where's the thing that does X?" and "what does the thing that I am looking at do?"; "a map of a
country, not an atlas of maps of its states"; "name important files, modules, and types. Do not directly
link them (links go stale)" and let the reader use symbol search; call out architectural invariants,
especially the ones expressed as an absence; point out boundaries between layers; end with cross-cutting
concerns. The rust-analyzer document is named as the model; I fetched it and it has exactly that shape
(Bird's Eye View, Entry Points, Code Map with one subsection per crate, Cross-Cutting Concerns with code
generation, cancellation, testing, stability).

Survey fact: only 1.5% of repositories (19) have ARCHITECTURE.* at root and 2.8% (35) in docs/ (4.1% combined;
tools 5.6%); any-depth 14.1% (177) mostly means per-module architecture notes. The convention exists in the
projects whose authors read this post (oxc, swc, rollup, tauri, delta, dependabot-core at root) but is far from
mainstream. Implication for frob: ARCHITECTURE.md is hand-written and cheap; do not generate it. Generate only
a crate map table next to it, and never link line numbers.

### 4.2 Diataxis (diataxis.fr, fetched: home, compass, how-to-use pages)

Four forms for four needs: tutorials (learning, action), how-to guides (work, action), reference
(work, cognition), explanation (study, cognition). The compass: ask whether the content informs action or
cognition, and whether it serves acquisition or application of skill; the answers map to tutorial, how-to,
reference, explanation. Guidance that matters for frob: "Use Diataxis as a guide, not a plan"; "Don't worry
about structure"; it "certainly does not mean that you should create empty structures for tutorials/howto
guides/reference/explanation with nothing in them. Don't do that. It's horrible." Structure emerges by
improving documents one step at a time. Reference is the one quadrant that machines can write, because it
"describes the machinery" and should mirror the structure of what it describes (the code), which is why the
exemplars generate reference and write the other three. Adopted at Gatsby, Cloudflare and Vonage per the
site's testimonials.

Survey fact: the folder names are rare (0.3% exact all-four, 1.2% loose), but the four needs are visible in
every large doc set under local names. Implication: organise frob's docs by the four needs, name the folders
for the reader's task, and do not create a quadrant until it has a page.

### 4.3 rustc-dev-guide and the error index (fetched: SUMMARY.md, README, book.toml, error-codes.md; rust tidy, error_index_generator, rustc_error_codes/lib.rs, rustc_driver)

- One source, many renderings. Each code has a hand-written Markdown explanation
  `compiler/rustc_error_codes/src/error_codes/E0xxx.md`. A registry macro `error_codes!` in `lib.rs` lists the
  codes; the comment forbids removing entries ("Do not remove entries from this list... add a note to the
  markdown file saying that this error is not emitted by the compiler any more"). `rustc --explain E0004`
  (`handle_explain` in rustc_driver_impl, which looks the description up with `try_find_description`) prints
  the same Markdown in the terminal. `src/tools/error_index_generator` (201 lines) renders HTML for the online
  index (`render_html`, with a link list per code and a redirect page named error-index.html) or one big
  Markdown file (`render_markdown`: "# Rust Compiler Error Index", then "## E0xxx" per code). The examples in each
  explanation are doctests: the fence is annotated `compile_fail,E0004`, so rustdoc verifies that the example
  fails with exactly that code.
- Cross-checks (tidy `error_codes.rs`): every code in the registry has an explanation file containing a
  doctest that fails with the right code; every code has a UI test with both `.rs` and `.stderr`; every code
  is actually emitted by the compiler (a regex search over `compiler/`). The pattern is "registry of ids, one
  file per id, a checker that the three agree".
- The guide itself: an mdBook; `SUMMARY.md` is hand-maintained (14 KB; parts such as "Building and debugging
  rustc", "Bootstrapping", "High-level compiler architecture", appendices including a glossary); `about-this-guide.md`
  is the map in prose ("it's recommended that you search for the docs you're looking for instead of reading them
  top to bottom"); `<!-- date-check: Jul 2026 -->` comments mark claims that go stale and are collected by a
  bot; `book.toml` configures a link checker with an exclude list, a mermaid preprocessor, edit-url template
  and search.

Implications for frob: tickets are a registry of ids (ULIDs), one file per id; "indexes" are the second
rendering; a check that "every ticket is listed in exactly one epic index and every index row resolves to a
ticket" is the tidy analogue. Rule pages, error codes and directives in frob's own docs should follow the
same one-source pattern, with examples verified by the doc-test or mdtest runner (documentation.md section 3
already says rule pages embed mdtest examples).

### 4.4 Rust API documentation conventions (RFC 1574, API guidelines C-CRATE-DOC, C-EXAMPLE, C-QUESTION-MARK, C-FAILURE; fetched)

Crate-level docs are thorough and include examples; every public item has an example that shows why, not just
how; examples use `?`, not `unwrap`, with hidden `# ` lines compiled but not shown; fallible functions have
"# Errors", panicking ones "# Panics", unsafe ones "# Safety" sections; link all the things; the summary
sentence is one line. These conventions are already adopted in documentation.md section 1; the survey adds that
examples are verified code (cargo test --doc is run explicitly in only 3.7% of workflow bodies, because
`cargo test` runs doctests by default, so this number is a floor for Rust).

### 4.5 ruff and uv (fetched: CONTRIBUTING, mkdocs configs, .gitattributes, ci workflows, generate_all.rs, generate_docs.rs)

See exemplars 1 and 2. Additional specifics:
- Regeneration is one command: `cargo dev generate-all` (ruff CONTRIBUTING: "Update `ruff.schema.json`,
  `docs/configuration.md` and `docs/rules`"; individual `generate-cli-help`, `generate-docs`,
  `generate-json-schema`, `generate-options`, `generate-rules-table`). `--mode check` "Don't write to the file,
  check if the file is up-to-date and error if not"; `--mode dry-run` writes to stdout.
- The rule documentation lives in the rule's Rust doc comment (sections such as "What it does", "Why is this
  bad?", "Example"); the generator also stamps "Added in <release link>" from the rule's status metadata.
- What is committed versus built: ruff and uv do not commit generated Markdown pages (docs/rules/, CLI reference,
  settings, environment variables are gitignored and built for the site); they commit schemas and generated
  Rust. This is possible because they have a site; without one, nobody could browse the reference on GitHub. frob's
  ticket branch has no site, so the opposite choice (commit generated pages) is right there (section 7).
- The docs build is a CI job with `mkdocs build --strict`, a formatting check for code in docs, and a README
  transform that adapts the root README for the site.

### 4.6 Kubernetes and Django doc structure (fetched via the contents API and docs/index.txt)

- Django: top-level docs folders are `intro` (install plus the 8-part tutorial), `howto`, `topics` (27 pages
  of explanation, e.g. db, forms, auth), `ref` (reference), `faq`, `internals`, `releases`, `misc`, plus
  `glossary.txt`, `contents.txt` and `index.txt`. `index.txt` is a handwritten map: "First steps", "The model
  layer", "The view layer", "The template layer", "Forms", "The development process"... each with a bolded
  one-line pointer list ("**Models**: Introduction to models | Field types | ..."). It is the best example of a
  map by what the reader wants to do.
- Kubernetes website: `content/en/docs` has concepts (15 sections, e.g. overview, architecture, workloads),
  tasks, tutorials, reference (glossary, kubectl, generated reference), setup, contribute, and an `OWNERS`
  file. "Generated" is a directory name (`reference/kubectl/generated`), and there is a dedicated
  contributor page `generate-ref-docs`. The structure is Diataxis-shaped without using the names.

### 4.7 How GitHub renders a branch with only Markdown (fetched from github/docs sources; one point UNVERIFIED)

- README selection: GitHub shows the README from `.github/`, then the repository root, then `docs/`, in that
  order, if more than one exists. Content beyond 500 KiB is truncated (docs: "any content beyond 500 KiB will
  be truncated").
- Branch behaviour: relative links and image paths are rewritten against whichever branch is being viewed, so a
  link such as `docs/CONTRIBUTING.md` works on any branch and in clones; links starting with `/` are relative to
  the repository root; link text must be on one line. `docs`: "GitHub will automatically transform your relative
  link or image path based on whatever branch you're currently on".
- Free navigation: an Outline menu with an auto-generated table of contents for any rendered Markdown file
  (from headings); automatic section-anchor links on headings; Mermaid diagrams in fenced blocks (the docs list
  Markdown files, issues, discussions, pull requests and wikis); alert callouts with `> [!NOTE]`; file finder
  with the `t` key on the branch view.
- Directory pages: GitHub renders a directory's README under the file list when you navigate into it (the same
  way it does at the root). The about-READMEs page quoted above only says it surfaces README at `.github`, root
  and `docs`; the per-directory behaviour is well known but I did not find it in the fetched text, so treat it as
  UNVERIFIED here. It is the reason to put a README in every epic directory.
- UNVERIFIED (from memory, not fetched): GitHub's code search indexes only the default branch, so an orphan
  ticket branch is not searchable there; and directory listings in the web UI stop showing entries beyond about
  1000. Both argue for (a) a grep-friendly index page and (b) splitting big directories (an epic with hundreds of
  tickets, or one flat folder for all done tickets) and for relying on the tracker mirror for search.
- The branch picker lists any branch; an orphan branch has no relation to main, so "compare" is meaningless
  and "latest commit" on the root listing shows the last ledger commit message; the commit messages on this
  branch therefore double as the activity feed (`tickets(update): ~HANDLE title` in the current repository
  history already reads that way).

### 4.8 mdBook and Docusaurus generated navigation (fetched)

- mdBook `SUMMARY.md` is the one navigation file and is written explicitly: prefix chapters, part titles (`#`
  headings), numbered chapters (nested lists), suffix chapters, draft chapters `- [Title]()` (a title without a
  file, to mark planned pages), and `---` separators. There is no directory auto-listing in mdBook itself; large
  books either hand-maintain it (rustc-dev-guide, 14 KB) or generate it with a script.
- Docusaurus can generate the sidebar from the filesystem: `{type: 'autogenerated', dirName: '.'}` makes each
  folder a category and each file a link, and slices can be interleaved with explicit items. The sort is by
  path or by `sidebar_position` front matter; category metadata lives in `_category_.json`.
- Both separate "what exists" (the files) from "how it is presented" (an index), and the index is generated or
  checked: for frob, a generated index plus a check that every file is reachable is the same pattern.

### 4.9 GitHub wiki versus docs in the repository (fetched from github/docs)

- A wiki is a separate Git repository, editable on the web by anyone with write access (or by everyone, if
  configured). Search engines index wikis only for repositories with 500 or more stars and public edit
  disabled; wikis have a soft limit of 5,000 files ("For performance reasons"); "A README should only contain
  information necessary for developers to get started... Longer documentation is best suited for wikis"
  (GitHub's own advice).
- Against wikis for frob: not part of the clone or branch, not reviewed through pull requests, not versioned
  with the code, not checked by CI, not indexed. The survey agrees: wiki enabled in 33% of tools versus 58% of
  libs, while tools put docs in docs/ (67.6%) or a site (36.6%).
- For the ticket ledger: the branch is itself a Git repository of Markdown files that is browsable like a wiki,
  with history and CAS writes, so a wiki adds nothing; do not enable one for navigation.

## 5. Observations that follow from the data

5.1 Newcomer onboarding is mostly CONTRIBUTING (66.6%, 87% for tools), issue forms (49%) and a
good-first-issue label (58.5%). The cheapest newcomer devices on the ticket branch are the equivalents: a
start-here page, a ticket template (issue-form analogue) described in the guide, and a good-first index.

5.2 Maps are by task, not by directory (django, uv, rustc-dev-guide). An index of tickets by directory (epic)
is natural for the file layout; by status, milestone and component are the other three axes, and "what should I
do next" (ready, unblocked) is the task-shaped one.

5.3 Generation is cheap where one tool owns both the code and the docs (ruff, uv, rust-analyzer, jj). Where
the output is committed, the marker, the command and a freshness gate always appear together.

5.4 Rot is concentrated in prose that restates the code (counts, option lists, file trees). matklad's rule
("only specify things that are unlikely to frequently change") and rustc's date-check comments are the two
cheap defences; generating the restatement is the third.

5.5 Nearly all generated-docs markers are invisible when rendered (HTML comments), so a reader on GitHub
cannot tell. Visible text is rare (mermaid blockquote).

5.6 Heavy structure is a size effect: median docs/ has 23 documents (57 for tools); the exemplars have 600+.
A new project's docs should be small and flat first (Diataxis: no empty quadrants).

5.7 Per-package READMEs are normal for packages (52.2% of workspace members, 62.6% in tools) and rare for
internal directories (about 30%). A crate README is the package page; frob's design already includes them.

5.8 GitHub gives a table of contents, anchors and diagrams for free; do not generate in-file TOCs, and prefer
mermaid text over images in generated pages.

## 6. Things worth flagging in frob's current design text (small)

- mirror.md section 1 says tickets live at `<epic-slug>/<ticket-slug>.md`; tickets.md section 2 says
  `tickets/<id>/ticket.md` with `events/<ulid>.toml`. If both describe the same ledger, one needs to say
  which is the human view on the branch and which the machine layout; section 7 below assumes the mirror.md
  layout (human files by epic, events under `.events/`).
- If a ticket file moves when it is reparented, every external link to it (tracker issue bodies, commit
  trailers, other tickets) breaks. See decision 2 in section 8.
- documentation.md section 3 commits generated pages "so GitHub browsing and diffs work". The survey
  supports that for the ticket branch and for small reference sets, but ruff and uv build the same pages into
  a site instead of committing them; document the reason frob differs.

## 7. Recommendation: navigation documents for frob

### 7.1 Principles

1. One marker, one regex, one regeneration command per generated file. Machine-greppable first line plus a
   visible one-liner.
2. Generated files are a pure function of the ledger (or the code) and the frob version. No timestamps, no
   "generated on", no random order. Use "as of event <ULID>" or the last ledger commit id instead. This keeps
   diffs minimal and makes `--check` exact.
3. Index by every axis a reader asks about, but cap each page (about 200 rows; split by month for done).
4. Titles and handles in every row; never a bare ULID.
5. Written prose is installed from templates or hand-authored; generated pages contain tables and links only.
6. Generate the restatement, hand-write the reasoning (rustc: registry plus hand-written explanation).

### 7.2 Ticket branch (`frob-tickets`): recommended generated set

Layout (extends mirror.md section 1; every generated path is marked "G", installed-from-template "I"):

```
README.md                     G  front door (7.2.1)
GLOSSARY.md                   G  fields, states, categories, outcomes, link kinds, handles (7.2.4)
guide/README.md               I  index of the guide (Diataxis: one page per need)
guide/first-ticket.md         I  tutorial: file, start, close one ticket in five minutes
guide/how-to.md               I  how-to: pick, split, block, drop, read evidence
guide/why-a-branch.md         I  explanation: ULIDs, handles, events, one writer
indexes/README.md             G  map of the indexes below
indexes/by-status.md          G  one section per status category
indexes/by-milestone.md       G  one section per milestone, with done/total
indexes/by-component.md       G  one section per component
indexes/by-type.md            G  epics, stories, tasks, bugs, ...
indexes/ready.md              G  doable and unblocked, ranked
indexes/good-first.md         G  ready tickets carrying the good-first label
indexes/blocked.md            G  blocked tickets and what blocks them, one mermaid graph if small
indexes/recent.md             G  last 50 events (what changed, by whom)
indexes/done/<YYYY-MM>.md     G  closed tickets by month (keeps pages small)
<epic-slug>/README.md         G  epic page (7.2.2)
<epic-slug>/<ticket-slug>.md  -  the ticket (source of truth, not generated)
.events/README.md             I  two lines: machine event logs, do not edit, see guide
.events/<ULID>/...            -  event logs
.gitattributes                I  linguist-generated for G paths and .events
mirror.toml                   -  tracker map (when the mirror is on)
```

#### 7.2.1 Root README.md (generated)

The first screen answers: what is this, who is it for, how do I use it, where is the code, where is the
tracker mirror. Content order (about 100-150 lines):

1. Title, one sentence: "Work tracking for <repo>, kept in git. This branch is the ledger; the code is on
   `main`." Links: code repository (`https://.../tree/main`), tracker mirror (when configured), the guide.
2. Visible generated notice, one line (7.4).
3. "Start here" in three bullets: read `guide/first-ticket.md`; run `frob ticket doable`; ask `frob ticket show
   ~HANDLE`. The three commands, copy-pasteable (the same three as the code repository's TICKETS.md).
4. Counters table: epics, open by category, done last 30 days, blocked, ready (numbers only; row per
   category, each number links to the index section).
5. "In progress now" (table: handle, title, holder, since), capped at 15.
6. "Ready to pick" top 10, with link to `indexes/ready.md` and `indexes/good-first.md`.
7. "Epics" table: epic title linked to its README, open/total, nearest milestone.
8. "Recently changed" top 10 with link to `indexes/recent.md`.
9. "How this branch is organised" (a four-line legend of the tree above and the rule that file names are
   presentation and the ULID in frontmatter is identity).
10. Footer: frob version, schema version, "as of event <ULID>", regeneration command.

Justification from the survey: README is the one file everyone reads (99.1%); the median README is 159 lines
with a heading every 14 lines; 40% have a usage heading, so make "how to use" explicit; 14% have a TOC and
GitHub gives an Outline anyway, so do not add one.

#### 7.2.2 Per-epic README.md (generated)

GitHub renders it under the file list when the epic directory is opened (UNVERIFIED in the fetched docs, widely
observed), so it is the page a newcomer lands on after the root. Content: epic title, status, milestone,
owner, the epic's own description (taken from the epic ticket body, quoted, not duplicated: first paragraph
plus a link), a progress line (done/total, by category), a table of child tickets grouped by status category
(handle, title, type, priority, assignee, updated), blocked children with their blockers, links to the parent
and to indexes filtered by this epic, and the last 10 events. Cap at 200 rows; beyond that, link the by-month
done pages. Directory size matters (the UI listing limit, UNVERIFIED): prefer epics of under a few hundred files.

#### 7.2.3 Indexes (generated)

- by-status: sections triage, todo, in-progress, done (collapsed by default with `<details>`, 100 most recent and
  a link to the monthly pages), blocked (derived).
- by-milestone: each milestone as a section with done/total, due date, tickets by status. Includes a
  "No milestone" section so the page proves completeness.
- by-component: sections per component from the registry; "No component" last. By-label is not generated by
  default (labels are free-form and explode); by-type small.
- ready: the `frob ticket doable` result at the as-of event, with rank and scope; marks scope-overlap exclusions.
- blocked: table of blocked tickets and blockers; a mermaid graph only when fewer than about 40 nodes (GitHub
  renders mermaid; the survey did not fetch its size limits), else the table only.
- recent: last 50 events, newest first: time, ticket handle and title, event kind, actor. This is the page
  the commit feed cannot give.
- good-first: ready tickets that carry the configured label (58.5% of the sample uses a good-first-style
  label; it is the most common newcomer device).
- done/<YYYY-MM>: closed tickets by close month with outcome (done, wont-do, duplicate...), so the by-status
  page stays small.

Each index page starts with the marker (7.4), a one-line description of the axis and a link to the others
(`indexes/README.md`), and ends with the as-of line.

#### 7.2.4 GLOSSARY.md (generated from the schema)

The `TicketSchema` derive (tickets.md section 3) already generates the frontmatter schema, validation, the
`--json` schema and a docs table. Generate GLOSSARY.md from the repository's effective configuration, not the
defaults: fields (name, type, required, meaning, allowed values), custom fields declared in
`[tickets.custom_fields]`, status categories and the display names configured in this repo, outcomes, the link
kinds with inverses and topology, the handle and ULID rules, the evidence kinds. Three audiences read it:
newcomers (what does `blocked` mean), people reading raw files (what does `scope_mode` do), and the mirror
(field mapping). The code repository's `docs/reference/ticket-fields.md` is generated from the same derive for the generic
(default) schema; the branch copy shows this repository's real configuration.

Survey support: glossary files exist in 16.9% of tools but 20.4% of repositories with large docs, and every
exemplar that invents vocabulary has one (jj, django, kubernetes, cilium).

#### 7.2.5 Installed guide (not generated, not hand-edited on the branch)

Diataxis, with only pages that have content: one tutorial ("your first ticket"), one how-to page (task
headings), one explanation page ("why a branch, why ULIDs"). Source: templates shipped in the frob binary,
rendered with the repository name, branch name, handle prefix and configured commands; written by `frob
ticket init` and refreshed by `frob ticket reindex` when the frob version changes. Marker: the same GENERATED
marker, with the source named as "frob template guide/<name>, version X". Reference is the GLOSSARY and the
code repository's CLI reference (link, not copy).

#### 7.2.6 What frob must write into each commit

Because writes go through gob-git `commit_paths` with CAS (frob never merges), regenerate the affected
indexes in the same commit as the ticket change: the indexes are a pure function of the new tree, so a CAS
retry simply regenerates them again. A ticket status change touches: the ticket file, an event file, its epic
README, by-status, possibly by-milestone and by-component, ready, recent, and the root README. That is about
8 files per write; it is acceptable only because the output is deterministic and capped. Humans editing on
github.com (the one path that merges) are told in the marker to regenerate; `frob check` reports drift
(GEN001) and `frob ticket reindex` fixes it.

Alternative (for repositories with CI and the mirror's single CI writer): regenerate only the root README and
indexes in the mirror job and leave ticket commits to touch just ticket and event files. This lowers commit
noise (and merge pressure for people who use the web editor) at the cost of a lag of one CI run; offer it as
`[tickets] index_writer = "ci" | "inline"`, default inline.

### 7.3 Code repository: recommended navigation and reference set

Hand-written (not generated):
- `README.md`: banner, pitch, install, quickstart (frob is a tool: 78.7% of tools use badges, 80% have images,
  78% link to a docs site), links to docs, TICKETS.md and CONTRIBUTING.
- `CONTRIBUTING.md` (87% of tools), `SECURITY.md` (52.5%), `CODE_OF_CONDUCT.md` (51.8%), `CHANGELOG.md`
  compiled from fragments (the towncrier model in section 2.5).
- `docs/architecture.md` in matklad's form (bird's-eye view, code map by crate, invariants as "Architecture
  Invariant:" sentences, boundaries, cross-cutting concerns; names not links; revisit twice a year). The survey
  favours putting a root-level pointer so it sits "next to README and CONTRIBUTING" as matklad advises: only 1.5%
  of repositories have it at root and 2.8% in docs/, so either is defensible; frob's convention (docs/) is
  fine if README and CONTRIBUTING link to it in their first screen.
- `docs/style.md`, `docs/decisions/*.md` (ADR bodies), tutorials, how-tos, explanations per product.
- FAQ and troubleshooting (27.5% and 29.2% of tools), written as soon as there are ten real questions.

Generated (marked, committed, gated by GEN001):
- `docs/README.md`: the docs map, by reader task: Start here, Guides, Reference, Concepts, Contributing, Decisions
  (Django's index.txt as the model). Table of every top-level docs page with its first-sentence summary
  (taken from the page's first paragraph or front matter `summary:`), plus the section list. A map by a
  generator beats a hand-kept one because 42.6% of repositories with docs/ have no index at all and hand-kept
  ones drift; ensure each page is reachable from it (the check below).
- `docs/SUMMARY.md` (if mdBook is used): generated from the directory tree and a small order file for the
  top-level sections; reference sections are generated lists. mdBook has no autogenerated sidebar
  (Docusaurus does); rustc-dev-guide hand-maintains a 14 KB file, ruff generates the mkdocs nav
  (`generate_mkdocs.py`). Check "every `docs/**/*.md` appears in SUMMARY.md, or is explicitly excluded".
  Whether mdBook accepts an HTML comment as the first line of SUMMARY.md was not verified; test it before
  relying on it, else put the marker in a sibling `SUMMARY.generated` note or use a visible leading line the
  parser tolerates.
- `docs/reference/` (per documentation.md section 3): cli/, rules/, config.md, directives.md, errors.md,
  capabilities.md; schemas under `docs/schemas/`. One marker, one regeneration command (`cargo dev gen
  <name>`), the source of truth named in the marker (clap doc comments, the Rule derive...).
- `docs/decisions/README.md`: ADR index from front matter (documentation.md already says so).
- `docs/crates.md` (or a table in each directory README): crate name, one-line description from
  `Cargo.toml`, path, link to its README, and the dependency direction. Generated as a supplement; it must
  not replace ARCHITECTURE prose.
- `crates/<crate>/README.md`: per-crate READMEs (the package page; 52.2% of workspace members have one) are
  written by hand but start from a generated header (name, description, rustdoc link) so they never
  disagree with `Cargo.toml`. The ruff approach is a script that generates crate READMEs for published
  crates (`scripts/generate-crate-readmes.py`, in its CONTRIBUTING); frob's design already pulls the README into
  rustdoc via `include_str!`, which makes the README the single source for both.
- `TICKETS.md` (answers open question 3): a short generated file at the repository root: branch name and web
  URL, the three commands, tracker link, and the link to the ticket branch README. It only changes when
  configuration changes, so it never churns. README gets one hand-written line pointing to it. A generated
  block inside README would mix generated and written text in one file; the survey only found that done as
  a splice region (npm's "AUTOGENERATED USAGE DESCRIPTIONS"), which works for tables but is easy to edit by
  mistake.
- `docs/glossary.md`: hand-written terms (what frob, grimble, crunk mean) plus an included generated section for
  ticket fields and states from the schema derive (shared with 7.2.4).
- Per-directory README: for each top-level directory a short README that says what it is for (29.5% of
  major directories have one; 30.9% in tools). For internal directories, write one sentence and the
  neighbours; generate only the "contents" table if it is more than ten entries.

### 7.4 Marking generated files

Layers, use all three:

1. In-file machine marker (first line of Markdown; for non-Markdown files the language's comment syntax):

   `<!-- GENERATED by frob v<version>: DO NOT EDIT. Regenerate: <command>. Source: <path or "tickets"> -->`

   One regex for every generated file (`^<!-- GENERATED by frob `); modelled on Go's
   `^// Code generated .* DO NOT EDIT\.$` convention (which GitHub linguist also recognises in the first 40
   lines) and on the ty/clippy/jj/rclone markers, which name command and source. The ticket-branch commands
   are `frob ticket reindex` (all ticket-branch files) and, in the code repository, `cargo dev gen <name>`.
2. A visible one-liner under the title, because GitHub hides HTML comments in rendered Markdown. Use a quiet
   italic line or a GitHub alert (`> [!NOTE]`, rendered by GitHub), for example:
   `> Generated file - edit the tickets, not this page. Regenerate with frob ticket reindex.`
   Mermaid's docs use the same idea with a stronger warning.
3. `.gitattributes`: `linguist-generated=true` for generated paths. GitHub collapses the diff and excludes the
   file from language stats ("Excluded from stats, hidden in diffs" in linguist's overrides table); 21.8% of
   tools do this. For generated Markdown also add `-diff` only if the diffs are noise (ruff does for schema
   and generated.rs; for docs pages keep diffs visible so reviewers see what changed). On the ticket branch
   add `.gitattributes` with `README.md indexes/** */README.md GLOSSARY.md linguist-generated=true`.
   Also `* text=auto eol=lf` (ruff, jj) so Windows checkouts do not make `--check` fail.

Plus a naming convention where it is free: `reference/` is wholly generated; `_generated` suffix for isolated
generated files in hand-written folders (rust-analyzer); generated pages never sit beside hand-written pages
with the same stem.

Cross-checks for GEN001 (all cheap):
- every file matching the marker regex is produced by a registered generator (finds orphan generated files left
  after a generator is removed);
- every generator output has the marker (finds generators that forgot it);
- the command in the marker exists (parse `frob`/`cargo dev gen <name>` against the registry);
- marker version equals current frob version or the file is flagged "stale generator version" (a warning,
  not a failure, so upgrading does not break every branch).

### 7.5 Keeping them current: the GEN gate

1. Every generator implements `Mode { Write, Check }` (ruff and uv have `Write`, `Check`, `DryRun`; DryRun is
   useful for previewing).
2. `frob check` runs `cargo dev gen all --check` (code repo) and `frob ticket reindex --check` (ledger):
   regenerate in memory, compare byte for byte, print a unified diff truncated at 100 lines (ruff's
   `generated_file_diff` does exactly that so stale files do not flood CI logs), exit 1 on drift, naming the
   regeneration command.
3. CI repeats `frob check` (GEN001 stage); the ledger check also runs in the mirror job before publishing, so
   the tracker never receives something the branch cannot reproduce.
4. Test-time self-heal is available for developers: rust-analyzer's generated code is "updated automatically
   on `cargo test`" (and the test fails when a file changed); jj regenerates via `cargo insta test --accept`.
   frob may offer `frob fix` for the same effect, but CI stays check-only.
5. Reachability and completeness checks (rustc's tidy pattern): every ticket appears in exactly one epic
   README and one status section; every `docs/**/*.md` is in SUMMARY.md and in docs/README.md; every glossary
   field exists in the schema and vice versa; every link in generated pages resolves (lychee, or a
   built-in relative-link resolver; 5.6% of the sample runs link checks, 12.5% of tools).
6. Docs build with warnings as errors (`mdbook build` with a linkcheck backend; ruff and uv do `mkdocs build
   --strict`; 12.1% of tools use strict mode) and doc tests (`mdbook test`).
7. Version stamp, not date stamp, in generated files so only a real input change produces a diff.

### 7.6 What NOT to generate

- Per-ticket rendered pages. The ticket file is already readable Markdown; a second rendering doubles files
  and diffs and can disagree with the source.
- Anything with timestamps or "generated on". Use the as-of event or the frob version. (Also no counts in
  every directory README: counts belong in the root README and the epic README only.)
- Narrative: "summaries" of tickets written by a model or by templating, architecture text, tutorials, how-tos
  and explanations. Diataxis reference is the one quadrant machines write well; the other three need an author.
  ARCHITECTURE.md in particular must stay hand-written (matklad: short, stable, about invariants).
- API reference copied into Markdown. docs.rs/rustdoc is the generator and the host.
- Tables of every ticket on one page. GitHub truncates rendered files at 500 KiB and long tables are slow
  to render and impossible to scan; split by axis and by month.
- Tables of contents inside generated pages (GitHub's Outline does it; TOCs appear in only 14% of READMEs and
  34.5% of the longer ones).
- Images or SVG renderings of graphs (binary churn, no diff); use mermaid text with a size cap, or a table.
- Link lists that use ULIDs as the visible text; always handle plus title.
- Generated pages whose truth is "the defaults": the branch glossary must reflect the repository's
  configured statuses and custom fields, else it confuses (a newcomer reads that `todo` has `backlog` and
  `ready` when the repo renamed them).
- An index by label by default (labels are free-form and multiply files), by assignee (churn, privacy) or by
  priority (a column, not a page).
- A second generated documentation set in the tracker mirror: the mirror body should carry the ticket and
  two links (branch file and epic), not copies of the indexes.
- Anything in the code repository that restates the ticket state (burn-down tables in README, "open
  tickets" counters): they rot the moment a ticket moves and nothing in CI about code would refresh them.

Where generated docs rot or confuse (observed in the sample and design):
- Generator removed, file left behind: orphan generated files (cross-check in 7.4).
- Marker without a command, or command that no longer exists: the marker is useless; check it.
- Invisible markers: readers edit the rendered view; add the visible line.
- Generated from a newer or older frob than the one the next contributor has: stamp the version; upgrade
  regenerates on the next write.
- Two writers regenerate the same file and conflict (web editor, parallel clones): resolution is always
  "regenerate", never a three-way merge; say so in the marker.
- Directory moves: reparenting that moves a ticket breaks inbound links (decision 2).

## 8. Decisions for the owner (with a recommendation each)

1. Commit generated pages in the code repository (as documentation.md says) or build them only into the
   mdBook site (as ruff and uv do)? Recommendation: commit the small, GitHub-browsable ones (docs/README.md,
   reference pages, schemas, ADR index), mark them `linguist-generated=true`, and gate them; reconsider when
   the reference set is large enough that diffs become noise. The ticket branch always commits them (no site).
2. Do ticket files move when the parent epic changes? Recommendation: no. File path is frozen at creation
   (mirror.md says the slug is frozen); epic README and indexes are built from the `parent` field, so a ticket
   can be listed under a different epic than its directory; a lint note ("filed under ...") appears on the
   ticket page. Moves break tracker links, commit trailers and bookmarks. If moving is preferred, leave a stub
   at the old path that links to the new one.
3. Index writer: inline in every write commit (default) or only the CI mirror job (`index_writer = "ci"`)?
   Recommendation: inline default, CI option, per 7.2.6.
4. `TICKETS.md` as a generated root file (recommended) versus a README section.
5. Where ARCHITECTURE.md lives: `docs/architecture.md` (current) with a link at the top of README and
   CONTRIBUTING (recommended) versus root.
6. Include a `guide/` on the ticket branch (recommended: three pages) or only a README. Newcomers who have
   never used frob are the stated audience, and the survey's top-scoring repositories all carry
   tutorial/howto pages; the cost is three templates in the frob binary.
7. mdBook SUMMARY.md: generate (recommended, with order file) or hand-keep with a completeness check.

## 9. Raw data, scripts and reproducibility

All under `<scratchpad>/docs/`:

| Path | What |
|---|---|
| `curated.txt`, `curated_status.json` | the 287 curated names and their resolution status |
| `sample.json` | 1254 repositories with stars, language, tool flag, homepage, wiki, discussions |
| `01_sample.py` | builds the sample (curated plus language buckets) |
| `02_fetch.py` | recursive tree, README, .gitattributes, changelog head, workflows, labels (resumable) |
| `03_heads.py` | first 800 bytes of up to 12 docs files per repository |
| `04_analyze.py` | feature extraction to `features.json` |
| `05_stats.py` | the prevalence tables: `stats.txt` |
| `06_heads.py` | generated-marker pass: `heads_stats.txt` |
| `07_exemplars.py` | composite score and exemplar list: `exemplars.txt` |
| `extra.txt`, `arch_loc.txt` | extra cross-tabs, ARCHITECTURE location counts |
| `trees/`, `bodies/`, `labels/`, `heads/` | raw per-repository data |
| `src/` | fetched study sources: matklad post, Diataxis pages, rustc-dev-guide files, error index generator, ruff and uv CONTRIBUTING, mkdocs configs, gitattributes, workflow files, GitHub docs sources, mdBook and Docusaurus pages, RFC 1574, API guidelines |

Re-running: `python3 01_sample.py` (about 5 minutes), `02_fetch.py` (about 12 minutes with 32 threads),
`03_heads.py`, `04_analyze.py` (about 2 minutes), `05_stats.py`, `06_heads.py`. Nothing under the repository
except this file; no cargo, no frob, no clones.

Limits repeated for the record: path-based heuristics (a `docs/` directory is not a documentation system), no
quality measure, workflow-body regexes are approximate (numbers in 2.7 are indicative), label lists capped at
100, 18 truncated trees, search and wiki usage unmeasured, three UNVERIFIED claims in 4.7.
