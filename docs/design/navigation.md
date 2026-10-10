# Navigation: canonical ids, a verifiable reindex, generated docs, profiles and a tour

Status: current
Owner: frob
Decisions: D81
Audience: contributor

Provenance: ACCEPTED (D81, owner decisions 2026-10-04 on the documentation
survey, ticket ~AMBGYQ4). Evidence: notes/research/docs-survey.md (1254
repositories, ten exemplars). Depends on mirror.md (the ticket branch),
tickets.md (identity, events), documentation.md (generators, GEN001),
diagnostics.md (teaching).

The goal is one sentence from the owner: it must be the least confusing
thing possible for someone who has never seen the repository.

## 1. Identity: ids are references, paths are presentation

Ticket files live on the ticket branch at a path computed from the
ticket's current state, and that path changes when the ticket moves to
another epic (section 2). A path is therefore never a reference. Only the
canonical id is.

| Where | Allowed reference | Enforced by |
|---|---|---|
| hand-written text in the code repository (docs, code comments, commit messages, directives) | full ULID; `~handle` only in chat and CLI output (tickets.md 2) | TICK004 (below) and the existing abbreviated-id fixer |
| ticket bodies, comments and events on the ticket branch | full ULID or `~handle` (expanded to the ULID on write) | TICK004 |
| generated pages (README, indexes, epic pages) | relative paths, because they are regenerated whenever a path changes | GEN001 |
| the tracker mirror | the issue projection carries the ULID; links point to the issue or to `indexes/by-id/` | mirror.md 2.1 |
| CLI arguments | ULID, `~handle` or alias | a path argument is refused (`E-TICKET-PATH`) with the id it names: `that file is ~6C0D1E2; pass the id` |

- **TICK004 ledger-path-reference** (Error, P+, machine fix): tracked
  hand-written text links to a ticket-branch path
  (`<epic>/<slug>.md`, a blob or tree URL on the ticket branch, or the
  old `tickets/<ULID>/ticket.md` form). The machine fix rewrites the link
  to the ULID. The rule runs over the code repository and over the
  hand-written files of the ticket branch.
- **A permanent link that is not a path.** `indexes/by-id/<first two
  ULID characters after the time part>.md` lists every ticket with its
  ULID, handle, title and current path, split into small pages, so
  `.../indexes/by-id/` is a stable place to look up any id. Repositories
  that mirror to GitHub may also configure a GitHub autolink reference
  that turns a ULID into a link to the mirrored issue search (setup is
  printed by `frob mirror init`; the autolink format limits are
  UNVERIFIED and checked at implementation).
- `frob ticket url <id>` prints the current web URL of the ticket file
  and of the mirrored issue, for people who want a link to paste.

## 2. Where a ticket file lives, and the reindex commit

### 2.1 The path function

`path(ticket) = <top-epic-slug>/<ticket-slug>.md`, where the top epic is
the outermost epic ancestor. Sub-epics do not get directories: their
tickets sit in the top epic's directory and the epic page groups them
by sub-epic, so a reparent inside one epic never moves a file and paths
stay shallow. The epic ticket itself is `<top-epic-slug>/EPIC.md`.
Sub-epics are flattened by decision, not merely by default: there is
no directory hierarchy below the top epic. Tickets with no epic live in
`_unfiled/`, which the front door lists first so they get filed.

The slug follows the ticket's current title (owner decision): a title
change renames the file through the same reindex commit as a reparent,
so a file name never disagrees with its title. Slug rules: the title
transliterated to ASCII, lowercased, every run of other characters
replaced by one `-`, trimmed, cut at 60 characters on a word boundary;
an empty result becomes the handle without the `~`; two tickets in one
directory with the same slug both get `-<handle>` appended, so the
outcome does not depend on which was created first. Identity is the
ULID in the frontmatter and the `.events/<ULID>/` directory, both
unaffected by any move or rename.

### 2.2 Moves happen only in reindex commits

A change of parent or title is two commits, written and pushed together by the
same verb (or, with `[tickets] index_writer = "ci"`, the second by the
CI job):

1. The **decision commit**: the event (`field parent` or `field title`)
   and the ticket's refolded frontmatter. No file moves.
2. The **reindex commit**, made by `frob ticket reindex`: moves files to
   their computed paths and regenerates the generated pages. Message
   `tickets(reindex): after <event ULID>`, trailer
   `Frob-Reindex: <frob version>`.

The reindex commit is checkable as nothing but a reindex, exactly:

- **Replay check (TICK005, Error).** Run the reindex in memory on the
  parent commit's tree with the frob version named in the trailer; the
  resulting tree id must equal the commit's tree id. This proves the
  commit is the pure output of the reindex function, with no room for a
  hidden edit, because tree ids cover every byte. It needs no
  similarity heuristics: a moved ticket file keeps its blob id.
- **No moves elsewhere (TICK006, Error).** A ledger commit without the
  trailer may not rename or delete a ticket file or touch an event file
  it did not add.
- **No misfiled tickets (TICK007, Error, machine fix).** On the tip of
  the branch every ticket file is at its computed path; the fix is
  `frob ticket reindex`.

When the frob version in the trailer is not available locally, TICK005
reports Unresolved (reason `generator-version`) instead of guessing; CI
pins the frob version, so CI always decides it.

