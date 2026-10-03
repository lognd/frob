# Ticket branch and the one-way tracker mirror

Status: ACCEPTED with changes (D79, owner review 2026-10-04, ticket
~J8PJHKX). The changes: GitHub Issues is the first tracker, behind a
platform-agnostic producer that is descriptive enough to route to any
tracker (section 2.1); edited issues are skipped and the divergence is
reported loudly with explicit resolution verbs (section 3.1).
Earlier owner decisions: the ledger lives on a dedicated orphan branch,
approachable to newcomers; the first tracker integration is a one-way
mirror (repository to tracker); conversations are not mirrored back;
material tracker decisions may flow back later, with field ownership
instead of timestamps. The navigation documents on the ticket branch
are specified after the documentation survey
(notes/research/docs-survey.md).

## 1. The ticket branch

- A normal orphan branch, default name `frob-tickets` (materialized knob
  `[tickets] branch`), so every clone fetches it, the hosting UI lists it
  and it can be browsed on the web. Hidden custom refs were rejected:
  clones would silently lack the ledger.
- Layout for humans, identity for machines: `README.md` (generated),
  `<top-epic-slug>/<ticket-slug>.md` (slug frozen at creation; the file
  moves only in a verifiable reindex commit when its top epic changes),
  `.events/<ULID>/` (event logs). The ULID stays canonical in each
  file's frontmatter; paths are presentation and never references.
  frob resolves ids through its index, never through paths. The full
  layout, the generated pages and the reindex rules are navigation.md.
- frob writes the branch through gob-git commit_paths with CAS (D23), so
  the code checkout is never touched. Branch protection on the hosting
  side should forbid force pushes.
- The code repository carries one short pointer, a generated region of
  README.md (navigation.md 3.2), saying where tickets live, the three
  commands to use, and the tracker link.

## 2. The one-way mirror: what it does

The repository ledger is the source of truth. The mirror publishes each
ticket to one tracker (GitHub Issues, GitLab Issues or Jira; one adapter
each) and keeps it current. It never reads tracker edits back as truth in
this phase; it detects them and reports them.

| Ledger | GitHub Issues | GitLab Issues | Jira |
|---|---|---|---|
| title, body, acceptance | title, body sections | title, description | summary, description |
| type, labels | labels | labels | issue type, labels |
| priority, points | labels, project field | labels, weight | priority, story points |
| parent, children | sub-issues | epic or parent (plan dependent) | parent |
| blocked-by, relates, duplicates | issue relationships where available, else body links | blocks, related | issue links |
| category, outcome | open or closed with state reason | open or closed | workflow transition (mapping table) |
| scope, evidence, leases | body section (generated, read-only) | same | same |
| comments | not mirrored by default | same | same |
| ULID | hidden body marker and a label or custom field | same | custom field |

The field mapping is configuration (`[mirror.<tracker>]`), materialized,
versioned, and checked at load against the tracker's live schema.

### 2.1 The producer is platform agnostic: the issue projection

GitHub Issues comes first, but nothing GitHub-specific lives above the
adapter. The mirror is two stages with a typed value between them:

1. **Produce** (tracker-independent, in frob): fold the ledger into one
   `IssueProjection` per ticket, the full description of what any
   tracker should show. It is descriptive, not GitHub-shaped: it keeps
   every distinction a richer tracker could use, and adapters drop or
   flatten what their tracker cannot hold.
2. **Route** (one adapter per tracker): translate a projection into
   tracker operations through the mapping table, then diff against the
   tracker's state and publish through the outbox.

| Projection field | Content | Notes for adapters |
|---|---|---|
| `identity` | ticket ULID, handle, aliases, repository URL, ledger path | the ULID must be stored where the adapter can search for it |
| `title` | the ticket title | |
| `sections` | ordered, typed body sections: `summary`, `acceptance` (list of Given/When/Then), `scope` (paths), `evidence` (links and verdicts), `links`, `managed_notice` | each section has kind, heading and markdown; adapters render or map each kind (Jira wiki markup, GitHub and GitLab markdown) |
| `classification` | type, labels, priority, points, milestone, epic | typed values, never pre-rendered labels; the mapping decides label, field or issue type |
| `state` | category (todo, doing, done), outcome (done, dropped, superseded, duplicate) and reason | mapping table to open/closed with reason, or to workflow transitions |
| `relations` | typed edges with target identity: parent, child, blocked-by, blocks, relates, duplicates, supersedes | adapters choose native relations, else body links, and must say which in `capabilities` |
| `people` | owner and assignee as frob identities | resolved through `[mirror.identities]`; unmapped identities are left unassigned and noted |
| `provenance` | last event ULID, render digest, producer version | the digest is what divergence detection compares |
| `private` | fields withheld by `[mirror] exclude` | never sent; recorded so a reader knows something was withheld |

Each adapter declares a `capabilities` record (native sub-issues,
native links, custom fields, state reasons, markdown dialect) and the
mapping is checked against it at load: a projection field the mapping
neither routes nor explicitly drops is a configuration error, so no
information disappears silently. The projection's JSON schema is
generated from the Rust type (`cargo dev gen schemas`, file
`docs/schemas/issue-projection.json`) when the producer is implemented;
`frob mirror render <ticket>` prints a projection, so a GitLab or Jira
adapter can be developed and tested from recorded projections without
touching the producer.

