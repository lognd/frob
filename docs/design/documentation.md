# Documentation: what is written, what is generated, and where rationale lives

Status: current
Owner: gob
Decisions: none
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Inputs: notes/documentation.md (rustdoc
conventions, how ruff, uv, ty, cargo, rust-analyzer, tokio and bevy
document, ADR practice, Diataxis, doc-gen tooling). Owner direction
2026-10-02: v1 source was full of ticket narrative that rotted; v2 must
generate what it can and keep the rest honest.

## 1. One home per kind of knowledge

| Kind of knowledge | Home | Never in |
|---|---|---|
| what a public item does, how to call it, what it returns, when it errors or panics | rustdoc on the item (`///`, `//!`), with `# Examples`, `# Errors`, `# Panics` per RFC 1574 and the API guidelines | markdown pages (they link to docs.rs instead) |
| a local, durable WHY that a reader of the next line needs (an invariant, a non-obvious constraint) | a `//` comment of at most one paragraph, at most one ticket pointer (a full ULID), pointing at an ADR or style anchor when the reason is longer | rustdoc, which users read without the tracker |
| deferred work | `// TODO(<ulid>): text` with the full ULID (the existing TODO001 contract) | bare TODO/FIXME |
| incident narrative, history, what was tried, measurements | the ticket body and events, the PR description, the commit body with a `Refs:` trailer | any source comment |
| a decision with alternatives and consequences | `docs/decisions/<date>-<slug>.md` (MADR, trimmed; section 5) | comments, tickets |
| architecture: codemap, boundaries, invariants | `docs/architecture.md` (matklad style: name symbols, not line numbers; "Architecture Invariant:" sentences) | scattered module docs |
| rules, CLI, config, schemas, directives, capabilities, errors, languages | generated reference pages from derives (section 3) | hand-written tables |
| tutorials, how-tos, explanations | written markdown per product in the Diataxis split | generated pages |
| what changed for users | `changelog.d/<ulid>.<type>.md` fragments compiled into `CHANGELOG.md` at release | commit log scraping |

## 2. Layout

```
docs/
  README.md                index
  architecture.md          workspace codemap, gob-* boundaries, invariants
  style.md                 code and comment rules, each with a Rationale line
  decisions/               ADRs; README.md index generated
  design/                  this set (explanation quadrant, cross-product)
  reference/               GENERATED (section 3): cli/, rules/, config.md, directives.md
  schemas/                 GENERATED JSON schemas
  frob/ grimble/ crunk/    tutorial.md, howto/, explanation/ (written)
CHANGELOG.md               compiled, never hand-edited between releases
changelog.d/               fragments
crates/<crate>/README.md   crate overview, pulled in by #![doc = include_str!("../README.md")]
```

Site: mdbook (one binary, `mdbook test` runs Rust blocks in prose,
no Python in the toolchain), with mdbook-admonish and mdbook-mermaid;
docs.rs for API docs. Revisit mkdocs only if search becomes a user
complaint.

## 3. Generated versus written

This table is the one path table; every other file links here.

