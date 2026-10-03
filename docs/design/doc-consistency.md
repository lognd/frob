# Doc consistency: one source, paired sections, checked facts

Status: ACCEPTED as the design (D84, ticket ~2NAP90Y). Evidence:
notes/research/docs-survey.md (1254 repositories; the exemplars ruff, uv,
jj, clippy, rustc, rust-analyzer generate reference from code, mark it,
and gate its freshness) and notes/research/docgen-survey.md (pending:
prevalence of include, splice, doctest and fact-check techniques; section
8 is updated when it lands). Builds on documentation.md (the generated
path table, GEN001), navigation.md 3 (markers, the README region),
code-model.md (directives, `frob:doc`, `describes`, `enumerates`), the
DRIFT family and `frob ack`.

Owner request (2026-10-03): stop drift within a doc, between docs, and
between docs and code, with a mechanism that forces docs to say the same
thing, and generate wherever possible.

## 1. What exists, and the gap

| Already enforced | How |
|---|---|
| code and doc stay paired | `frob:doc path#section` on a symbol (or `frob:describes` in the doc); `frob ack` records both digests; DRIFT001 fires when either side changes until the pair is re-read and acked |
| reference pages match the code | generated from one source (CLI, config, rules, schemas); GEN001 fails on a stale copy |
| links resolve | DOC002 |
| public items are documented | DOC001 |

The gap: nothing binds a doc to another doc, nothing checks the facts
prose states, and nothing stops the same thing being written twice. The
milestone-2 planner found fifteen contradictions across the design set
(the plan-cache location, two meanings of "pack", an id reused for two
rules), and every one of them was a fact written in two places.

## 2. The ladder: strongest first

No tool can prove that two differently worded paragraphs mean the same.
So the family turns every consistency need into one of four checkable
forms, and prefers the strongest that fits:

1. **One source, generated copies** (section 3). The copies cannot
   disagree; GEN001 keeps them byte-identical. Use for anything that is
   repeated verbatim.
2. **Checked facts** (section 5). Prose that names a CLI verb, a flag, a
   config key or its default, a rule id, a decision id, a path or a
   list of enum members is checked against the source of truth.
   Deterministic, no ack needed.
3. **Paired sections** (section 4). Two sections that must agree but
   are written differently (an explanation and its summary) are bound
   symmetrically; changing either flags both until a person re-reads
   them and acks.
4. **One home per definition** (section 6). A term or a decision is
   defined once; other places link to it. Duplicates are flagged
   with an include as the fix.

## 3. One source: include regions and generated summaries

### 3.1 Include regions

```markdown
<!-- frob:include docs/design/security.md#1-invariants -->
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

### 3.2 Generated summaries

Where many docs feed one overview, the overview is generated from
structured fields in the sources:

- **The decision log.** Each design doc carries its decisions in a
  front-matter table (`decisions: [{id: D84, summary: "...", status:
  accepted, ticket: ...}]`); the README's decision table is generated
  from them. A decision row can no longer disagree with its doc, and a
  decision id defined twice is SYNC006.
- **Rule tables in design docs** become generated from the rule
  registry plus a `planned` list for rules not yet implemented (section
  5.3), so a design doc's table and the reference page share one source.
- Other indexes (docs map, SUMMARY.md, ticket indexes) are already
  generated (navigation.md 3).

### 3.3 Editing a generated region

Text edited inside a region is SYNC002 (Error, fix maybe-incorrect):
the finding shows the diff and offers to move the edit into the source
section when the source is markdown, then re-render. Conflicts in
regions are resolved by re-rendering, never merged (navigation.md 3.3).

## 4. Paired sections: the doc-to-doc ack edge

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
  paired sections are near-identical (section 6).

## 5. Checked facts

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

### 5.0 Enumerations without a second copy

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

### 5.1 Three values

A fact whose source cannot be read (the CLI registry of a product not
built here, a config schema not generated yet) is Unresolved with the
reason, never passed. A fact in a file the walker cannot parse is
Unresolved `parse-error`.

### 5.2 Design docs that describe the future

Design docs name verbs, keys and rules that do not exist yet. They are
facts about the plan, so they are checked against the plan:

- A design doc may declare planned items in its front matter
  (`planned: {verbs: ["release cut"], keys: ["[pm] ready_min"], rules:
  [PM033, PM034]}`); a mention that matches a planned item passes. Once
  the item exists, the planned entry is SYNC015 planned-but-shipped
  (Warning, machine fix: remove it), so the list empties itself.
- A planned item declared in two docs with different meanings is the
  same as a definition conflict (5.3).

### 5.3 Ids are defined once

Every rule id, decision id, error code and verb has exactly one
defining place: the registry for implemented things, one design doc's
`planned` list for future things. **SYNC006 id-defined-twice** (Error)
fires when two places define the same id, including a retired id
reused with a new meaning (the REL001 case); retired ids are listed in
the registry with their retirement decision, and reuse needs the
decision id in the new definition.

## 6. One home per definition

- `frob:defines TERM` marks the canonical definition of a term (a
  glossary entry or a heading). **SYNC008 duplicate-definition**
  (Advisory) fires when another doc defines the same term (a heading
  equal to the term, or a bold term followed by a colon or a dash),
  with the fix "link to the canonical definition, or include it".
- **SYNC007 near-duplicate-section** (Advisory): two sections whose
  normalized text shares more than `[sync] duplicate_threshold`
  (default 0.8 by word shingles) and are neither an include nor a pair.
  The finding offers both fixes: make one an include of the other
  (machine fix when one side is a strict superset), or pair them.
- Generated text, includes and quoted blocks are excluded from both.

## 7. Rules, crate and placement

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
- **Teaching:** each rule's explain page shows the ladder (section 2)
  so a reader learns to reach for an include before a pair.

## 8. Self-application to this repository

1. Generate the README decision log from per-doc front matter (3.2),
   then turn the design docs' rule tables into generated tables.
2. The fifteen contradictions the planner found are the first fixture
   corpus: each becomes a fire example for the rule that would have
   caught it (SYNC006 for the reused REL001, SYNC007 for the plan-cache
   paragraphs, SYNC010 for knob defaults stated in prose), and the
   design set is fixed in the same tickets.
3. The docgen survey's findings (notes/research/docgen-survey.md)
   update this section and may adjust thresholds and the false-positive
   rules of section 5.