## 3. The problems and their mechanisms

| Problem | Mechanism |
|---|---|
| **Who runs it, and with which credentials** | One writer: a CI job triggered by pushes to the ticket branch runs `frob mirror push`. The token lives in CI secrets with the least scope (issues write on one project). Developers run `frob mirror push --dry-run` locally to preview; local pushes are possible but opt-in. One writer removes races between machines. |
| **Partial failure and retries** | An outbox: each ledger event that needs publishing becomes an operation with an idempotency key (ticket ULID plus event ULID). The mirror keeps a map file `mirror.toml` on the ticket branch: ticket ULID to tracker key, last published event, and a hash of the last published rendering. Re-running is safe: an operation whose hash matches the tracker's current state is skipped; a failed one is retried next run. At-least-once delivery, idempotent effect. |
| **Rate limits and cost** | Incremental by default: only tickets with events after the last published event are touched. Conditional requests (ETags) where the API offers them, batching, exponential backoff that honours `Retry-After`. A full resync is an explicit verb. |
| **Identity** | Tracker key stored as a ticket alias (so `frob ticket show PROJ-123` works); ULID stored in the issue (hidden marker plus a label or custom field) so the mirror re-finds an issue even if the map file is lost. Duplicate detection on first sync: an issue already carrying the ULID is adopted, never duplicated. |
| **Edits made in the tracker** | Detected, never overwritten silently: before updating an issue the mirror compares the tracker's current rendering with the last published digest. If someone edited it, the mirror skips that issue and reports MIR002 (section 3.1). |
| **Deletions and drops** | Never delete in the tracker. A dropped ticket is closed with its reason; a deleted tracker issue is recreated and reported. |
| **Schema drift** | The adapter validates the mapping against the tracker's schema at startup (custom field ids, workflow states, labels). A missing field fails the run with one clear diagnostic and a remedy, before any write. |
| **Tracker or network down** | The run stops cleanly; nothing is half-written beyond the outbox; `frob check` reports MIR001 (Unresolved, not required by default) saying the mirror is behind by N events since a time. Never silent. |
| **Echo loops** | Not possible in one-way mode: the mirror never imports. In the later import phase, imported changes carry the tracker event id and are never re-published. |
| **Privacy and security** | Evidence transcripts are redacted (gob-log) before publishing; a `[mirror] exclude` list keeps sensitive tickets or fields private; the mirror never publishes leases' worktree paths. |
| **Upkeep per tracker** | One adapter crate per tracker behind a small trait (create, update, close, link, find-by-ULID, schema), with recorded API fixtures so tests run offline. |

### 3.1 Divergence is loud and resolvable (owner decision)

Skipping an edited issue is only safe if nobody can miss it. So:

- **Loud.** MIR002 is severity Error and a required finding: it fails
  `frob check` and the mirror CI job (exit 1), and it is repeated every
  run until resolved. The mirror job also posts one comment on the
  issue itself, once: the issue is managed from the repository, the
  edit was not applied, and who can resolve it with which command.
- **Specific.** The finding names the ticket, the issue URL, each edited
  field with its published and current values (a diff for body
  sections), the tracker user and the time, read from the tracker's
  history API where it exists.
- **Resolvable**, by one of three verbs, each recorded as a ledger event
  with the resolver and a reason, so the decision is auditable:

  | Verb | Effect |
  |---|---|
  | `frob mirror resolve <ticket> --keep-repo` | re-publish the repository version over the edit, with a comment linking the edit |
  | `frob mirror resolve <ticket> --adopt` | turn the tracker edit into a ledger change through the normal ticket verbs (the edit is applied to the ticket, then re-published), the manual form of the later import phase |
  | `frob mirror resolve <ticket> --ignore-field <field> --reason "..."` | stop mirroring that field for that issue (recorded in `mirror.toml`); the field becomes tracker-owned for that issue only |

  The diagnostic prints all three verbs as `help` lines (diagnostics.md),
  and `frob explain MIR002` explains when to choose which.

## 4. Later: bringing material decisions back

Field ownership decides conflicts, not timestamps: code-coupled fields
(scope, acceptance, evidence, links, done-by-land) are always owned by
the repository; a short list of planning fields (priority, cycle,
assignee, drop or reopen with a reason) may be declared tracker-owned;
everything else changed in the tracker arrives as a proposal event that
someone accepts or declines with `frob ticket proposals`. Tracker users
map to identities in configuration; unmapped users' changes are always
proposals. This phase needs polling or webhooks and is not part of the
first version.

## 5. Owner decisions and open questions

Decided 2026-10-04:

1. GitHub Issues first, behind the platform-agnostic projection
   (section 2.1); GitLab and Jira adapters route from the same
   projection later.
2. Divergence: skip and report, loudly and resolvably (section 3.1).

3. The code repository's pointer is a generated region of README.md,
   not a `TICKETS.md` (navigation.md 3.2).
