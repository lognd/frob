# Documentation: what is written, what is generated, and where rationale lives

Status: current
Owner: gob
Decisions: D20, D50, D84, D85
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Inputs: notes/research/documentation.md (rustdoc
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
  README.md                index of every document with its status (generated)
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
| config reference and schema | `docs/reference/config/frob.md`, `docs/schemas/config.json` | `ConfigTable` derive and schemars (the `$defs` each field's `$ref` links need are merged into the document root; a name clash keeps the first definition and logs a warning) | `cargo dev gen config` |
| rule pages | `docs/reference/rules/<ID>.md` (each embeds the rule's mdtest fire and clean examples; rows for severity, tier, scope, polarity and needs) | `Rule` derive doc comment (must contain a Remedy section or it does not compile) | `cargo dev gen rules` |
| directives (shared by all products) | `docs/reference/directives.md`, `docs/schemas/directives.json` | the `Directive` derive | `cargo dev gen directives` |
| crunk.toml reference and schema | `docs/reference/config/crunk.md`, `docs/schemas/crunk.json` | the `crunk-spec` table types (serde and schemars; not registered in the frob config inventory) | `cargo dev gen config` and `cargo dev gen schemas` |
| envelope schema | `docs/schemas/envelope.json` | `gob-diagnostics` types | `cargo dev gen schemas` |
| errors, languages and fidelity (Milestone 2 or later (D36)) | `docs/reference/errors.md`, `docs/reference/languages.md` | the error codes, the adapter matrix and the `frob doctor --languages` fidelity report (level, capability precision, NotApplicable rules per language) | `cargo dev gen` |
| capabilities | `docs/grimble/reference/capabilities.md` | `Capability` derive | `cargo dev gen` |
| ticket and per-verb response schemas (the `TicketSchema` derive is landed; the generated pages are Milestone 2 or later (D36)) | `docs/schemas/ticket.json`, `docs/schemas/*-response.json` | ticket model and `--json` response types | `cargo dev gen schemas` |
| sibling contract schema (Milestone 2 or later (D36)) | `docs/schemas/sibling.json`, `docs/schemas/grimble-graph.json` | the sibling `--json` types (grimble/grmb-spec.md 20.2, 9.3) | `cargo dev gen schemas` |
| docs index | `docs/README.md` | the status header of each document under `docs/` (DOC003 checks the headers) | `cargo dev gen docs-index` |
| Decision log | `docs/decisions/README.md` | `docs/decisions/decisions.toml` | `cargo dev gen decisions` |
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
SUMMARY.md and the ledger-side generators are documentation.md 3.

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
tickets of the milestone so a reviewer sees what shipped without a note. Epic and docs tickets need no fragment by default (`[pm] changelog_exempt_types`, ~YYJGRFJ; `[]` opts every type in, and a fragment they do carry is still validated). A refusal on
`changelog_fragment` names both `frob ticket fragment` and `--no-changelog --reason`.
`[pm] changelog_tests_only_types` (default `[]`, intended opt-in `["chore"]`) is the one
file-based waiver: a ticket of a listed type closes without a fragment when its branch diff
against the base touches only test files (a `tests/` directory, or a Python, TypeScript or C#
test file). An empty diff, a diff that also touches any other file, or a missing ticket branch
never qualifies, and a fragment the ticket does carry is still validated. The audited
`--no-changelog --reason` path stays file-agnostic.
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
in docs/design/shared/architecture.md section 3 and sit outside the 2 s check budget (they run
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
| broken relative links and anchors | DOC002 (follows `docs/MOVED.toml`) |
| orphan pages | DOC007: a `docs/` page that no markdown link chain from `docs/README.md` or a root page reaches; generated, `historical` and `superseded-by` pages are exempt; a heuristic, so waive with `frob:waive DOC007`; ships `off` until the docs overhaul (~DEPQFYE) |
| doc-to-doc agreement, repeated text, facts in prose | include regions, `frob:same-as` pairs, checked facts, single definitions (documentation.md, SYNC family) |

## 9. Writing style for the written pages

Diataxis: a tutorial teaches by doing one path end to end; a how-to
solves one task; reference is generated; explanation says why. Each
page states which quadrant it is in its first line. Sentences short,
one idea each, ASCII, no emoji; command blocks runnable as written;
every page under 400 lines or it is split.

## 10. Doc consistency: one source, paired sections, checked facts

Merged from the former documentation.md.
Status of this chapter: draft.

Provenance: ACCEPTED as the design (D84, ticket ~2NAP90Y). Evidence:
notes/research/docs-survey.md (1254 repositories; the exemplars ruff, uv,
jj, clippy, rustc, rust-analyzer generate reference from code, mark it,
and gate its freshness) and notes/research/docgen-survey.md (the same 1254 repositories: 43 percent
have no doc-consistency mechanism at all; includes are common only with a
site generator and use named anchors, almost never line ranges;
marker-region tools appear in none; hand-copied duplicate paragraphs are
in 85 percent of sampled docs sites; checks that prose mentions things
that exist are bespoke and rare; section 10.9 records what was adopted). Builds on documentation.md (the generated
path table, GEN001), documentation.md 3 (markers, the README region),
code-model.md (directives, `frob:doc`, `describes`, `enumerates`), the
DRIFT family and `frob ack`.

Owner request (2026-10-03): stop drift within a doc, between docs, and
between docs and code, with a mechanism that forces docs to say the same
thing, and generate wherever possible.

### 10.1 What exists, and the gap

| Already enforced | How |
|---|---|
| code and doc stay paired | `frob:doc path#section` on a symbol (or `frob:describes` in the doc); `frob ack` records both digests; DRIFT001 fires when either side changes until the pair is re-read and acked |
| reference pages match the code | generated from one source (CLI, config, rules, schemas); GEN001 fails on a stale copy |
| links resolve | DOC002 |
| every document under `docs/` has one status header from the fixed vocabulary, and `superseded-by` names an existing document | DOC003 |
| public items are documented | DOC001 |

The gap: nothing binds a doc to another doc, nothing checks the facts
prose states, and nothing stops the same thing being written twice. The
milestone-2 planner found fifteen contradictions across the design set
(the plan-cache location, two meanings of "pack", an id reused for two
rules), and every one of them was a fact written in two places.

### 10.2 The ladder: strongest first

No tool can prove that two differently worded paragraphs mean the same.
So the family turns every consistency need into one of four checkable
forms, and prefers the strongest that fits:

1. **One source, generated copies** (section 10.3). The copies cannot
   disagree; GEN001 keeps them byte-identical. Use for anything that is
   repeated verbatim.
2. **Checked facts** (section 10.5). Prose that names a CLI verb, a flag, a
   config key or its default, a rule id, a decision id, a path or a
   list of enum members is checked against the source of truth.
   Deterministic, no ack needed.
3. **Paired sections** (section 10.4). Two sections that must agree but
   are written differently (an explanation and its summary) are bound
   symmetrically; changing either flags both until a person re-reads
   them and acks.
4. **One home per definition** (section 10.6). A term or a decision is
   defined once; other places link to it. Duplicates are flagged
   with an include as the fix.

### 10.3 One source: include regions and generated summaries

#### 10.3.1 Include regions

```markdown
<!-- frob:include docs/design/shared/security.md#1-invariants -->
...generated copy, never edited by hand...
<!-- frob:end include -->
```

- Sources: a markdown section (`path#slug`, the heading and its body up
  to the next heading of the same or higher level), a whole file, or a
  code region marked in the source with `frob:region NAME` and
  `frob:endregion` comments (`path#region:NAME`), rendered in a fenced
  block with the source language. A line range is not allowed: line
  numbers move, names do not.
- Options, all host-defined: `heading=keep|drop|demote`, `fence=LANG`
  for code, `lines=N` to cap the copy with a visible "(continued in
  SOURCE)" link. No arbitrary transforms and no command output: output
  of a program is produced only by a registered generator (documentation
  .md 3), so an include can never execute anything (security.md I11).
- Includes nest; a cycle is SYNC003. The copy carries the source digest
  in the end marker (the closing comment gains `digest=blake3:...`) so
  staleness is a digest comparison, not a re-render.
- `frob fix` (or `cargo dev gen docs` in this repository) re-renders
  every region; GEN001's check covers them.

##### 10.3.1.1 Existing include syntaxes are read, not replaced

A repository that builds a docs site already has an include syntax:
mdBook `{{#include path:anchor}}`, MkDocs snippets `--8<--`, Sphinx
`literalinclude` and `include`, AsciiDoc `include::`, MDX imports. The
survey found these in 45.7 percent of site-generator repositories and
dedicated marker-region tools in none, so frob reads the existing
directives as pointers and gives them the gate the site tools lack
(only 6.8 percent of repositories run strict docs builds):

- the source file exists; a named anchor exists exactly once in its
  source, in a recognized comment form (mdBook `ANCHOR:` and
  `ANCHOR_END:`, MkDocs `--8<-- [start:name]`, Sphinx `:start-after:`,
  frob's `frob:region`); an empty region is an error (SYNC004);
- line-range includes are allowed for these tools but reported as
  Advisory SYNC007 "line ranges move; name the region" (the survey
  counted 798 anchor includes against 13 line ranges in mdBook);
- `frob:include` is for plain markdown read on GitHub or in a terminal,
  where no site build expands includes, so the copy must be committed.

##### 10.3.1.2 A changed region flags the prose around it

Transclusion keeps the quoted text current but not the explanation
around it, and no surveyed tool notices that. For includes of a code
region, frob records the region's digest in `frob.lock` against the
including section, the same way code-doc bindings work: when the code
region changes, the including section is flagged (SYNC001, "the code
this section quotes changed: re-read the explanation") until it is
acked. Includes of doc sections do not create this pair (a copied
section has no separate explanation to go stale).

##### 10.3.1.3 Crate docs from the README

`#![doc = include_str!("../README.md")]` single-sources a crate's README
and its rustdoc front page (12.3 percent of Rust repositories with a
`lib.rs`). Its known failure is relative links that work on GitHub and
break on docs.rs; frob's generated README header (documentation.md 3.2)
renders links that resolve in both places, and DOC002 checks them from
both roots.

#### 10.3.2 Generated summaries

Where many docs feed one overview, the overview is generated from
structured fields in the sources:

- **The decision log.** Each design doc carries its decisions in a
  `### Dn` section and one `[[decision]]` row in
  `docs/decisions/decisions.toml` (id, date, summary, status, home); the
  log at `docs/decisions/README.md` is generated from that file, and a
  missing home heading fails generation. New decisions are added there,
  never as prose rows. A decision row can no longer disagree with its doc, and a
  decision id defined twice is SYNC006.
- **Rule tables in design docs** become generated from the rule
  registry plus a `planned` list for rules not yet implemented (section
  5.3), so a design doc's table and the reference page share one source.
- Other indexes (docs map, SUMMARY.md, ticket indexes) are already
  generated (documentation.md 3).

#### 10.3.3 Editing a generated region

Text edited inside a region is SYNC002 (Error, fix maybe-incorrect):
the finding shows the diff and offers to move the edit into the source
section when the source is markdown, then re-render. Conflicts in
regions are resolved by re-rendering, never merged (documentation.md 3.3).

### 10.4 Paired sections: the doc-to-doc ack edge

```markdown
## 2. The ladder
<!-- frob:same-as docs/design/README.md#d84 -->
```

- `frob:same-as TARGET` in a section declares that this section and the
  target must say the same thing. The pair is symmetric: declaring it on
  either side is enough, declaring it on both is fine.
- `frob ack` records the digests of both sections in `frob.lock` (the
  same lock entries as code-doc bindings; DRIFT004's re-attestation
  covers format changes).
- **SYNC001 paired-section-drift** (Error): one side changed since the
  ack. The finding shows both sections and the diff of the changed
  side, and names the remedy: update the other side if needed, then
  `frob ack --pair A B --reason "..."`. An ack where only one side
  changed and the other was not opened in the same change is allowed,
  but its reason is mandatory, as for all acks.
- A pair whose target is gone is DRIFT002 (dangling target), as for
  code bindings.
- Groups: `frob:same-as` may name several targets; a change to any
  member flags the group.
- Pairs are the fallback, not the default: if the two sections could be
  one source plus an include, SYNC007 (Advisory) suggests it when the
  paired sections are near-identical (section 10.6).

### 10.5 Checked facts

Facts in prose are found by shape, inside code spans and fenced blocks,
and checked against their source of truth. Prose outside code spans is
not interpreted.

| Fact | Recognized as | Checked against | Rule |
|---|---|---|---|
| a CLI invocation | a code span or a shell block line starting with a product of this repository (`frob`, `grimble`, `crunk`) | the CLI registry (gob-cli): the verb path exists, each flag exists on it, enum values are valid | SYNC009 unknown-cli-reference (Error; did-you-mean) |
| a config key | a code span `[table] key` or `[table] key = value`, or a TOML block | the config schema: the key exists; a value stated with the word "default" next to it equals the schema default | SYNC010 config-fact-mismatch (Error; fix maybe-incorrect: replace with the schema default) |
| a rule id | `[A-Z]+[0-9]{3}` in a code span or a table cell | the rule registry plus the planned-rules list (5.3) | SYNC011 unknown-rule-id (Error) |
| a decision id | `D[0-9]+` | the generated decision log | SYNC012 unknown-decision (Error) |
| a path | a code span that looks like a repository path (contains `/` and an existing top-level directory, or ends in a known extension) | the tree at HEAD | SYNC013 dangling-path-mention (Warning; DOC002 stays the rule for links) |
| a list of members | the list or table following `frob:enumerates SYMREF` (5.0; no members attribute) | the members of the enum, the fields of the struct, the verbs of a CLI group, the keys of a config table, the rules of a family | SYNC014 enumeration-mismatch (Error; fix: remove extra rows (machine), add missing rows with placeholders (has-placeholders)) |
| a ticket reference | full ULID or `~handle` | the ledger | REF001 (exists) |

Rules for false positives: a span is checked only when its first token
names something this repository owns (a product, a config table, a
rule family, a directory); anything else is not a fact. A doc can mark
a deliberately historical or foreign mention with `frob:historical` on
the span's line (for example "v1 had `frob ticket sprint migrate`"),
which is counted in the summary and never checked.

#### 10.5.0 Enumerations without a second copy

v1's `frob:enumerates` carried its own copy of the members in a
`members="..."` attribute: one line, up to 5879 characters in v1's own
docs, unreadable in a diff, and maintained by hand next to the readable
list it duplicated. v2 removes the copy. The directive names only the
symbol; the claim is the doc's own list:

```markdown
<!-- frob:enumerates crates/gob-rules/src/family.rs::Family -->
| Family | What it checks |
|---|---|
| `DOC` | documentation coverage and links |
| `DRIFT` | code and doc pairs |
```

- **The claim is the next list or table** after the directive: the
  first column of a table, or the first code span of each list item.
  Rows keep their hand-written descriptions; only the keys are checked.
- **Modes:** `exact` (default: the keys equal the members), `subset`
  (`frob:enumerates SYM subset`: every key is a member, for a doc that
  discusses a few), and `ordered` (keys in declaration order). A
  filter narrows the members compared: `where prefix=A11Y`.
- **Fix (machine for removals, has-placeholders for additions):** a
  missing member gets a new row in declaration order with the
  description cell `(describe this member)`, which SYNC014 keeps
  flagging until it is replaced; a key that is no longer a member has
  its row removed.
- **Members come from the source of truth:** enum variants, struct
  fields, the verbs of a CLI group, the keys of a config table, the
  rules of a family (registries are queried, not parsed from text). A
  shape the extractor cannot resolve is Unresolved, never a pass (v1's
  rule, kept).
- **When nothing is hand-written per member, do not claim, generate.**
  A list with no descriptions (v1's 5879-character case was a plain id
  list) is an include region rendered from the symbol
  (`frob:include crates/...::Sym#members`), which cannot drift and
  needs no check. `enumerates` is for lists that carry prose per member.
- No ack is involved: the members are re-derived on every run (v1's
  insight: a list can match its last ack and still be wrong).

##### 10.5.0.1 Claim shapes

The markdown adapter (tree-sitter-md) parses headings, lists, list
items, GFM pipe tables and inline code spans. Headings are extracted
today (they are sections); tables, lists and code spans inside them are
new extraction work for the prose query (universal-model.md Q11).

| Shape | Selected by | Keys are | Everything else is |
|---|---|---|---|
| table | `as=table` (or auto) | one cell per row in the key column: the first column, or the column whose header is named by `column="Family"` | free prose (descriptions, other columns) |
| list | `as=list` (or auto) | the first code span of each top-level item; else its leading bold text; else the item has no key and is SYNC014 Unresolved "put the member name in backticks" | nested items and the rest of the item text |
| headings | `as=headings` | the text of each heading one level below the directive's section (code spans and emphasis stripped) | the body under each heading, including its subheadings |
| section | `as=section` | the union of keys from every table, list or heading group in the directive's section and all its subsections | groupings: a doc may split members across subsections ("Families that read code", "Families that read tickets") |

- **Extent.** The claim starts after the directive and ends at the next
  heading of the same or higher level than the directive's section.
  Auto-detection takes the first table, list or heading group in that
  extent; when the extent holds more than one candidate block, auto is
  ambiguous and the finding is Unresolved with "add as=..." (no
  guessing). `frob rule why SYNC014 path:line` shows which block was
  read and which keys it found.
- **Key normalization.** Strip one code span, link syntax (the link
  text is the key), emphasis, and trailing punctuation; compare
  case-sensitively. Formatting otherwise does not matter to the check:
  `` `DOC` ``, `[`DOC`](rules/DOC.md)` and `**DOC**` are the same key.
  A cell or item holding two or more code spans is ambiguous and
  Unresolved for that row ("one member per row").
- **Member names.** A member may have several names: the identifier
  (`Doc`), a serde or clap rename (`doc`), a display string (`DOC`).
  By default a key matches any declared name of its member; `key=ident`,
  `key=serde` or `key=display` pins one. A key matching two members is
  Unresolved.
- **Duplicates.** A key listed twice in one claim is a finding (in
  `section` mode this is how a member filed under two subsections is
  caught).
- **Order.** `ordered` checks declaration order. Without it, order is
  free, and the fix still keeps whatever order the block already has.
- **Several docs.** Directives sharing `group=NAME` are checked
  together: each is a subset, and their union must equal the members
  ("every rule family is documented on some page").

##### 10.5.0.2 Fixes written in the block's own shape

- A missing member is inserted in the existing block's shape: a table
  row with the same column count and `(describe this member)` in each
  prose cell; a list item with the same bullet or number style and the
  key in a code span if the siblings use one; a heading at the same
  level with a placeholder paragraph.
- Placement keeps the block sorted the way it already is. If the keys
  are in declaration order, insert after the member's predecessor; if
  they are alphabetical, insert alphabetically; otherwise append and
  say so in the fix summary.
- Removing a stale member removes its row, item, or heading with its
  body (a heading's body is shown in the fix preview, because it may
  hold prose worth keeping elsewhere; the fix is maybe-incorrect for
  headings, machine for rows and items).
- In `section` mode a missing member has no obvious subsection, so the
  fix is has-placeholders and asks which group it belongs to.

##### 10.5.0.3 Adopting fact checks in an existing repository: a ratchet

Heuristic doc checks fail by noise (the survey's evidence: typos has 172
false-positive issues; markdownlint MD051 and lychee have the same
history). Two controls:

- **Recognition is narrow** (section 10.5): only code spans whose first
  token names something this repository owns.
- **A shrink-only baseline**, copied from cpython's nit-picky check:
  `frob sync baseline` writes the currently unresolved references to
  `.frob-sync-baseline` (committed, generated, marked). A check fails on
  any unresolved reference not in the baseline, and also when a
  baseline entry now resolves (SYNC016 baseline-entry-resolved, machine
  fix: remove it). The baseline can only shrink, so adoption never
  starts with a wall of findings and never regresses.

Facts are harvested from a generator's input (the config schema, the
clap definitions, the rule registry), never from its rendered pages, so
a stale generated page cannot make a stale mention look valid.

#### 10.5.1 Three values

A fact whose source cannot be read (the CLI registry of a product not
built here, a config schema not generated yet) is Unresolved with the
reason, never passed. A fact in a file the walker cannot parse is
Unresolved `parse-error`.

#### 10.5.2 Design docs that describe the future

Design docs name verbs, keys and rules that do not exist yet. They are
facts about the plan, so they are checked against the plan:

- A design doc may declare planned items in its front matter
  (`planned: {verbs: ["release cut"], keys: ["[pm] ready_min"], rules:
  [PM033, PM034]}`); a mention that matches a planned item passes. Once
  the item exists, the planned entry is SYNC015 planned-but-shipped
  (Warning, machine fix: remove it), so the list empties itself.
- A planned item declared in two docs with different meanings is the
  same as a definition conflict (5.3).

#### 10.5.3 Ids are defined once

Every rule id, decision id, error code and verb has exactly one
defining place: the registry for implemented things, one design doc's
`planned` list for future things. **SYNC006 id-defined-twice** (Error)
fires when two places define the same id, including a retired id
reused with a new meaning (the REL001 case); retired ids are listed in
the registry with their retirement decision, and reuse needs the
decision id in the new definition.

### 10.6 One home per definition

- `frob:defines TERM` marks the canonical definition of a term (a
  glossary entry or a heading). **SYNC008 duplicate-definition**
  (Advisory) fires when another doc defines the same term (a heading
  equal to the term, or a bold term followed by a colon or a dash),
  with the fix "link to the canonical definition, or include it".
- **SYNC007 near-duplicate-section** (Advisory): paragraphs of at least
  100 characters and 15 words are normalized (lowercase, links to their
  text, punctuation stripped) and hashed; two sections sharing more
  than `[sync] duplicate_threshold` (default 0.8) of their paragraphs,
  or two files sharing 80 percent, are reported unless they are an
  include or a pair. Exact copies rank above diverged near-copies (same
  start and end, different middle), whose precision was about 50
  percent in the survey. The survey ran this over 7146 files in under a
  minute in plain Python, so it is cheap enough for every check.
- **Exempt classes:** versioned docs directories, translation
  directories, and generated files (marker or declared generator
  output).
- **Agent-instruction mirrors** (`CLAUDE.md`, `AGENTS.md`, `.cursor/`,
  `.claude/`, `.agents/` rules that copy one another, the newest mirror
  class in the survey) are reported as their own class with the fix
  "declare one canonical file and generate the others".
- **Keep-in-sync comments.** 13.1 percent of repositories carry
  comments like "keep in sync with X" or "also update Y" in code,
  config or workflows, checked by nothing. SYNC017 keep-in-sync-comment
  (Advisory) finds them and offers to turn each into a `frob:same-as`
  pair, so the wish becomes a check.
  The finding offers both fixes: make one an include of the other
  (machine fix when one side is a strict superset), or pair them.
- Generated text, includes and quoted blocks are excluded from both.

### 10.7 Rules, crate and placement

| Id | Name | Severity | Polarity | Fix |
|---|---|---|---|---|
| SYNC001 | paired-section-drift | error | P+ | manual (ack) |
| SYNC002 | edited-generated-region | error | P+ | maybe-incorrect |
| SYNC003 | include-cycle | error | P+ | manual |
| SYNC004 | include-source-missing | error | P+ | manual |
| SYNC005 | include-stale | error | P+ | machine (re-render) |
| SYNC006 | id-defined-twice | error | P+ | manual |
| SYNC007 | near-duplicate-section | advisory | P0 | machine or maybe-incorrect |
| SYNC008 | duplicate-definition | advisory | P0 | manual |
| SYNC009 | unknown-cli-reference | error | P+ | manual (did-you-mean) |
| SYNC010 | config-fact-mismatch | error | P+ | maybe-incorrect |
| SYNC011 | unknown-rule-id | error | P+ | manual |
| SYNC012 | unknown-decision | error | P+ | manual |
| SYNC013 | dangling-path-mention | warn | P+ | manual |
| SYNC014 | enumeration-mismatch | error | P+ | machine |
| SYNC015 | planned-but-shipped | warn | P+ | machine |
| SYNC016 | baseline-entry-resolved | error | P+ | machine |
| SYNC017 | keep-in-sync-comment | advisory | P0 | maybe-incorrect |

- **Engine:** `gob-docsync`, product-neutral (grimble and crunk
  document too): section addressing and digests (shared with
  gob-text), include rendering, fact extraction, the planned-items and
  definitions index. The rules are a frob family, written in GRL where
  possible once the executor exists (the fact checks need typed side
  relations: the CLI registry, the config schema, the rule registry,
  the decision log; grl-spec.md 6), and tier-0 Rust until then.
- **Cost:** facts and sections are extracted per file and cached with
  the other per-file payloads; pair and definition checks are per
  repository over the cached index. Target: under 100 ms warm on this
  repository.
- **Teaching:** each rule's explain page shows the ladder (section 10.2)
  so a reader learns to reach for an include before a pair.

### 10.8a Not built: spelling, prose style and external link checks

Spell checkers, prose linters and external link checkers are adopted by
single-digit percentages and are noisy; frob does not reimplement them.
It provides the glue: they run as trusted tool stages (security.md 2.4)
whose findings map into the envelope, and the section 10.5.0.3 ratchet
applies to them too.

### 10.8 Self-application to this repository

1. Generate the README decision log from per-doc front matter (3.2),
   then turn the design docs' rule tables into generated tables.
2. The fifteen contradictions the planner found are the first fixture
   corpus: each becomes a fire example for the rule that would have
   caught it (SYNC006 for the reused REL001, SYNC007 for the plan-cache
   paragraphs, SYNC010 for knob defaults stated in prose), and the
   design set is fixed in the same tickets.
3. Docs in this repository that copy one another (the design docs'
   repeated rule tables, the two layouts of the ticket ledger) are the
   first SYNC007 corpus.

### 10.9 What the docgen survey changed

Adopted from notes/research/docgen-survey.md section 5: reading existing
include syntaxes (3.1.1), named regions only (3.1.1), re-read pairs for
quoted code (3.1.2), README single-sourcing (3.1.3), the shrink-only
ratchet and harvesting from inputs (5.0.3), duplicate thresholds and
classes (6), keep-in-sync comments (SYNC017), glue instead of new prose
tools (8a). Not adopted: an explicit typed inline reference syntax for
facts (for example a `cli-flag:` prefix inside code spans), because it
makes rendered docs harder to read; narrow recognition plus the ratchet
gives the same false-positive control.

## 11. Navigation: profiles, generated docs and the tour

Merged from the former documentation.md.

Provenance: ACCEPTED (D81, owner decisions 2026-10-04 on the documentation
survey, ticket ~AMBGYQ4). Evidence: notes/research/docs-survey.md (1254
repositories, ten exemplars). Depends on frob/tickets.md (the ticket branch,
identity, events), documentation.md (generators, GEN001),
cli-contract.md (teaching).

The goal is one sentence from the owner: it must be the least confusing
thing possible for someone who has never seen the repository.

Sections 11.1, 11.2, 11.6 and 11.7 of the former text (ids as references, the ticket path function and the reindex, the
rules and verbs summary, the owner decisions) now live in [frob/tickets.md](../frob/tickets.md) sections 2.3, 11 and 11.5-11.6;
the numbers below are unchanged so that existing citations stay valid until this document is merged.

### 11.3 The generated set

Adopted from the survey (frob/tickets.md section 11.6) with the owner's decisions. Every
generated file is a pure function of the ledger or the code plus the
frob version: no timestamps (an "as of event ULID" line instead), stable
order, capped pages.

#### 11.3.1 Ticket branch

```text
README.md                     G  front door (3.3)
GLOSSARY.md                   G  fields, states, links, handles: this repository's effective config
TOUR.md                       G  the repository tour (section 11.5)
guide/README.md               I  two entry points: New here / Working here (section 11.4)
guide/new/first-ticket.md     I  tutorial: pick, do and finish one small ticket
guide/new/reading-a-ticket.md I  what each part of a ticket file means
guide/work/how-to.md          I  how-to: file, split, block, drop, reparent, read evidence
guide/work/why-a-branch.md    I  explanation: ULIDs, handles, events, one writer, reindex
indexes/README.md             G  map of the indexes
indexes/by-status.md          G
indexes/by-milestone.md       G
indexes/by-component.md       G
indexes/ready.md              G  doable and unblocked, ranked
indexes/good-first.md         G  ready good-first tickets with their start notes (section 11.4.2)
indexes/blocked.md            G
indexes/recent.md             G  last 50 events
indexes/done/<YYYY-MM>.md     G
indexes/by-id/<xx>.md         G  the permanent lookup (frob/tickets.md section 2.3)
<epic>/README.md              G  epic page
<epic>/EPIC.md                -  the epic ticket
<epic>/<ticket-slug>.md       -  a ticket (source of truth)
_unfiled/                     -  tickets without an epic
.events/<ULID>/               -  event logs (machine)
.gitattributes                I  linguist-generated for G paths and .events; eol=lf
```

G is generated by `frob ticket reindex`; I is installed from templates
shipped in the frob binary, rendered with the repository's names and
commands, refreshed by reindex when the frob version changes. Neither
is edited by hand. The content of each page follows survey 7.2.1 to
7.2.5 (front door order, epic page, index axes, glossary from the
effective configuration, never the defaults).

#### 11.3.2 Code repository

- **Generated pages are committed, marked and checked** (owner
  decision). Unlike ruff and uv, which build reference pages into a
  site, frob commits them so they read on GitHub, in diffs and in a
  terminal pager with no site build; the cost, generated diffs, is
  contained by `linguist-generated` and GEN001. documentation.md 3 is
  the path table.
- **The ticket pointer is a section of README.md** (owner decision:
  nobody opens a `TICKETS.md`). It is a generated region:

  ```markdown
  <!-- GENERATED by frob: BEGIN tickets. Regenerate: frob ticket reindex --code-readme -->
  ## Tickets
  ...branch link, the three commands, tracker link...
  <!-- GENERATED by frob: END tickets -->
  ```

  GEN001 checks the region byte for byte and refuses edits inside it;
  the rest of README is hand-written. It changes only when ticket
  configuration changes.
- **docs/architecture.md** stays where it is, hand-written in matklad's
  form, linked in the first screen of README.md and CONTRIBUTING.md.
- **docs/SUMMARY.md is generated from an order file**, `docs/order.toml`
  (hand-written: the sequence of top-level sections and pages);
  reference sections are generated lists. The gate checks that every
  `docs/**/*.md` appears in SUMMARY.md or is explicitly excluded. This
  is also the reading order for terminal reading: a pager can walk
  SUMMARY.md in order (next and previous file), so the docs read
  front to back.
- `docs/README.md` (the map by reader task) and the per-crate README
  headers are generated as in survey 7.3.

#### 11.3.3 Marking and the gate

Three layers on every generated file (survey 7.4): the first-line
marker `<!-- GENERATED by frob v<version>: DO NOT EDIT. Regenerate:
<command>. Source: <source> -->` (one regex for all), a visible line
under the title (`> Generated: edit the tickets, not this page.
Regenerate with frob ticket reindex.`), and `linguist-generated` in
`.gitattributes`. GEN001 runs in `frob check` and in the mirror job:
every generator has `Write` and `Check` modes; `--check` regenerates in
memory and prints a capped unified diff; the cross-checks of survey 7.4
(orphan generated files, missing markers, marker commands that do not
exist, stale generator version as a warning) and 7.5 (every ticket in
exactly one epic page and one status section, every docs page in
SUMMARY.md, glossary equals schema, every relative link resolves) are
part of it. Conflicts in generated files are never merged: resolution
is always to regenerate, and the marker says so.

### 11.4 Two kinds of reader, and help for a first small task

#### 11.4.1 Profiles

Two reader profiles, used in two places:

- **In the documents**: the guide and the front door have two entry
  points, "New here" (what tickets are, how to pick a small one, how to
  finish it, how to read the repository) and "Working here" (verbs,
  workflow, gates, reindex, mirror). Every guide page says at the top
  which profile it is for and links to the other.
- **In the tools**: a local profile, `frob profile newcomer|experienced`
  (stored in `.frob/profile.toml`, local and disposable, default
  newcomer until the person has closed three tickets in this
  repository, then a one-time note suggests switching):

  | Behaviour | newcomer | experienced |
  |---|---|---|
  | `[ui] teach` | `always` for the first five occurrences of each std rule (counts in `.frob/seen.toml`), then `first`; pack rules are never taught inline (security.md 2.10) | `first` |
  | after each verb | a one-line "next step" (`next: frob work ~X`) | none |
  | `frob ticket doable` | good-first tickets first, with their start notes | ranked by priority |
  | unknown verb or failure | the three most likely commands and the guide page | did-you-mean only |

  The profile changes presentation only: never what a check decides,
  never a gate.

  Implementation: `crates/frob/src/profile.rs` resolves the profile and
  supplies the text-only presenter hooks (`next:` line, failure help)
  that `gob-cli` calls after a verb; JSON output is never touched. The
  teach-count rule is `Profile::teach_for`; wiring it to
  `.frob/seen.toml` waits on the teaching-state ticket.

#### 11.4.2 Good first tickets

The most common newcomer device in the survey (58.5 percent of
repositories) is a good-first label; frob makes it trustworthy:

- **PM031 good-first-incomplete** (Error on the label): a ticket labelled
  `good-first` must have at most `[tickets] good_first_max_points`
  points (default 2), a scope, Given/When/Then acceptance, and a
  `## Start here` section naming the files to read first, the test
  command and who to ask. `frob ticket new --good-first` scaffolds the
  section with `<TODO: ...>` placeholders, and PM031 reports a section
  that still contains one.
- **PM032 good-first-pool-low** (Warning): fewer than
  `[tickets] good_first_min` ready good-first tickets (default 3), so
  maintainers see when newcomers have nothing to pick.
- `frob ticket doable --newcomer` (the newcomer profile's default) and
  `indexes/good-first.md` list them smallest first with the start notes
  inline. The first-ticket tutorial ends by picking one of them.

### 11.5 The repository tour

A short generated walkthrough, `TOUR.md` on the ticket branch and
`frob tour` in the terminal, that teaches how this repository works by
walking through real examples from it. Prose comes from templates in the
frob binary (stable, written by people); the facts and examples are
filled in from the repository (generated). Nothing is model-written.

Stops, in order:

1. **What lives where**: the code branch and the ticket branch, and the
   top-level code map (from the grimble model nodes when present, else
   the workspace members), each with its one-line description.
2. **An epic**: the largest open epic, its page, and how its tickets are
   grouped.
3. **The life of one ticket**: a real done ticket followed through its
   events (create, start, evidence, land, close), with the land commit
   on the code branch and the evidence record, each linked.
4. **The rules that guard the repository**: the gates `frob check` runs
   here, from the effective configuration, with one real finding
   explained if there is one.
5. **Your turn**: one ready good-first ticket, with its start notes and
   the three commands to take it.

The examples are pinned so the tour does not churn: the first reindex
picks them deterministically (the most recently closed ticket with
evidence and a land, the largest epic, the first good-first ticket by
ULID) and writes them to `[tour]` in `frob.toml` (materialized knobs);
a pinned example that disappears or is dropped is replaced on the next
reindex and reported as a note. `frob tour` shows the same stops one at
a time, with next and previous, and opens linked files in the pager.

The `[tour]` section of `frob.toml` holds the pins and the hand-written
facts. The pins are `epic` (stop 2), `closed` (stop 3) and `good_first`
(stop 5), each a ticket id; an empty value lets the reindex pick one as
above. The facts are `code_map` (stop 1), a list of `"path: one-line
description"` strings, and `gates` (stop 4), a list of `"name: one-line
description"` strings; when empty, the code map falls back to the model
nodes or workspace members and the gates to the effective
configuration. None of the keys is enforced; the full table is in
[the config reference](../../reference/config/frob.md).

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D20

Documentation: reference pages generated from derives, mdbook site, MADR ADRs bound to architecture invariants, towncrier-style fragments, NARR rules forbid ticket narrative in code

### D50

Generated docs (T-0016): pages live at `docs/reference/{rules/<ID>.md, directives.md, config.md, cli/<product>.md}` and schemas at `docs/schemas/*.json`; `cargo dev gen all --check` is the GEN001 stage in CI; gob-dev exits 1 on internal errors because it may not use `std::process`; the PROC001 allow list is gob-exec, gob-git and frob (binary)

### D84

Doc consistency (~2NAP90Y): a ladder, strongest first: one source with generated copies (include regions from markdown sections and named code regions, no command output; generated summaries such as the decision log from per-doc front matter); checked facts in code spans (CLI verbs and flags, config keys and stated defaults, rule ids, decision ids, paths, enumerates) against their source of truth, with design docs declaring planned items; symmetric `frob:same-as` pairs acked in frob.lock (the doc-to-doc edge); one home per definition with near-duplicate detection. Family SYNC001-017 in a product-neutral gob-docsync engine; the docgen survey added reading existing include syntaxes (mdBook, MkDocs, Sphinx, AsciiDoc, MDX), re-read pairs for quoted code regions, a shrink-only ratchet baseline, duplicate classes and keep-in-sync comments

### D85

Design consistency pass 2 (~FDTYYEE): fifteen planner findings resolved; executable caches leave the work tree while per-worktree parse and findings caches stay with MAC'd, engine-scoped rows; a pack is a directory and packs-and-plugins.md's TOML is its tier-1 data file; crate homes named (gob-plan, gob-std, gob-wasm::worker, gob-fix); GRL rewrites are fixtures until a family moves; ledger migration to the ticket branch specified; GATE001 cleared only by an exception; base findings from git objects for changed files; CI016

Also logged against: notes/review/design-consistency.md.