| Page | Path | Source of truth | Generator |
|---|---|---|---|
| CLI reference | `docs/reference/cli/<product>.md` (plus `docs/reference/cli/any.md` for the verbs shared by every product, such as `schema`) | clap derive doc comments | `cargo dev gen cli` |
| man pages, completions (Milestone 2 or later (D36)) | `man/`, `completions/` | clap derive doc comments | `cargo dev gen cli` |
| config reference and schema | `docs/reference/config.md`, `docs/schemas/config.json` | `ConfigTable` derive and schemars | `cargo dev gen config` |
| rule pages | `docs/reference/rules/<ID>.md` (each embeds the rule's mdtest fire and clean examples; rows for severity, tier, scope, polarity and needs) | `Rule` derive doc comment (must contain a Remedy section or it does not compile) | `cargo dev gen rules` |
| directives (shared by all products) | `docs/reference/directives.md`, `docs/schemas/directives.json` | the `Directive` derive | `cargo dev gen directives` |
| crunk.toml reference and schema | `docs/crunk/config.md`, `docs/schemas/crunk.json` | the `crunk-spec` table types (serde and schemars; not registered in the frob config inventory) | `cargo dev gen config` and `cargo dev gen schemas` |
| envelope schema | `docs/schemas/envelope.json` | `gob-diagnostics` types | `cargo dev gen schemas` |
| errors, languages and fidelity (Milestone 2 or later (D36)) | `docs/reference/errors.md`, `docs/reference/languages.md` | the error codes, the adapter matrix and the `frob doctor --languages` fidelity report (level, capability precision, NotApplicable rules per language) | `cargo dev gen` |
| capabilities | `docs/grimble/reference/capabilities.md` | `Capability` derive | `cargo dev gen` |
| ticket and per-verb response schemas (the `TicketSchema` derive is landed; the generated pages are Milestone 2 or later (D36)) | `docs/schemas/ticket.json`, `docs/schemas/*-response.json` | ticket model and `--json` response types | `cargo dev gen schemas` |
| sibling contract schema (Milestone 2 or later (D36)) | `docs/schemas/sibling.json`, `docs/schemas/grimble-graph.json` | the sibling `--json` types (grimble-model.md 9.5, 9.3) | `cargo dev gen schemas` |
| ADR index | `docs/decisions/README.md` | ADR frontmatter | `cargo dev gen adr-index` |
| web types | `web/src/api.ts` | response schemas | `cargo dev gen ts` |
| editor grammar | `editors/grimble.tmLanguage.json` | grimble keyword table | `cargo dev gen editors` |
| `CHANGELOG.md` | `CHANGELOG.md` | fragments | `frob release changelog --version X` (frob-release; `cargo dev gen` calls it) |
| tutorial, howto, explanation, architecture, style, ADR bodies | `docs/<product>/...`, `docs/architecture.md`, `docs/style.md`, `docs/decisions/*.md` | humans | none; linted and drift-checked only |

One `Mode { Write, Check }` across generators; `cargo dev gen all
--check` is the gate (in CI it is the GEN001 stage; `--check` prints
unified diffs and exits 1 on drift). `gob-dev` exits 1 on its own
internal errors because it may not use `std::process`. `cargo dev` exists only in this workspace (gob-dev), so the
gate is a `[[check.tool]]` stage in this repo's `frob.toml`, whose
output maps to GEN001; it is repo-local, not a built-in rule that
consumer repos inherit. It runs in `frob check` so drift fails locally
before CI. Generated pages are committed so GitHub browsing, diffs and
terminal reading work with no site build (owner decision, D81; ruff and
uv build theirs into a site instead, and the survey supports either for
a small reference set). Marking, the README region, the generated
SUMMARY.md and the ledger-side generators are navigation.md 3.

## 4. Keeping ticket narrative out of code (enforced)

A policy pack shipped with frob (rule family NARR, over tree-sitter
comment nodes in every language, excepted only with an `accept` and a reason):

| Rule | Check |
|---|---|
| NARR001 | a `//`-style comment block mentions more than one ticket id, or exceeds 6 lines without being rustdoc or an `// Invariant:` block |
| NARR002 | history words in a comment (`used to`, `previously`, `regression`, `incident`, `hotfix`, `as of 20xx`, `see discussion`) |
| NARR003 | a ticket id inside rustdoc (`///`, `//!`) or a docstring |
| NARR004 | a comment longer than 3 lines containing `because` or `rationale` that does not reference `docs/decisions/` or `docs/style.md#` |
| NARR005 | a `frob:ticket` directive block followed by prose on adjacent comment lines (the directive binds; the story goes to the ticket) |

The ticket id the NARR rules match is the full 26-char ULID
(`[0-9A-HJKMNP-TV-Z]{26}`), the `~handle` form, and v1 aliases
(`T-` followed by digits); a bare 6-char prefix in prose is not
detectable and is not matched.

Directives (`frob:ticket`, `frob:todo <ulid>`, `frob:accept ... because=`,
`grimble:defer ... ticket=`)
are machine-read and exempt from NARR003; an exception reason is capped
at one sentence, with the longer reason in the ticket it names.
`frob narrative move` (kept from v1) relocates an existing block into
the ticket body and leaves the one-line pointer, so migration of v1
code is mechanical.

Where the narrative goes: the ticket (events and comments are the
timeline), the PR description, the commit body. `frob ticket show`
and `brief` render it; nothing is lost, it is just not in the code.

## 5. ADRs

MADR trimmed: title, status, date, ticket, Context, Decision,
Consequences, Alternatives considered (one line each), optional
Supersedes. Files are named `<date>-<slug>.md` (a short ULID suffix
disambiguates two ADRs with the same slug on one day), so concurrent
worktrees never collide; the generated index assigns display numbers
(`ADR-0007`) that are never reused and never persisted outside the
index. Required when a
change touches an "Architecture Invariant" sentence in
`docs/architecture.md`; the existing doc-drift mechanism (`frob:doc`
anchors and `frob ack`) binds those sections to the `gob-*` crate
roots, and a rule (DEC004) refuses a land that changes a bound crate
root without a new or updated ADR or an ack with reason. The v1
`decisions/AD-###` concept maps onto this directory.

## 6. CHANGELOG

Fragments `changelog.d/<ulid>.<notice|added|changed|fixed|removed|deprecated|security>.md`
(`notice` is the lead notice, one paragraph above the type groups, at most one per release section),
one or two user-facing sentences, first line prefixed with the product
(`frob:`, `grimble:`, `crunk:`). `frob release changelog` (frob-release;
`cargo dev gen` calls it) compiles per product under one version
heading and deletes the fragments. Gate: a
land that touches a product crate or a `gob-*` public item without a
fragment is refused (REL003, the only rule for fragment presence;
`[pm.done] changelog_fragment` evaluates it). REL003 is an Error: repository-wide
for every fragment the compile's validator rejects (unknown type, bad ULID, ULID
with no ticket, empty or non-ASCII body, near-miss product prefix); under
`check --ticket` also for the checked, still-open ticket that has no fragment
file; not applicable when `changelog_fragment` is not in `[pm] done_requires`
and there is no `changelog.d` directory. `frob ticket fragment TICKET
[--type T] [--sentence S] [--force]` writes the skeleton (from the ticket title, except as below) into
the ticket's worktree and validates it with the compile's own validator, so the agent
edits a sentence rather than inventing a file. The default type follows the ticket
type: bug and incident `fixed`, security `security`, story and epic `added`, every
other type (task, docs, chore) `changed`; `--type` overrides. For bug, security and incident tickets the title describes the
problem, not the change, so `--sentence` is required: without it the verb is a usage error
(exit 2) whose message shows `frob ticket fragment TICKET --sentence "<what changed for
the user>"`; every other type keeps the title default. One function
(`frob_release::fragment::sentence_required`) decides; `land` and `close` never write a
fragment, so the rule lives only in `ticket fragment`. `land` and `close`
never write it: a refusal on `changelog_fragment` names the verb, because a sentence
nobody read would defeat the point of the fragment. A change with no user-visible effect
(a design document, an internal refactor, a test-only change) needs no fragment: `ticket
close` and `land` accept `--no-changelog --reason TEXT` (both required together, no
exemption by file type), recorded as an audited `changelog-exempt` event that satisfies
`changelog_fragment` and REL003 for that ticket; `release status` lists the exempted
tickets of the milestone so a reviewer sees what shipped without a note. A refusal on
`changelog_fragment` names both `frob ticket fragment` and `--no-changelog --reason`.
git-cliff and release-plz are not used:
commit history is not the user-facing voice.

