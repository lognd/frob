# Ticket branch and the one-way tracker mirror

Status: current
Owner: frob
Decisions: D79
Audience: contributor

Provenance: ACCEPTED with changes (D79). Owner decisions 2026-10-04: GitHub
Issues first behind a platform-agnostic producer (section 2.1); tracker
edits never block anything (section 3.4). The protocol (section 3) was
rewritten from an adversarial audit and a TLA+ model (ticket ~HV53M66).
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
  `<top-epic-slug>/<ticket-slug>.md` (the slug follows the title; the
  file moves only in a verifiable reindex commit when its top epic or
  title changes),
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

## 3. The protocol (audited and model-checked)

Evidence: notes/review/mirror-audit.md (an adversarial audit: 1 critical,
9 high, 17 medium, 6 low findings MIR-AUD-01 to 33; 30 GitHub facts
verified against GitHub's documentation, 16 marked UNVERIFIED) and
docs/design/models/mirror/ (a TLA+ model checked with TLC: the first
version of this protocol violated no-loss, convergence, no-duplicate
and map integrity; with the fixes F1-F9 below every safety property
holds in every checked configuration, up to 12.8 million distinct
states). The model's README has the properties, the counterexamples
and an inductive argument for the safety properties beyond the model's
bounds.

No part of this protocol ever fails a check or blocks a land (owner
decision). Failures surface as MIR001 (mirror behind, with a reason)
and in `frob mirror status`.

### 3.1 Who runs it, and with which credentials (MIR-AUD-01, 26, 31)

- The mirror job is defined only on the default branch and runs on
  `schedule`, `workflow_dispatch` and `repository_dispatch`, which
  always use the default branch's workflow file. It is never triggered
  by a push to the ticket branch: a push-triggered job would run the
  workflow file from the ticket branch, which every ledger writer can
  edit. A secret-free nudge workflow on the ticket branch may send a
  `repository_dispatch` ("something changed"); it carries nothing the
  mirror trusts. Scheduled runs also catch tracker edits made when the
  ledger is quiet (model flaw F1).
- Credentials (a dedicated GitHub App's key, the marker keyring) live in
  an environment whose deployment branches are restricted to the
  default branch, never in repository secrets. The job checks that it
  runs from the default branch before requesting the environment.
  `frob mirror init` prints the setup; `doctor` verifies it through the
  API (Error where the API answers, Unresolved otherwise).
- A TICK rule: a `.github/` tree on the ticket branch other than the
  generated nudge workflow (byte-compared) is an Error.
- One writer: the job takes a writer lock (a ref on the ticket branch
  updated by CAS) and keeps a watermark of the last processed ledger
  commit (MIR-AUD-13). The mirror's own ledger commits never trigger
  runs.
- MIR001 is time-based: "no successful run for N hours" (scheduled runs
  are delayed, dropped, and disabled after inactivity), plus the
  per-scope reasons below.

### 3.2 What a run looks at: feed, sweep and budget (MIR-AUD-02, 10, 27, 33; F8)

- **Change feed.** One GraphQL query per 100 issues lists the bot's
  issues updated since the stored cursor, ordered by update time; only
  issues whose update time passed the stored observed value get a
  history read. Ledger-driven work comes from tickets with unpublished
  events. Both sources select work (F1: not only ledger changes).
- **Sweep.** Each run also reconciles the next K issues of a persisted
  round-robin cursor, so every issue is visited within ceil(N/K) runs
  even when the feed misses a change (repository-level renames do not
  bump issue update times). `frob mirror status` states that bound.
- **Budget planner.** At start the run reads the rate-limit headers and
  spends at most a configured share (default half) of what remains, at
  most C creates (default 50) and M mutations (default 300), serially,
  at least one second between mutations. Work classes in strict
  priority: (1) recovery of uncertain creates, (2) ledger-driven
  updates oldest first, (3) creates oldest first, (4) reconcile of
  changed issues, (5) the sweep. Within a class, a run resumes after
  the last completed ticket (round robin), never from a fixed order,
  so no ticket starves (F8). The budget must cover at least one
  ticket's reads plus one write; below that the run reports MIR001
  `budget-too-small` (the model shows starvation otherwise).
- **Errors.** `retry-after` is honoured; with no remaining budget the
  run stops (it never sleeps to the reset) and records the reset time;
  otherwise wait 60 s, doubling, at most three retries, then stop.
  Every GraphQL response's `errors` array is checked (rate limiting is
  reported there with HTTP 200), and partial data is treated as failure
  for that query's scope.
- **Progress.** A stopped run commits its progress (the map is sharded
  per ticket and committed every K operations, MIR-AUD-14) and reports
  MIR001 `rate-limited` with the next window. The next run continues.

### 3.3 Identity: markers, creates and duplicates (MIR-AUD-04, 05, 09, 15, 16, 24; F3-F6; spoofed marker)

- **Marker format** `frob:v1 kid=<id> ulid=<ULID> nonce=<n> mac=<...>`,
  the MAC over (repository node id, ULID, nonce) under key `kid`, from a
  keyring (one signing key, older keys verify-only for a stated period;
  rotation re-marks issues gradually within the budget).
- **A marker counts only in the bot-authored creation revision of the
  issue body** (the first revision, authored by a mirror bot id). The
  model found that a human pasting another ticket's marker into a
  bot-created issue made the mirror adopt it; the author check and the
  MAC alone do not stop a copied string. A marker edited out of or into
  later revisions changes nothing (F4, MIR-AUD-24). A marker under an
  unknown kid on a bot issue is MIR001 `marker-key-unknown`, never a
  recreate.
- **Lookup is read-your-writes.** The mirror finds a ticket's issues by
  listing the bot's issues (by creator, newest first), never through
  search, which lags (F5). The tracker is the identity authority; the
  map file is a cache of it.
- **Create protocol.** Before a create the run derives a nonce and
  records "create started" in the journal. A create whose outcome is
  unknown (timeout, 5xx, crash) makes the ticket create-uncertain: no
  further create for it until recovery has listed the bot's issues back
  to the create's start time and matched the nonce. GitHub's create has
  no idempotency key, so a duplicate can still appear (a timed-out
  create that lands after its retry); the model confirms this cannot be
  prevented, only bounded: at most one extra issue per uncertain create.
- **Duplicates are found every run, not only on first sync** (F6): if
  two bot issues carry valid markers for one ULID, the lowest issue
  number is canonical; the others are closed as duplicates of it, keep
  their markers (so they are never re-adopted), and their history is
  still read so edits made on them are captured (F3: the history cursor
  is taken before the ticket's issues are listed and kept across a
  create).
- **Status codes.** 301 (moved or transferred) updates the cached
  location after verifying the marker; 404 is never read as "deleted"
  (a token that cannot see the issue also gets 404); 410 (deleted)
  marks the ticket unmirrored and reports it. The mirror never
  recreates an issue without a person running `frob mirror recreate
  <ticket>`. A blindness check (the token sees the repository and its
  own recent issues) runs first; if it fails the run stops with MIR001
  `token-blind`.
- **Own writes.** A dedicated App identity (`[mirror] bot_ids`, by
  user id). Before each mutation the run journals (issue, field, value
  digest, run id); a history entry is "own" only if its actor is a bot
  id and its value digest matches a journaled write. Any other bot
  entry is an edit by "unknown automation". Unconfirmed journal entries
  are re-read at the start of the next run.

### 3.4 Reconcile, never block (owner decision; MIR-AUD-03, 06, 11, 20, 25; F2, F7, F9)

- **One owner per field.** Every projected field has exactly one owner
  in `[mirror.fields]` (materialized). In version 1 every field the
  mirror writes is repository-owned; tracker-owned are only what the
  mirror never writes (comments, reactions, labels outside the `frob:`
  namespace, fields listed in `tracker_owned`). Labels and assignees
  are changed with additive and subtractive endpoints, never by
  replacing the whole set, so tracker-owned labels are never deleted
  (MIR-AUD-11).
- **Per issue in a run:** read the current values and the history after
  the cursor; for each repository-owned field changed by someone other
  than the mirror, revert it to the projection and record the change as
  a proposal; never write a tracker-owned field. Values are compared
  after the tracker's own normalization (read back once and stored), so
  the mirror does not rewrite fields the tracker reformats (MIR-AUD-20).
- **The cursor is the history position actually read** (an event id,
  never a time), advanced only after the proposals it covers are
  committed (F2, MIR-AUD-25).
- **What "nothing is lost" means, precisely** (MIR-AUD-03). The value
  present at read time is always captured (read-time capture compares
  it with the last observed value). Intermediate values and authors are
  captured from history while history retains them; GitHub keeps the
  original body plus the latest 99 edits, revision content can be
  deleted by writers, and some changes (repository-level label and
  milestone renames, project fields other than status, deletions) have
  no per-issue history. Those cases are recorded with `fidelity = gap`
  and listed in `frob mirror status`; a repository-level inventory of
  managed labels, milestones and issue types catches renames once,
  not per issue.
- **Revert wars end** (MIR-AUD-06). A field changed again by a
  non-mirror actor within the backoff window is reverted after 1, 2,
  4 ... runs, at most once a day. After three re-applications by the
  same actor or automation the field becomes `contested` for that issue:
  the mirror stops reverting it, keeps one pending proposal with the
  latest value, and lists it in `mirror status` (MIR002, Advisory). A
  new ledger event on the field, or an accept or decline, clears it.
- **Comments.** None per issue by default (they multiply into
  notification storms, MIR-AUD-17); the issue body's managed notice
  says the issue is managed from the repository and where proposals
  go. If comments are enabled, the once-per-day rule checks the issue's
  own comments before posting, not state in the map (F7).

### 3.5 Proposals (MIR-AUD-07, 08, 12, 22; F9)

- Stored by reference: tracker item id, field, actor id, time, a digest
  of the value and a capped, escaped excerpt (200 characters, `origin =
  tracker`). The full value is fetched at accept time; if it is gone,
  the proposal closes as `unavailable`. Abusive text never enters the
  append-only ledger beyond the capped excerpt.
- Keyed by the tracker's event id, so a re-run after a crash never
  records an edit twice and an accepted or declined proposal never
  comes back (F9).
- Append-only with supersede: a later edit by the same actor to the
  same field appends a small event with `supersedes`; the fold shows
  the latest. Caps: one new proposal per (issue, field) per day, P per
  run; proposals expire after `[mirror] proposal_ttl_days` (default 30)
  as `expired`. All proposals of a run are written in one ledger
  commit.
- Identities are mapped by tracker user id, never login (logins can be
  released and claimed).
- `frob ticket proposals accept` inherits the old adopt guards: TTY
  only, never with an agent marker, shows the escaped diff, refuses
  edits by unmapped identities, and never touches scope, acceptance,
  evidence or links.
- New event kinds `proposal`, `proposal-superseded`,
  `proposal-accepted`, `proposal-declined`, `proposal-expired` join
  tickets.md 2a.

### 3.6 Publishing safely (MIR-AUD-18, 19, 21, 23, 28, 30, 32)

- Render limits are checked before any write: body size (65536
  characters), label count and length, sub-issue limits. A ticket that
  cannot be published is isolated (MIR001 for that ticket only); one bad
  ticket never stops the run.
- Mirrored text cannot trigger GitHub side effects: `@` mentions and
  team mentions are neutralised, closing keywords (`fixes #12`) and
  cross-repository references are rendered as plain text, no task-list
  checkboxes are rendered. Closing keywords in code-branch commits that
  close a mirrored issue are treated as a tracker edit (reverted and
  proposed), never fought silently.
- Publication is irreversible (edit history is readable by anyone with
  read access): `[mirror] exclude` and redaction apply before the first
  publish; evidence is published as verdicts and links, never
  transcripts.
- One managed label (`frob:managed`), not one label per ULID. Projects
  fields are written only with an App that has project access, and
  only status is reconciled; other project fields are read-time only.
- Transfer, conversion to a discussion, lock and pin are classified and
  reported, never acted on blindly.

### 3.6a Operational details (closing the re-cut's gaps)

- **Caps never move the cursor past an edit.** When the per-run
  proposal cap or the one-proposal-per-(issue, field)-per-day cap is
  reached, the issue's cursor stops before the first edit not yet
  recorded; the next run (or the next day) re-reads from there. Repeated
  edits of one field on one day are recorded the next day as one
  `proposal-superseded` holding the latest value, with the intermediate
  values counted. The read-time value is always captured, so the cap
  delays authorship, never the latest value.
- **The write journal** lives in the ticket's map shard on the ticket
  branch: each entry is (issue, field, value digest, run id, time). An
  entry stays until a later run confirms it by read-back and for 30
  days after (so history entries can still be attributed), then it is
  pruned.
- **The writer lock** is a file `.mirror/lock` on the ticket branch
  holding (run id, start, expiry), written by CAS; a run that finds an
  unexpired lock of another run exits 0 with MIR001 `locked`; an expired
  lock (default 60 minutes, `[mirror] lock_ttl_minutes`) is taken over
  and the takeover is logged. GitHub's concurrency group is a second,
  independent guard.
- **The mirror's commits never trigger a run** because the mirror job
  is never push-triggered (3.1), and the nudge workflow ignores pushes
  whose author is a mirror bot id. Pushes with the App token do trigger
  workflows on GitHub; GITHUB_TOKEN pushes do not; the nudge's actor
  check covers both.
- **TICK008 ledger-branch-workflow** (Error): a `.github/` tree on the
  ticket branch other than the generated nudge workflow (byte-compared).
  The nudge runs with GITHUB_TOKEN and the least permissions that let it
  send `repository_dispatch`; which permission that is, is UNVERIFIED
  and checked by the verification ticket below.
- **Knobs** (all materialized under `[mirror]`): `behind_hours = 24`
  (MIR001 when no successful run for that long), `budget_share = 0.5`,
  `creates_per_run = 50`, `mutations_per_run = 300`, `sweep_per_run =
  50`, `proposals_per_run = 100`, `proposal_ttl_days = 30`,
  `contested_after = 3`, `commit_every = 25`, `lock_ttl_minutes = 60`.
- **`frob mirror recreate <ticket>`** is a human verb: TTY only, never
  with an agent marker, and it refuses unless the tracker answered 410
  (deleted) for the issue; a 404 is refused with the blindness
  explanation (the token may not see it).
- **Reopened duplicates** are closed again by the next run's duplicate
  scan, with one host-template comment the first time explaining that
  the canonical issue is the lowest-numbered one.
- **Neutralisation form** (3.6), ASCII only: user and team mentions,
  issue and pull request references, cross-repository references and
  closing-keyword phrases in mirrored text are rendered inside code spans
  (`` `@name` ``, `` `fixes #12` ``), where GitHub neither notifies nor
  links nor closes.
- **Verifying the tracker facts.** The audit left 16 GitHub facts
  UNVERIFIED (among them read-your-writes listing, the nudge's
  permission, autolink limits); one ticket verifies each against the
  live API in a sandbox repository before the first live run, and the
  adapter's capabilities record cites the result.

### 3.7 Stated properties and assumptions

Properties (formal statements and TLC results in
docs/design/models/mirror/README.md):

| Property | Holds |
|---|---|
| never writes a tracker-owned field | always |
| the cursor never passes an unrecorded edit (within retained history; gaps reported) | always |
| proposals never change the tracker; the mirror writes only ledger values | always |
| the map never points a ticket at another ticket's issue | always |
| at most one comment per issue per day (when enabled) | always |
| tracker writes per run within the budget | always |
| a closed proposal is never reopened | always |
| a run on a converged state changes nothing | always |
| at most one duplicate issue per uncertain create, closed by the next run | always (zero duplicates is impossible on GitHub) |
| convergence: every repository-owned field eventually equals the ledger | when human edits and faults are finite, runs keep happening, and the budget covers one ticket's reads plus one write |
| under edits that never stop: each issue equals the ledger infinitely often, every edit recorded, no ticket starved | with round-robin order and that minimum budget; contested fields bound the cost |

Assumptions about the tracker, each with a runtime check that stops the
affected scope and reports MIR001 with the reason, never silent
wrongness (audit section 4, TA1-TA15): the run is the legitimate single
writer; the token sees the right repository with the right rights;
responses mean what their status says; rate-limit headers are present;
the issue is where it was; author plus creation-revision marker identify
the issue; history is complete for the window or the gap is detected;
writes stick when read back; the projection fits the limits; managed
labels and types exist; the ledger only moves forward; identities are
keyed by user id; every bot history entry matches a journaled write;
other actors eventually stop editing a field or it becomes contested;
cursors are event ids. The issue lookup's read-your-writes behaviour on
GitHub's list endpoint is UNVERIFIED and is the first thing the adapter
tests against the live API.

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
2. Tracker edits never block: one owner per field, repository-owned
   fields reverted deterministically, edits captured as proposals within
   the stated bounds (section 3.4). Replaces the earlier skip-and-report.

3. The code repository's pointer is a generated region of README.md,
   not a `TICKETS.md` (navigation.md 3.2).