### 2.3 Moving an existing ledger onto the ticket branch

Milestone 1 repositories (this one included) keep tickets at
`tickets/<id>/` on the code branch. `frob ticket migrate --to-branch`
is a one-shot, verifiable move:

1. Build the orphan branch from the current tree: each
   `tickets/<id>/ticket.md` becomes `<top-epic-slug>/<slug>.md`, each
   `tickets/<id>/events/<ulid>.toml` becomes `.events/<id>/<ulid>.toml`,
   then generate the README, indexes and guide. `--dry-run` prints the
   mapping.
2. Verify before anything else changes: for every ticket, the fold of
   the branch copy equals the fold of the original (the doctor check on
   both), and the event counts match; any difference aborts.
3. Commit the branch, then one commit on the code branch that removes
   `tickets/`, sets `[tickets] storage = "branch"` (materialized), and
   adds the README region. Leases, evidence and land read the ledger
   through frob-ledger, which reads the configured storage.
4. Rollback is reverting that one code commit; the branch can be
   deleted. The migration ticket is the first user of the reindex
   replay check (TICK005), run on the initial branch commit.

### 2.4 Why this is the least confusing option

A newcomer opening `parser-rewrite/` sees every ticket of that epic and
nothing else; no ticket says "I actually belong elsewhere". History
survives the move (`git log --follow` sees an identical blob). The cost,
broken links to old paths, is removed by never linking paths (section 1).

## 3. The generated set

Adopted from the survey (section 7) with the owner's decisions. Every
generated file is a pure function of the ledger or the code plus the
frob version: no timestamps (an "as of event ULID" line instead), stable
order, capped pages.

### 3.1 Ticket branch

```text
README.md                     G  front door (3.3)
GLOSSARY.md                   G  fields, states, links, handles: this repository's effective config
TOUR.md                       G  the repository tour (section 5)
guide/README.md               I  two entry points: New here / Working here (section 4)
guide/new/first-ticket.md     I  tutorial: pick, do and finish one small ticket
guide/new/reading-a-ticket.md I  what each part of a ticket file means
guide/work/how-to.md          I  how-to: file, split, block, drop, reparent, read evidence
guide/work/why-a-branch.md    I  explanation: ULIDs, handles, events, one writer, reindex
indexes/README.md             G  map of the indexes
indexes/by-status.md          G
indexes/by-milestone.md       G
indexes/by-component.md       G
indexes/ready.md              G  doable and unblocked, ranked
indexes/good-first.md         G  ready good-first tickets with their start notes (section 4.2)
indexes/blocked.md            G
indexes/recent.md             G  last 50 events
indexes/done/<YYYY-MM>.md     G
indexes/by-id/<xx>.md         G  the permanent lookup (section 1)
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

### 3.2 Code repository

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

### 3.3 Marking and the gate

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

## 4. Two kinds of reader, and help for a first small task

### 4.1 Profiles

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

### 4.2 Good first tickets

The most common newcomer device in the survey (58.5 percent of
repositories) is a good-first label; frob makes it trustworthy:

- **PM031 good-first-incomplete** (Error on the label): a ticket labelled
  `good-first` must have at most `[tickets] good_first_max_points`
  points (default 2), a scope, Given/When/Then acceptance, and a
  `## Start here` section naming the files to read first, the test
  command and who to ask. `frob ticket new --good-first` scaffolds the
  section.
- **PM032 good-first-pool-low** (Warning): fewer than
  `[tickets] good_first_min` ready good-first tickets (default 3), so
  maintainers see when newcomers have nothing to pick.
- `frob ticket doable --newcomer` (the newcomer profile's default) and
  `indexes/good-first.md` list them smallest first with the start notes
  inline. The first-ticket tutorial ends by picking one of them.

## 5. The repository tour

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

## 6. New rules and verbs (summary)

| Id or verb | Kind | Meaning |
|---|---|---|
| TICK004 | Error, P+, machine fix | ledger-path-reference: a path used as a ticket reference |
| TICK005 | Error, P+ | reindex-not-pure: replay of a reindex commit does not reproduce its tree |
| TICK006 | Error, P+ | move-outside-reindex: a non-reindex ledger commit moved, deleted or edited existing ticket or event files |
| TICK007 | Error, P+, machine fix | misfiled-ticket: a ticket file is not at its computed path |
| PM031 | Error | good-first-incomplete |
| PM032 | Warning | good-first-pool-low |
| `E-TICKET-PATH` | CLI error | a file path was given where a ticket id is expected |
| `frob ticket reindex [--check] [--code-readme]` | verb | regenerate the ticket branch (and the README region) |
| `frob ticket url <id>` | verb | current web URLs for a ticket |
| `frob profile newcomer\|experienced` | verb | local presentation profile |
| `frob tour` | verb | the repository tour in the terminal |

## 7. Owner decisions (2026-10-04)

1. Sub-epics are flattened into the top epic's directory; no hierarchy
   below it.
2. A title change renames the file (section 2.1), through a reindex
   commit like any other move. Freezing slugs was rejected: with ids as
   the only references and the reindex proven pure by replay, a frozen
   slug's only effect would be a file name that disagrees with its
   title.