## 7. Rustdoc discipline

- `#![deny(missing_docs)]` in every crate; clippy `missing_errors_doc`,
  `missing_panics_doc`, `missing_safety_doc` and
  `rustdoc::broken_intra_doc_links` denied everywhere, locally and in
  CI, from the first commit (decided 2026-10-02).
- Every public item: summary line, blank line, detail; `# Errors` for
  every `Result`-returning function naming the error set variants;
  `# Examples` with a doc test for every public entry point of a
  `gob-*` crate.
- Private items documented when the WHY is non-obvious; one line.
- `cargo doc --document-private-items -D warnings` and `cargo test
  --doc` in CI; docs.rs metadata `all-features` and `rustdoc-args
  --cfg docsrs`.
- Crate README is the crate's lib doc through `include_str!`, so there
  is one text.

## 8. CI gates (run by frob check, so local and CI agree)

The external-tool gates are `[[check.tool]]` entries in this repo's
`frob.toml`, not built-in rules. They are spawns of the classes listed
in git-io.md section 3 and sit outside the 2 s check budget (they run
concurrently and are timed as separate stages).

| Gate | Command or rule |
|---|---|
| generated docs current | `cargo dev gen --check` (GEN001, repo-local tool stage) |
| rustdoc clean, doc tests | `cargo doc` with `-D warnings`, `cargo test --doc` (tool stage) |
| missing docs and sections | clippy lints above (tool stage) |
| site builds, links | `mdbook build`, `lychee --offline`; remote links weekly (tool stage) |
| spelling, markdown style | `typos`, `markdownlint` (tool stage) |
| comment hygiene | NARR001-005 |
| fragment present | REL003 |
| ADR present | DEC004 |
| doc drift | `frob:doc` / `describes` anchors and `frob ack` (existing) |
| doc-to-doc agreement, repeated text, facts in prose | include regions, `frob:same-as` pairs, checked facts, single definitions (doc-consistency.md, SYNC family) |

## 9. Writing style for the written pages

Diataxis: a tutorial teaches by doing one path end to end; a how-to
solves one task; reference is generated; explanation says why. Each
page states which quadrant it is in its first line. Sentences short,
one idea each, ASCII, no emoji; command blocks runnable as written;
every page under 400 lines or it is split.
