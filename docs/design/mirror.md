# Ticket branch and the one-way tracker mirror

Status: DRAFT under T-0001, for owner review (proposed decision D79).
Owner decisions so far: the ledger lives on a dedicated orphan branch,
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
  `<epic-slug>/<ticket-slug>.md` (slug frozen at creation), `.events/<ULID>/`
  (event logs). The ULID stays canonical in each file's frontmatter;
  paths are presentation. frob resolves ids through its index, never
  through paths.
- frob writes the branch through gob-git commit_paths with CAS (D23), so
  the code checkout is never touched. Branch protection on the hosting
  side should forbid force pushes.
- The code repository carries one short committed pointer (`TICKETS.md`
  or a README section, generated) saying where tickets live, the three
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

## 3. The problems and their mechanisms

| Problem | Mechanism |
|---|---|
| **Who runs it, and with which credentials** | One writer: a CI job triggered by pushes to the ticket branch runs `frob mirror push`. The token lives in CI secrets with the least scope (issues write on one project). Developers run `frob mirror push --dry-run` locally to preview; local pushes are possible but opt-in. One writer removes races between machines. |
| **Partial failure and retries** | An outbox: each ledger event that needs publishing becomes an operation with an idempotency key (ticket ULID plus event ULID). The mirror keeps a map file `mirror.toml` on the ticket branch: ticket ULID to tracker key, last published event, and a hash of the last published rendering. Re-running is safe: an operation whose hash matches the tracker's current state is skipped; a failed one is retried next run. At-least-once delivery, idempotent effect. |
| **Rate limits and cost** | Incremental by default: only tickets with events after the last published event are touched. Conditional requests (ETags) where the API offers them, batching, exponential backoff that honours `Retry-After`. A full resync is an explicit verb. |
| **Identity** | Tracker key stored as a ticket alias (so `frob ticket show PROJ-123` works); ULID stored in the issue (hidden marker plus a label or custom field) so the mirror re-finds an issue even if the map file is lost. Duplicate detection on first sync: an issue already carrying the ULID is adopted, never duplicated. |
| **Edits made in the tracker** | Detected, not overwritten silently: before updating an issue the mirror compares the tracker's current rendering with the last published hash. If someone edited it, the mirror reports a MIR002 divergence finding naming the fields and the tracker user, and (by policy knob) either skips that issue or overwrites it with a comment saying the ticket is managed from the repository and where to edit it. Default: skip and report. |
| **Deletions and drops** | Never delete in the tracker. A dropped ticket is closed with its reason; a deleted tracker issue is recreated and reported. |
| **Schema drift** | The adapter validates the mapping against the tracker's schema at startup (custom field ids, workflow states, labels). A missing field fails the run with one clear diagnostic and a remedy, before any write. |
| **Tracker or network down** | The run stops cleanly; nothing is half-written beyond the outbox; `frob check` reports MIR001 (Unresolved, not required by default) saying the mirror is behind by N events since a time. Never silent. |
| **Echo loops** | Not possible in one-way mode: the mirror never imports. In the later import phase, imported changes carry the tracker event id and are never re-published. |
| **Privacy and security** | Evidence transcripts are redacted (gob-log) before publishing; a `[mirror] exclude` list keeps sensitive tickets or fields private; the mirror never publishes leases' worktree paths. |
| **Upkeep per tracker** | One adapter crate per tracker behind a small trait (create, update, close, link, find-by-ULID, schema), with recorded API fixtures so tests run offline. |

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

## 5. Open questions

1. Which tracker first?
2. Divergence policy default: skip and report (proposed), or overwrite
   with a pointer comment?
3. Should the code repository's pointer be a committed generated
   `TICKETS.md`, or a section inside README.md?
