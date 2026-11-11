# Tickets: storage, model, evidence, landing, navigation and the tracker mirror

Status: current
Owner: frob
Decisions: D7, D8, D14, D23, D24, D26, D33, D46, D47, D48, D79, D81, D92, D99
Audience: contributor

The ticket ledger end to end: how it is stored and identified (part 2), the data model (3), Jira mapping,
evidence, landing and verbs (4 to 8), where ticket files live and how the reindex moves them (11), and the
one-way tracker mirror with its audited protocol (12 to 15). Merged from the former tickets.md, mirror.md and
the ticket-path parts of shared/documentation.md (the generated set, profiles and tour stay in shared/documentation.md). The
TLA+ model of the mirror protocol stays under docs/design/mirror/.

Provenance: tickets: written under T-0001 (a v1-format id that migrates with an alias). Inputs: notes/v1/tickets.md
(data model, 25 incident classes, Jira gap list), notes/research/rust-ecosystem.md section 3,
notes/v1/ops-and-integrations.md (telemetry), notes/research/jira.md and notes/v1/agent-usage.md (sections 4 and 5).
Navigation: ACCEPTED (D81, owner decisions 2026-10-04 on the documentation survey, ticket ~AMBGYQ4; evidence
notes/research/docs-survey.md, 1254 repositories, ten exemplars). Mirror: ACCEPTED with changes (D79). Owner
decisions 2026-10-04: GitHub Issues first behind a platform-agnostic producer (section 12.1); tracker edits never
block anything (section 13.4). The protocol (section 13) was rewritten from an adversarial audit and a TLA+ model
(ticket ~HV53M66). Earlier owner decisions: the ledger lives on a dedicated orphan branch, approachable to
newcomers; the first tracker integration is a one-way mirror (repository to tracker); conversations are not
mirrored back; material tracker decisions may flow back later, with field ownership instead of timestamps.

The goal of the navigation parts is one sentence from the owner: it must be the least confusing thing possible
for someone who has never seen the repository.

## 1. Thesis

v1's 52k lines of ticket code are mostly defenses against one cause:
branch-local ledgers with many concurrent writers. Four patches exist
for that cause (display overlay, cross-worktree lease side channel,
mirror commits, land-time splice) and 109 of 300 main commits were
mirror churn. v2 picks ONE writer story and builds Jira-class features
on top of it.

## 2. Storage and identity

### 2.1 Layout and the ticket branch

- The ledger is a normal orphan branch, default name `frob-tickets` (materialized knob `[tickets] branch`), so
  every clone fetches it, the hosting UI lists it and it can be browsed on the web. Hidden custom refs were
  rejected: clones would silently lack the ledger (D79).
- Layout for humans, identity for machines: `README.md` (generated), `<top-epic-slug>/<ticket-slug>.md` for
  tickets (the slug follows the title; the file moves only in a verifiable reindex commit when its top epic or
  title changes, section 11) and `.events/<ULID>/` for event logs. The ULID stays canonical in each file's
  frontmatter; frob resolves ids through its index, never through paths (section 2.3).
- `tickets/<id>/` (`ticket.md` as TOML frontmatter plus markdown body, `events/<ulid>.toml` as append-only state
  changes, field changes, comments, evidence and reviews, and `attachments/`) is the legacy milestone-1 machine
  layout; this repository has migrated off it and no longer has a `tickets/` directory. Everything else in this
  section (ULID identity, handles, aliases, events) holds for both layouts. Terminal tickets are not moved;
  `archive` is a view.
- frob writes the branch through gob-git commit_paths with CAS (D23), so the code checkout is never touched.
  Branch protection on the hosting side should forbid force pushes.
- The code repository carries one short pointer, a generated region of README.md (shared/documentation.md 3.2), saying
  where tickets live, the three commands to use, and the tracker link.
- Selecting the layout (~H3WVSYM): `[tickets] ref_mode = "orphan"` stores the ledger on
  `refs/heads/<[tickets] branch>` in the ticket-branch layout, while `[tickets] ref` stays the code base branch
  that `work` branches from and `land` advances. Milestone and cycle objects sit at `_milestones/<ULID>/` and
  `_cycles/<ULID>/` at the branch root. `trunk` and `branch` keep the legacy `tickets/<id>/` layout. The setup is
  `docs/guides/ticket-branch.md`.
- Inert text (D91, ~JTV288R): everything under the ledger directory is data written through the ledger write
  path; text in it, such as a `frob:waive` quoted from a v1 ticket, is never a live directive. Directive and
  comment scanning skips ledger files (one `FileRole` classification in gob-walk, docs/design/shared/code-model.md section 4); the
  ledger rules (TICK, PM, privacy) still read them.

### 2.2 Ids, handles and aliases

- Id: a ULID minted at creation. No counters, no draft ids, no promote,
  no renumber. The full 26-char ULID is the only persisted form:
  directives, links, commit trailers, changelog fragments and directory
  names all carry it. The human handle is the unique suffix of the
  ULID's random part (the last 16 characters), shown as `~xxxxxxx` with
  a minimum of 7 characters (`[tickets] handle_min_len`; the minimum
  governs display, and input accepts any unique suffix), lengthened
  only when two tickets collide, and accepted by every verb
  (`frob ticket show ~6C0D1E2`). A handle is never persisted: a fixer
  expands handles to full ids on write, and a TICK rule flags an
  abbreviated id in tracked text. The time prefix is not used as a
  handle because every ULID created in the same ~17 minutes shares it.
  A repo may set `[tickets] prefix = "FRB"`, which puts the prefix
  before the handle in CLI output only (`FRB-~6C0D1E2`); it is accepted
  on input and never persisted, so directives and commit messages carry
  only the full ULID. ULIDs sort by creation time, which is what humans
  used counters for. `aliases` hold v1 ids (`frob:T-0042`,
  migration.md); `ticket new --alias` sets them, and an alias resolves
  like a handle (an ambiguous one is `E-TICKET-AMBIGUOUS`).
- Why not counters assigned at land (the ecosystem note's suggestion):
  it keeps two names per ticket alive and brings back promote and
  rewrite-every-reference. Time-ordered ids are enough; the handle
  gives humans the short name.
- Events, not mining: every transition and field change is an event
  file with `at`, `actor`, `from`, `to`, `reason`. Cycle time, flow and
  velocity are computed from events, not git archaeology. Comments are
  events of kind `comment`. See section 2.4 for the full model.

### 2.3 References: ids, not paths

A ticket file lives on the ticket branch at a path computed from the ticket's current state, and that path
changes when the ticket moves to another epic (section 11). A path is therefore never a reference. Only the
canonical id is.

| Where | Allowed reference | Enforced by |
|---|---|---|
| hand-written text in the code repository (docs, code comments, commit messages, directives) | full ULID; `~handle` only in chat and CLI output (section 2.2) | TICK006 (below) and the existing abbreviated-id fixer |
| ticket bodies, comments and events on the ticket branch | full ULID or `~handle` (expanded to the ULID on write) | TICK006 |
| generated pages (README, indexes, epic pages) | relative paths, because they are regenerated whenever a path changes | GEN001 |
| the tracker mirror | the issue projection carries the ULID; links point to the issue or to `indexes/by-id/` | section 12.1 |
| CLI arguments | ULID, `~handle` or alias | a path argument is refused (`E-TICKET-PATH`) with the id it names: `that file is ~6C0D1E2; pass the id` |

- **TICK006 ledger-path-reference** (Error, P+, machine fix): tracked
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

### 2.4 Events

An event is one small TOML file, `tickets/<id>/events/<ulid>.toml`,
written by the verb that caused it and never edited afterwards:

```toml
kind = "transition"          # one of the kinds in the table below
at = 2026-10-02T14:03:11Z
actor = "logan"              # git identity, or FROB_AGENT: a label for the audit trail, not authorization
from = "ready"
to = "in-progress"
reason = "started via frob work"
```

Why files, not a log: each event has its own path, so two worktrees
acting on one ticket merge with no conflict; a PR shows exactly which
events it adds; deleting history is visible as a deletion. Why not git
mining: v1 derived state-change times from commit dates at day
granularity and got them wrong whenever a mirror or splice commit moved
the change. Ordering: the ULID in the file name orders events by
creation time, but monotonicity holds only inside one generator, so the
fold orders by (ULID time, `at`, file name) and treats ties between
processes as concurrent; a `field` event carries the previous value, so
a conflicting concurrent pair is reported, never silently picked.
Integrity means the frontmatter equals the fold of the events:
`frob ticket doctor` re-folds and compares (not a digest comparison, so
a merge of concurrent changes is not corruption) and `ticket reconcile`
rewrites the frontmatter from the fold. The SQLite index folds events
into per-ticket timelines, cycle times, velocity, and flow metrics in
one pass; `frob ticket show --events` prints the timeline. Counts stay
small: a busy ticket has tens of events, each a few hundred bytes.

Every kind that any file refers to is in this table. frob-ledger's
`EventBody` interprets `create`, `field`, `transition`, `comment`,
`link`, `exception`, `evidence`, `evidence-bypass` and `land`; every
`rev`-1 file carries a `rev` key, the revision of the event file format
(not of the ticket), and a kind a reader does not know folds to no
change. Every producer writes through one API, `Ledger::append(ticket,
EventBody)`, which writes the event file, re-folds the ticket file and
commits on the ledger ref (CAS) (`Ledger::append_many` commits a batch of events in one commit); no crate writes event files directly
(~CFM8QB0).

The fold binds an acceptance criterion (`bound = true`) only from
measured, passing evidence: a record whose status is `measured` and
whose verdict is not a failure, whose `accepts` maps to the criterion
through the `moved` maps of later acceptance edits (a removed criterion
binds nothing). For each (provider, reference, criterion) the latest
record decides, so a failure or an unmeasured record after a pass
unbinds, and a pass after a failure binds; a criterion is bound when
any (provider, reference) pair's latest record for it passes.

| Kind | Subject | Required fields | Producer verb | Consumers |
|---|---|---|---|---|
| `create` | ticket | the initial field values (title, type, body, scope, links, idempotency key, aliases) | new | fold (the birth event; a ticket whose first event is not `create` fails doctor) |
| `transition` | ticket | from, to, reason | start, requeue, review, close, drop, reopen, land, triage | cycle time, velocity, flow, close guard |
| `field` | ticket | field, old, new; reason when the field is `flavour` (PM028) or a driver is resolved (PM021) | update, body | fold, doctor, PM rules |
| `comment` | ticket | subtype (note, decision, question, answer, evidence), body | comment | brief, blocked-on-question view |
| `link` | ticket | op (add, remove), link type, target | link, unlink | graph, doctor |
| `evidence` | ticket | evidence id, verdict, measured value, commit, store URI or inline text | evidence | close guard, done-report |
| `evidence-bypass` | ticket | reason | `ticket close --no-evidence --reason` | audit, doctor |
| `changelog-exempt` | ticket | reason | `ticket close` and `land` with `--no-changelog --reason` | audit, REL003, show, brief, release status (folds to no change, so old binaries read it as an uninterpreted kind) |
| `land-exempt` | ticket | reason | `ticket close --outcome done --no-land --reason` | audit, doctor (folds to no change, so old binaries read it as an uninterpreted kind) |
| `scrub` | ticket | reason, files rewritten, digests recomputed (file, old, new) | `ticket doctor --fix` (the `TICK004` and `TICK005` repair) | audit only; the fold ignores it, `updated` included |
| `lease` | ticket | op (evict, restore; later take, renew, release, steal), holder, observed oid, parked ref, tip, idle, window, reason | `work --next` eviction, `claim restore` | audit only; the fold ignores it, `updated` included |
| `review` | ticket or exception | subject, verdict, reviewer | review, `exceptions` review of an accept | EXC012, cycle report |
| `exception` | ticket | kind (accept, defer, hotfix), rule, site | check --fix, land --hotfix | ticket page, close guard |
| `cycle` | ticket | cycle id, op (assign, carried, over-commit), reason (required for over-commit) | cycle assign, cycle close | velocity, forecasts, cycle report |
| `attempt` | ticket | outcome (failed, abandoned), reason | requeue --failed, a failed land | brief, doctor |
| `triage` | ticket | action (accept, decline, snooze, duplicate), until (snooze only), reason (when given) | ticket triage | inbox; the fold ignores it (the `transition` and `link` events written beside it carry the state change) |
| `add-alias` | ticket | alias (a tracker key such as `PROJ-123`) | `mirror alias` | the fold appends it to `aliases` once, so `ticket show PROJ-123` resolves |
| `proposal` | ticket | tracker event id, item, field, actor id, time, value digest, excerpt (capped), origin (`tracker`) | mirror run | proposals list, `proposals accept`; the ticket fold ignores it (section 13.5) |
| `proposal-superseded` | ticket | the `proposal` fields plus `supersedes` (the replaced tracker event id) | mirror run | proposals list; the latest pending proposal per (item, field) wins |
| `proposal-accepted` | ticket | tracker event id, reason (when given) | `ticket proposals accept` | proposals list; closed for good, a re-recorded tracker event id stays closed |
| `proposal-declined` | ticket | tracker event id, reason (when given) | `ticket proposals decline` | proposals list; closed for good |
| `proposal-expired` | ticket | tracker event id, reason (when given) | mirror run after `proposal_ttl_days` | proposals list; closed for good |
| `cost` | ticket | tokens in, out, cache, cost, wall seconds | harness hook, land | stats, forecasts |

The class of service is the field `class` (and `due`): `create` and
`field` events carry it, an event or file without it folds to
`standard`, and `standard` is never written, so a ledger that does not
use classes is byte-identical to one written before them. A binary older
than the field rejects the unknown key in a ticket or `create` event that
carries a non-standard class (their schemas deny unknown keys), so set a
class only once every writer runs a binary that knows it. The SQLite index
format moved to 2 (a cache; it is rebuilt on first open).

Acceptance edits are `field` events on `acceptance` written by `frob
ticket update --add-acceptance TEXT`, `--remove-acceptance N` and
`--clear-acceptance` (one event per command; `--set acceptance=` is
refused because criteria hold commas). `old` and `new` are the lists of
criterion texts and a `moved` array maps each old criterion, by position,
to its 1-based position in `new` (0 when removed). Evidence events are
immutable and record `accepts` as positions in the list as it stood when
they were written, so indices are not rewritten and do not shift in the
record: a reader resolves a record's current criteria by composing the
`moved` maps of every later acceptance event (`frob_ledger::fold::
remap_accepts`, `Ledger::criteria_now`). A removal therefore never leaves
evidence silently pointing at a different criterion, and `ticket update`
reports (`lost_evidence` in the envelope, a warning in text) each record
that loses a criterion, so it can be re-offered with `evidence add
--accepts N`.

Events with no ticket live under `events/<ulid>.toml` at the repo root,
with the same envelope plus a `subject` such as `exception:<id>` or
`component:<name>`. Their kinds are `budget-raise` (subject component:
knob, old, new, reason, actor; producer `exceptions budget`; consumer
the EXC budget rules), `audit` (subject exception: verdict STILL-NEEDED,
OBSOLETE or COP-OUT; producer `exceptions audit`) and `review` as above.
Acks are not events: they live in the ack log of the product lock file.

- Merge: disjoint ids are disjoint paths; events are append-only files
  so concurrent work on one ticket merges with no conflict on events.
  The only conflict surface is `ticket.md` frontmatter, which is a
  cache of the events. The merge driver (`frob merge-driver`, a hidden
  verb that git invokes) takes the union of the event files found on
  disk and in every merge head, and re-folds the frontmatter; it never
  picks a last writer. `frob init`
  and `frob doctor --fix` install the `.gitattributes` line
  (`tickets/**/ticket.md merge=frob-ledger`, plus `tickets/_milestones/*/milestone.md` and `tickets/_cycles/*/cycle.md`, which `frob merge-driver` dispatches to the pm resolver) and `git config
  merge.frob-ledger.driver`, and `doctor` verifies both because git
  config is not cloned. A hosting provider's merge button never runs
  the driver, so a TICK rule re-folds every ticket in CI and fails when
  a frontmatter disagrees with its events. No custom splice.
- Index: SQLite under `.frob/tickets.sqlite` of each worktree, rebuilt
  from the ledger files keyed by content hash and the id of the tickets
  subtree (not the whole tree, so unrelated commits do not invalidate it); every query verb
  reads the index; thousands of tickets load in tens of milliseconds.
  v1's `doable` took over 120s at 1,245 tickets.
- Writer story: ledger commits advance the configured ledger ref
  (`[tickets] ref`, default the trunk branch). A worktree verb resolves
  the repository from the git common dir (never from cwd), writes the
  ticket files, and builds the commit tree from the ledger ref's current
  tree plus the changed ticket directory, never from any index, so a
  user's staged changes can never enter a ledger commit. The ref is
  updated by compare-and-swap with up to `[git] cas_retries`
  retries (re-read the tip, rebuild the tree, retry); exhausting them
  is exit 3 retryable. When some checkout has the ledger ref checked
  out, frob updates that checkout's index and worktree for the ledger paths
  only, and refuses with a remedy if those paths have local edits.
  `[tickets] ref_mode = "branch"` puts ledger commits on the current
  branch instead, for protected-trunk and fork flows (`ref_mode =
  "trunk"`, the default, commits to `[tickets] ref`, default
  `refs/heads/main`). A reconcile commit is made when concurrent event
  writes leave the frontmatter behind the fold. No mirror step, no
  overlay. In the default mode a land carries no ledger diff because the
  ledger was never branch-local.
  In trunk mode with a feature branch checked out, every ticket verb
  adds a warning to its envelope naming the ref it reads and commits to
  and stating that the working tree is not the ledger (F-504, F-562).
  `land --dry-run` treats a base that moved only by commits under the
  ledger directory as merged, so trunk-mode ticket commits do not make
  it skip the check.

### 2.5 CI, forks and offline clones

CI is a fresh clone and sees only pushed commits. Ledger commits on the
trunk must therefore be pushed before or with any PR whose code
references the ticket (push is the `frob land --push` flag, which pushes the base
branch during landing). Nothing lists unpushed
ledger commits: `frob ticket doctor` checks folds, event order, ids and
conflicts only, so push the trunk by hand when `--push` was not used. The TICK
rule flags a ticket referenced in code or a trailer that is absent from
the base ref (`origin/<trunk>`), so a dangling reference fails locally
and in CI. Where trunk is branch-protected or the work is a fork,
`ref_mode = "branch"` keeps the ticket commits in the PR itself. An offline
clone keeps working: ledger commits queue locally and the CAS retry
rule applies when the remote catches up.

## 3. Data model

Fields are declared once in Rust with `#[derive(TicketSchema)]` which
generates the frontmatter schema, the `ticket update` validation, the
`--json` schema, and the docs table. Unknown keys are an error (not a
v1-style warn) unless declared under `[tickets.custom_fields]`.

| Group | Fields |
|---|---|
| identity | id, aliases (v1 ids namespaced by source repo, migration.md), title, type, created, reporter, assignee (optional), owner_team (optional) |
| classification | priority (low, medium, high or critical), class of service (expedite, fixed-date, standard or intangible; default standard), component (registry, shared/charter.md), labels, area |
| hierarchy | parent, children (derived), links (typed, section 3) |
| planning | cycle (object; membership is an event), milestone (a release object, never a ticket type), points, due (RFC 3339; orders fixed-date tickets), rank (fractional, LexoRank-style) |
| state | status (category plus status name, section 3), outcome (done, fixed, wont-fix, duplicate, invalid), blocked (derived from open blockers) |
| scope | scope (globs), scope_mode (exclusive, append, none), scope_ack reason, evidence_scope |
| acceptance | criteria list with bound evidence ids |
| evidence | evidence records (runnable id, kind, last verdict, verified_at, at commit) |
| agent | worktree, branch, lease (derived), tokens (in, out, cache), cost |
| audit | events (external files) |
| custom | per-repo declared typed fields (string, int, enum, date, symref, ticket ref) |

Types replace v1's kind x tier conflation: `epic | story | task | bug |
security | docs | invariant | incident | chore | custom`. A milestone is
a release object (pm-and-releases.md 11), not a ticket type. A story has
`flavour = user_story | quality_objective` and carries the structured
fields that pm-and-releases.md requires (sections 2 and 3 there). Each type
declares its evidence policy (bug needs a repro that fails at parent,
docs accepts command evidence), its land commit type, and whether it can
be worked directly (epics cannot, and `doable` excludes them).

**Doable order.** `ticket doable`, the board NEXT list and `cycle plan`'s
candidate order are one function, `frob_ledger::ops::doable_cmp`, so they
cannot diverge. Sort keys, in order: class lane (`expedite` first, then
`fixed-date` by `due`, undated last, then `standard` and `intangible`
together); priority (`critical`, `high`, `medium`, `low`); `rank` when set
(reserved: tickets carry no stored rank yet, so the key is skipped); age
(oldest `created` first); then the id as the final tie-break.

One canonical table, declared once with inverses and topology
constraints; every other file uses these spellings.

| Link | Inverse | Topology |
|---|---|---|
| `blocks` | `blocked-by` | acyclic |
| `parent` | `child` | single parent, acyclic |
| `relates` | `relates` | symmetric, no constraint |
| `duplicates` | `duplicated-by` | one-way; target is not itself a duplicate; source takes outcome `duplicate` |
| `causes` | `caused-by` | acyclic |
| `splits` | `split-from` | single origin |
| `discovered-from` | `spawned` | provenance (agents spawn follow-ups constantly); acyclic; `spawned` is a link kind in its own right in code |
| `enabler-for` | `enabled-by` | target is a story or quality objective |
| `supersedes` | `superseded-by` | acyclic |
| `implements` | none stored; the first-class frontmatter field `implements: [design:<anchor>]` (set by `ticket new --implements` and `frob plan --from-design`) is validated against `grimble graph --json` on create, an unknown anchor is refused, and the overlay (unplanned, planned, in-progress, done, with the graph test verdict) is computed onto the anchor, never stored | target is an invariant or a grimble entity; a grimble entity is validated only through `grimble --json`, and is Unresolved when grimble is absent |
| `fixes` | none stored | target is a finding fingerprint |

Cross-repo links use a `repo:` prefix and are resolved through the fleet
manifest (Milestone 2 or later (D36)). `blocked` is derived: a ticket is
blocked while any `blocked-by` target is non-terminal.

Statuses are categories plus close guards; there is no transition
graph. Categories are fixed: `triage`, `todo`, `in-progress`, `done`,
and `blocked`, which is derived from open `blocked-by` links and is
never set. Display names are free within a category: `triage {triage}`,
`todo {backlog, ready}`, `in-progress {in-progress, in-review}`, `done
{done, dropped}`; every terminal status carries an `outcome`. There is
no `landing` status: land is one synchronous transaction that moves
`in-review` to `done` at its end.

Guards are named Rust predicates (`has_evidence`, `no_open_blockers`,
`children_terminal`, `lease_free`) selected in `[tickets.guards]` and
evaluated when a ticket would reach `done`. `close` and `land` evaluate
the same guard set: a ticket whose scope changed files reaches `done`
only through `land`, and `close` is the path for tickets with no
landing (outcome wont-fix, duplicate or invalid, or
evidence-only work). A repo can choose the guard set; it cannot remove
the integrity guards on `done`. Post-actions (`release_lease`,
`record_land`) are fixed behaviour. `fail` is not a state: it is an
`attempt` event plus a `requeue` back to `ready`.

Size a ticket when you create it (`frob ticket new --points N`, or `frob ticket update --points N`
later): PM009 warns on every ready, non-epic ticket without points, and an unsized ready queue cannot
be planned into a cycle. Epics are not sized; their children are.

- Scope is a write lease taken at `start`, stored in
  `<common_dir>/frob/leases/<id>.toml` (single clone: shared by its worktrees,
  invisible to other clones and machines; cross-clone safety is the
  ledger CAS plus the SCOPE rule at land). The holder is the actor plus
  the worktree path; an agent harness sets `FROB_AGENT` so parallel
  agents are distinct holders. `work` and `work --here` are idempotent only
  for the same holder; any other caller gets exit 3 `E-LEASE-HELD`
  naming the holder.
- Acquisition is atomic: read all leases, compute overlap, write the
  new lease, all under one lock file (`<common_dir>/frob/leases.lock`,
  an flock) in the git common dir; `--steal` takes the same lock and is
  allowed only for the same ticket (it never takes another ticket's
  lease), recording the previous holder in the lease history.
- Waiting is fair. `frob work TICKET --wait SECS` enqueues a waiter
  record (ticket, holder, scope, enqueued-at, heartbeat) in
  `<common_dir>/frob/waiters/<id>.toml`, written under the same lock as
  acquisition, then blocks inside the process (sleep with capped
  backoff, re-check under the lock, heartbeat each pass) until its whole
  scope is free or SECS pass; callers never poll. While a waiter exists,
  a new acquisition whose scope overlaps the waiter's is refused with
  `E-LEASE-QUEUED` naming the waiter and its age, so the waiter gets the
  paths as soon as the holders release; acquisitions overlapping no
  waiter proceed, and overlapping waiters are served FIFO by enqueue
  time (a waiter only yields to earlier waiters, and waiters hold
  nothing, so two waiters cannot deadlock). A waiter whose heartbeat is
  older than `[lease] waiter_ttl_secs` (default 60) is reaped, so a
  crashed waiter never blocks others. `lease list` and
  `ticket contention` report each waiter with its age and blockers
  (overlapping live leases and earlier waiters).
<!-- frob:ticket 01M41ZRNYEWRY4V2MXT3WMXBBJ -->
- TTL is the knob `[lease] ttl_secs` (default 7200); the lock wait is
  `[lease] lock_timeout_ms` (default 5000), and append-shared files are
  exempt from overlap through `[lease] shared_files`, which when unset
  defaults to the well-known generated lockfiles in any directory (patterns `**/<name>`: `Cargo.lock`, `uv.lock`,
  `poetry.lock`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`,
  `go.sum`, `Gemfile.lock`, `composer.lock`, `flake.lock`); an explicit
  value, including `[]`, replaces that default, and an `E-LEASE-HELD` whose
  overlap is only lockfiles names the key in its remedy. Generated
  outputs are exempt the same way through `[lease] generated_files`
  (default `docs/reference/**` and `docs/schemas/**`, the `gen all`
  outputs; an explicit value, including `[]`, replaces it), so a broad
  `docs/**` lease does not block a ticket that regenerates them.
  <!-- frob:ticket 01M4GPWWWZFCHYMKYNKB3S3XGJ -->
  At land, a base
  merge whose conflicts are all shared lockfiles takes the base side and
  regenerates `Cargo.lock` with `cargo metadata --offline` (it keeps locked
  versions, unlike `cargo update --workspace`), committing the result in
  the merge commit; any other lockfile refuses with `E-LAND-LOCKFILE`;
  a conflict confined to lockfiles and `generated_files` takes the base
  side of the generated paths, re-runs `cargo dev gen all` on the merged
  tree and commits what it wrote (a failing generator refuses with
  `E-LAND-GENERATED`; in the land train the member is skipped with that
  reason);
  any other conflicting base merge (including one in `frob.toml`, which
  is never read while conflicted) is aborted so the worktree is exactly as
  before and refused with `E-LAND-CONFLICT` naming the conflicted paths,
  the remedy being to merge the base on the branch, resolve, commit, then
  land again
  (a clean base merge is then checked for dropped hunks: every line the
  ticket's own non-merge commits added, that the pre-merge tree held and the
  base does not carry, must still be in the merged tree, else the land
  refuses with `E-LAND-HUNKS-DROPPED` naming the commit and file and a
  `cherry-pick -n` remedy; this catches a stacked successor whose base
  squash-landed and whose adjacent hunks the merge resolved away)
  (every verb that opens the lease store passes the same config; the old
  `[tickets] registry_files` alias is gone). A ticket's own changelog
  fragment `changelog.d/<its ULID>.<type>.md` needs no lease: it is
  always in scope for SCOPE001 and never contends for overlap, while a
  requested glob that would cover other tickets' fragments
  (`changelog.d/**`, `changelog.d/*`) is refused at `lease widen` with
  `E-LEASE-FRAGMENT-GLOB`; such a glob already recorded in a ticket's
  scope is kept but ignored by overlap and SCOPE001. The heartbeat is renewed by any frob verb run from that
  worktree that proves activity (`ticket evidence add` today; the rest are
  tracked) and, when it exists, by the daemon; only a live lease whose holder's
  worktree is the caller's is renewed, so a stolen lease is never extended by
  the old holder. `land` renews a lease that expired when no other holder has
  taken the ticket or an overlapping scope since, and refuses
  `E-LAND-NOT-LEASED` otherwise, so a 40-minute build
  with no frob call stays inside the TTL. The renewed lease is for the
  ticket's own worktree (the one on its `ticket/<handle>` branch, also when
  `land` runs from the primary root), never for the caller's. `frob work`
  run from that worktree on an in-progress ticket with no live lease
  re-leases it in place on the same terms, with no requeue; a stale lease can be taken
  with `--steal` and a reason. Leases release automatically on every
  terminal transition and on `requeue`.
- Overlap is glob intersection OR resolved-set intersection (in code, a
  conservative intersection test over the glob text, with the resolved
  file set as a backstop; for two wildcard globs the text test is
  segment-wise over the `/`-separated segments, so `crates/*/Cargo.toml`
  and `crates/frob-evidence/tests/**` are disjoint while
  `crates/*/src/**` and `crates/frob-*/src/lib.rs` overlap, and a glob
  with a character class, brace or escape is undecidable and always
  overlaps): two
  tickets scoped to `src/newmod/**` overlap even though no file exists
  yet (v1's glob-overlap proof is kept), and a glob that is disjoint
  from another's text but resolves to a shared file also overlaps.
  `doable` excludes overlaps; `wave --agents N` partitions;
  `contention` names the hot files. The per-holder WIP limit is
  `[pm.wip] in_progress_per_identity` (the former `[lease] wip_per_holder`
  was removed so there is one knob), and `work` and `start` also refuse
  with `E-WIP-REPO` past the repository limit `[pm.wip] in_progress`,
  naming every holder; expired leases do not count and are reported as
  stale. An `expedite` ticket (class of service) is the one exception: it
  skips the repository limit while fewer than `[pm.classes] expedite_max`
  (default 1) expedite tickets hold a live lease, and past that it is
  refused with `E-WIP-EXPEDITE` (exit 3); an `expedite_max` of 0 closes the
  lane. Standard tickets still count every live holder, expedite included.
  The repository count runs inside the lease-store lock together with the
  lease write (`acquire_admitting`), counting live leases, so two concurrent
  `work` calls cannot both take the last slot.
- Zero-match scope warning (~PVJ9SQM). A scope entry that matches no file
  tracked at `HEAD` grants a lease over nothing and, matching nothing,
  reports no overlap, which reads as "cleanly disjoint". `ticket new`,
  `ticket update --add-scope`, `lease widen` and `work`/`start` therefore
  warn, naming the glob and, when one exists, the near tracked path (same
  file name elsewhere, or a single closest name one typo away in the same
  directory; with no near candidate the warning is plain, never a guess).
  It is a warning, not a refusal: the denominator is the tracked tree, so a
  repository with no tracked files (an empty fixture, a fresh `git init`) is
  never judged. A ticket whose job is to create files declares them with the
  label `creates:<glob>` (flags `--new-scope` on `ticket new`,
  `--add-new-scope` on `ticket update`, `--new-glob` on `lease widen`); the
  label is ledger data, so `work` stays quiet on later calls, and the entry is
  an ordinary scope glob everywhere else (lease, overlap, SCOPE001).
- Flags of `frob lease widen <ticket>` (from `frob lease widen --help`):
  `--glob <TEXT>` adds a scope glob to the ticket first (repeatable); `--new-glob <TEXT>` is the
  same for files the ticket will create, adding a `creates:` label that silences the zero-match
  warning (repeatable); `--from-diff` also adds every file the branch diff touches outside the
  scope that no other live lease holds; `--base <REF>` is the ref the `--from-diff` diff is taken
  against (default the lease's pinned base, else `[check] base`); `--wait <SECS>` waits up to SECS
  seconds, reporting the holder, when an addition overlaps another ticket's lease (default 0 fails
  at once); `--schema` prints the JSON schema of the verb's data and exits. Shared flags:
  `--format <auto|json|text|md>`, `--json`, `--text`, `-q/--quiet`, `-v/--verbose`,
  `--color <auto|always|never>`, `--cwd <DIR>`.
- Absorbing the diff (~BVVPJB4). `lease widen --from-diff [--base REF]`
  and `check --ticket REF --widen` grow the ticket scope (and the held
  lease) to every file the branch diff touches outside the scope that no
  other live lease holds. Each absorbed file becomes a literal glob
  (wildcard characters in the name are bracket-escaped) added through the
  normal `scope` ledger event, lease first, so a refusal leaves both
  untouched. A file another live lease covers is never absorbed: `lease
  widen` warns naming that ticket and `check --widen` logs it. Shared files,
  the ticket's own changelog fragment and ledger paths are skipped; scope
  entries stored comma-joined still count per part. Idempotent: a second run
  finds nothing outside the scope and records no event.
- Waiting for an overlapping lease (~1K18GCM). `ticket update --add-scope`
  and `lease widen` fail at once with `E-LEASE-HELD` when the widened scope
  overlaps another ticket's live lease. `--wait SECS` retries the rescope
  (every 250 ms, each try under the lease lock) for at most SECS seconds,
  printing the blocking holder on stderr when the wait starts and at most
  every 10 s after, and succeeds when the holder releases or its lease
  expires. On expiry the first `E-LEASE-HELD` is returned and neither the
  ticket nor the lease changed; `--wait 0` (the default) never waits. Only
  an overlap with another ticket is waited on; other refusals return at once.
- Worktree garbage collection (~BZXZK29). A worktree outlives its ticket
  unless something removes it, and each one carries its own `target/`
  (15 to 20 GB), so `frob work` and `frob land` run a throttled pass that
  removes finished worktrees (docs/design/shared/architecture.md section 3, "Garbage
  collection"). A linked worktree is a candidate only when it lies, by path
  components, under the directory `[worktree] dir` names, is on branch
  `ticket/<handle>`, holds no live lease, is not the current directory, and
  its ticket is in the ledger. A candidate with uncommitted changes
  (`.frob/` excluded) is kept and reported, whatever its ticket's state.
  For a closed ticket anything else is removable, and the branch is deleted
  when it is merged into the base. For a ticket that is still open (an
  expired lease, nothing unsaved) the worktree goes only when its branch tip
  is in the base or on a remote; a branch with unpushed commits is kept and
  reported, and the open ticket always keeps its branch, so a later `frob work`
  re-attaches it. Removal is plain `git worktree remove` without `--force`,
  so git's own refusal is a second guard.
- Edits outside any symbol (imports, module headers) belong to the
  file-level scope: a symbol-level entry claims only symbol bodies, so
  such edits need a file-level entry or conflict with any symbol-level
  lease on that file.
- Milestone 1 ships file-glob leases only.
- New: `scope_mode = append` for registry-style files where concurrent
  tickets only add lines (the SCOPE001 complaint from crunk); the land
  verifies additive-only diffs for append-mode files. Milestone 2 or
  later (D36).
- New: symbol-level scope entries (`src/x.rs::Parser.*`) so two tickets
  can share a file; overlap is then per symbol via the code graph.
  Milestone 2 or later (D36).
- Mega-glob refusal stays (not built in milestone 1; Milestone 2 or later (D36)), with the threshold in `[tickets]
  mega_glob_files`, and the ack is one flag with a reason.

## 4. Jira mapping and pinch points

Source: notes/research/jira.md (data model, 22 pinch points with evidence, 27
competitor concepts). Rule: keep every Jira concept a user would look
for, change the mechanism where Jira's mechanism is the pinch.

Milestone 1 (D36) keeps types, links, components, labels, `outcome` and
the ledger core of this table. The triage inbox, rank, the query
language, saved queries, boards, custom fields and cross-repo links are
Milestone 2 or later (D36).

| Jira concept | frob v2 | Pinch avoided |
|---|---|---|
| issue types, hierarchy levels | type enum (section 3) plus configurable depth; one `parent` edge | Epic Link / Parent Link / parent churn (pinch 10) |
| system and custom fields | fixed core schema; typed extras in `frob.toml`, validated at write | 700-field configurations, global field ids (2) |
| statuses, categories, transitions, conditions, validators, post-functions | categories fixed (`triage`, `todo`, `in-progress`, `done`, plus derived `blocked`); display names free; guards are predicates on `close` and `land`, not a transition graph; policy change is a commit | "transition not found", admin-only workflow edits, saved JQL breaking on rename (3) |
| resolution | mandatory `outcome` written atomically with the terminal status: done, fixed, wont-fix, duplicate, invalid | Done-without-resolution, "Unresolved" counted as resolved (9) |
| priority | `low`, `medium`, `high`, `critical` enum | - |
| class of service | `class` enum: `expedite`, `fixed-date`, `standard`, `intangible`; `ticket new --class`, `ticket update --class`; `doable` lists expedite first, then fixed-date by `due`, then the rest by priority and age (section 3) | - |
| components | registry in config, each with path globs and optional owner; double as the product selector in the monorepo | free-text drift |
| versions / fix version | milestone = release object (never a ticket type) with state, date, notes, derived from git tags where present | release cut outside tickets |
| labels | declared in config; unknown label is a write error | typo-prone free text (19) |
| issue links and inverses | typed edges with inverses and topology constraints, one canonical table in section 3 | multi-parent requests, unmanaged link types (19) |
| sprints | optional time windows (`cycle` objects) with start, end, goal; membership is an event, so carry-over is computed and velocity counts only the completing cycle | Sprint field accumulating, commitment distortion (8) |
| boards, swimlanes, quick filters, WIP limits | saved queries plus group-by; rendered by CLI, TUI and web GUI (shared/cli-contract.md) | unmapped statuses vanishing, cross-project sprint leakage (shared/cli-contract.md) |
| backlog rank | per-queue fractional index stored in the ticket; a rebalance is an ordinary commit | LexoRank rebalancing lock and stuck migrations (6) |
| story points, time tracking, worklogs | optional `points`; measured tokens, cost and wall-clock from events; no hand-logged hours | estimation theatre, duplicate point fields (7) |
| comments | typed events: note, decision, question, answer, evidence; the body stays the spec | ticket-as-chat, decision at comment 27 (17) |
| watchers, notifications | none; `doable`, `ticket log --since`, SSE in the GUI, one optional webhook | inbox noise (pm-and-releases.md) |
| changelog, history | event files plus git history; query predicates `was`, `changed after` | - |
| automation rules | hooks and policy rules in `frob.toml`, versioned, run locally | opaque rules, step quotas |
| JQL, saved filters | `frob ticket query` with a small language over the SQLite projection: field predicates, history predicates, graph functions (`blockedBy`, `childrenOf`, `doable`); saved queries in config | index lag, missing totals, token pagination (pinch points 14, 15) |
| dashboards, gadgets | `frob stats` and the GUI dashboards over the same queries | - |
| permissions, security levels | repo access; agent identities with capability flags in config | five permission layers (shared/architecture.md) |
| team- vs company-managed | one implementation | migration losses (20) |
| Plans: dependencies, capacity | dependency graph native; capacity is points per cycle (pm-and-releases.md section 5); agent concurrency is the WIP limit | - |
| REST API, webhooks | the JSON envelope (shared/cli-contract.md) is the API; MCP and HTTP wrap it | rate limits, /search churn (15) |
| triage inbox (Linear) | agent-filed tickets land in `triage`; `accept`, `decline`, `snooze`, `duplicate` verbs; triage rules in config | agent noise in the backlog |
| auto-archive, stale close | thresholds in config; archive is a query, ids never reused | done items vanishing, key renumbering (18) |
| bulk edit | `query | update` applied as one commit with `--dry-run` diff first | 1000-issue cap, per-group transitions (4) |
| markup | CommonMark only | wiki vs ADF (16) |
| offline, CLI | the CLI is the product; git is the sync | no offline mode (5) |
| session objects (Linear agents) | the lease plus worktree is the session: holder, started, heartbeat, and `question` comments that mark the ticket blocked on an answer | "who is working on what, blocked on which question" |

Explicitly not adopted: notification schemes, issue security levels,
screens and field configurations, multiple parents, hosted multi-tenant
anything.

## 5. Agentic usage versus human Jira usage

Measured in notes/v1/agent-usage.md (36,610 agent calls, 34 days).

| Jira assumes | Agents actually do | v2 consequence |
|---|---|---|
| one person edits one issue in a browser | dozens of workers mutate the ledger concurrently from worktrees | ledger commits on one configured ref by compare-and-swap, append-only events, leases shared through .git |
| a human reads a screen | 97 percent of calls parsed text with grep/tail/sed | JSON envelope by default off-TTY, schema per verb |
| a click either works or shows a dialog | half of failures were blind identical retries; `work` on a started ticket errored | idempotent verbs, `already: true`, `--wait` instead of failing |
| notifications arrive | agents poll; one ticket produced 14,346 status polls | `land` is synchronous and `--wait <secs>` bounds lock waits; there is nothing to poll |
| fields are set one at a time in a form | 3,149 one-field setter calls at 5-13 s each | `update` with a patch, `batch` on stdin, sub-100 ms reads |
| the issue id is given at creation | 761 of 763 tickets were born as drafts and promoted later at 62 percent failure | ULID at creation, no promote |
| scope is implicit (assignee) | scope is a write lease; 1,100 refusals were lease or empty-scope related; agents rarely consulted `contention` | lease refusal carries holder, age, and overlap; `new` accepts scope; scope patches in one call |
| "done" is a click | closure needs evidence that passes and binds to criteria; 90 percent of `close` calls were refused for a reason | keep the guards, make each refusal name the one missing thing and its command |
| ticket text is a summary for a person | ticket text is the agent's prompt: body, acceptance, scope, verify commands | `brief` stays; body sections are structured (context, plan, log) and `brief` renders them |
| cost is time logged by hand | cost is tokens and wall time per ticket | token and cost fields folded from `cost` events written by the harness hook and land |
| help is a documentation site | 8 percent of calls were `--help`; the most common agent-visible line was an informational notice prefixed ERROR | small closed verb set, `--schema`, remedies in every error, never mislabel severity |

Hot path to optimise first (79 percent of calls): check, land, show,
evidence, scope/update, new, done-report, work, body, start.

## 6. Evidence and closure

Kept from v1: closure requires resolvable evidence that passes at the
closing commit, bound to acceptance criteria, in scope; bugs need a
repro that fails at the parent commit; done report auto-composes
Changed and Evidence sections.

A record added for a ticket that a design entity names with a
`frob:ticket` directive also stores that entity's `body_digest` from
`grimble graph --json` in its `design` list (`{entity, body_digest}`;
grmb-spec 12.8, D207). The digest is read when the record is captured;
a missing `grimble`, a repository without a model, or an entity without
a digest leaves the list empty, and such a record is outside every WINDOW.
Milestone evidence has no ticket of its own; an attestation (on a ticket or a
milestone) also stores the digests of every ticket named in its facts.

Large artifacts (screenshots, benchmark dumps, traces) never enter the
repository (decided 2026-10-02). An evidence record stores the
measurer, the verdict, the measured value, the commit, and for a blob
its BLAKE3 hash, size, media type, and a URI. The URI points at an
artifact store the repo configures: `[evidence] store =
"dir:.git/frob/artifacts"` (local, outside `.frob/` and non-authoritative,
for solo work) or any https URL; milestone 1 supports exactly those two (an https
store is record-only: the URI is written to the event, nothing is
uploaded).
`gh-artifact:`, `gh-release:` and `s3:`/`gcs:` stores are Milestone 2 or
later (D36); they need a client and credentials that no milestone-1
crate owns, and GitHub run artifacts expire (90 days by default). `frob
ticket evidence fetch <id>` retrieves and verifies the hash; a missing
or expired blob degrades the verdict to Unmeasured with the URI shown,
never to Failed, and Unmeasured on a terminal ticket is not a finding.
Text under `[evidence] inline_max_bytes` (default 16 KiB; a
command transcript, a JSON measurement) may be stored inline in the
event file after `gob-log` redaction (docs/design/shared/architecture.md section 1.5); a
TICK rule scans events for unredacted secret patterns. Captured text also has the worktree root,
repository root and home directory rewritten to `<worktree>`, `<repo>` and `~` before the digest is
computed (the digest covers the stored, scrubbed text); any other home root (another user, or when `HOME` is unset) becomes `~other`, in the transcript, test names, failed test names and the ref alike, so a record never needs `ticket doctor --fix`. Lease events record the worktree relative
to the repository parent, so a pushed ledger never carries the local user name; `TICK004` reports
committed ledger files that still hold an absolute home path (an Error).

Private terms (~2GXRW72) generalize the same scrub. One redaction engine (`frob-ledger::redact`) holds the built-in
home-path rule and the user's private rules, so detection, repair and audit are shared. Rules are local-only
(`frob/privacy.toml` in the user config dir and under the git common dir, docs/design/shared/architecture.md section 1.6), never committed, and
a matched term is never echoed anywhere: errors, logs, findings and audit events carry the rule's `replace` label and a
12-character blake3 hash of its pattern. Write time: every ledger write (new, update, comment, close and drop reasons,
evidence, milestone and cycle files) and `ticket fragment` refuse text matching a private rule with exit 2
(`E-REDACT-PRIVATE`) and write nothing. Detection: `TICK005` (Error) flags ledger files and changelog fragments holding a
term; it is local-only, so where no local rules exist (CI) it reports nothing. Repair: `ticket doctor --fix` applies every
rule in the one forward `tickets(scrub)` commit with the TICK004 scrub, recomputing inline digests and writing one `scrub`
audit event per ticket naming files, digests, and each rule by label and hash. Idempotent. Out of scope: commit messages and
staged source files.

`ticket doctor --fix` repairs a ledger written before that scrub existed, in place and in one forward commit
(`tickets(scrub): ...`) through the same write path as every other repair; git history is never rewritten. Every ledger
file below the tickets directory that holds an absolute home path is rewritten with the repair scrub: this checkout's
worktree to `<worktree>`, the repository (the checkout and a local `origin`) to `<repo>`, sibling worktrees to the form
relative to the repository parent (`app-wt/T1`), the home directory to `~`, and any other `/home/<name>`, `/Users/<name>`,
`/root` or `C:\Users\<name>` root to `~other`. A file the rewrite cannot clear is reported (`scrub_unresolved`), never
guessed at. Integrity: an `evidence` event whose `digest` covered its inline text (or an attestation statement) has the
digest, and `size`, recomputed over the scrubbed text, so it still verifies and still binds the same criteria; a record
whose digest did not match its text before is left as it was, so the repair never masks damage; a record that points at a
`dir:` artifact keeps its digest because artifacts outside the ledger (`.git/frob/artifacts`) are local and untouched.
Each ticket with a rewritten file gets one audit-only `scrub` event naming the files and the old and new digests
(milestone and cycle files are rewritten the same way and named in the commit and the doctor output only), and
`ticket.md` is re-checked against the fold of the scrubbed events and re-rendered from it if they differ. A second run
finds nothing and commits nothing. The GUI renders blobs through
the same fetch. Changed: evidence providers are a trait
(`pytest`, `cargo test`, `ctest`, `vitest`, `junit`, `command`) so
Rust-only or docs-only repos close tickets natively (milestone 1 ships
`nextest`, `pytest`, `command` and `file` providers, later `vitest`, `jest` and
`dotnet` (`dotnet test` with a TRX report); the `command` and
`pytest` providers may run only programs in `[evidence] allowed_tools`,
and `pytest` is listed by default like `cargo` and `git`); the close guard
requires a Measured record for the code-changing types task, bug,
security, story, incident and invariant, and `ticket close
--no-evidence --reason` bypasses it with an audited `evidence-bypass`
event; evidence verdicts
are `Passed | Failed | Unmeasured` and Unmeasured never reads as Failed.

**The pytest provider** (~M525Y1M). `ticket evidence add --provider pytest
--ref '<pytest args>'` runs `pytest -o junit_family=xunit1 --junitxml=<tmp>
<args>` through gob-exec (a `Tool` program, so `pytest` must be in
`[evidence] allowed_tools`, else `E-EVIDENCE-TOOL`), reads the junit file and
records one measured record whose test names (`test_count` in the event, the
full list in the artifact named by `tests_digest`; old events carry an inline
`tests` array that still reads) are pytest node ids
(`tests/test_a.py::TestC::test_m[param]`) and whose `failed_tests` are the
cases with a `failure` or `error`; a skipped case did not execute and is not
listed. The transcript (stdout then stderr) goes through the same redaction,
path scrub and non-ASCII escape as every provider, so the stored text is
ASCII. A ref matching more than 50 tests draws a warning from `evidence add`
that suggests exact-name refs. Exit code 5 (nothing collected) is `E-EVIDENCE-NO-TESTS`, not a failed
measurement. `frob test` selects Python tests the same way as Rust ones (the
Python adapter puts their symbols and calls in the graph; a changed `.py`
file is no longer an `unresolved_files` entry), runs
`pytest <node id>...` for them after the nextest run, and appends one
evidence event per runner. With `--all`, pytest also runs when the work tree
has Python test files. Tests that run pytest need `python3` and `pytest` on
`PATH`: when absent they skip with the named reason on stderr, or fail when
`FROB_REQUIRE_PYTHON_TESTS` is set.

**Which outcomes the close guards apply to** (~8RZK7QV). Evidence, criteria,
children and changelog fragment prove that a change was made, so they apply
to outcomes `done` and `fixed` only. `invalid`, `duplicate` and `wont-fix`
close on a required `--reason` alone: no `--no-evidence` or `--no-changelog`
is needed (or asked for), and `ticket close` without a reason is a usage
error for them. The decision is one function of the outcome,
`frob_evidence::done::guards_apply`, read by both guards, so `ticket close`
and `land` agree.

**Done requirements** (~XGAS05X, release 0.532.0). A close or land with
outcome `done` or `fixed` also evaluates every entry of `[pm] done_requires`
(pm-and-releases.md section 4) through the close guard `done_requires`, in
the configured order, and refuses on the first that fails.
`criteria_evidenced`: every acceptance criterion is bound (a measured
passing record or an attestation, latest per provider, reference and
criterion, through the moved maps); a story, bug or security ticket with no criteria at all is
refused (`E-DONE-NO-CRITERIA`, ~H1NWDN9, D92: with nothing to bind the requirement would pass
vacuously; always on, checked before `done_requires`, and not excused by the evidence bypass, so
it is refused on its own close or land, never on a later one), while chore, docs, epic and every
other type may close with none, since there is nothing to state as given/when/then and a forced
criterion would be ceremonial (an exempt ticket without criteria closes with a warning);
`--no-evidence --reason` bypasses this requirement only and records
the `evidence-bypass` event. `no_open_children`: every child is done.
`changelog_fragment`: `changelog.d/<ULID>.<type>.md` exists and passes the
compile's own validator (REL003, ~HE2EX99): an unknown type, an empty or
non-ASCII body or a near-miss product prefix refuses with the validation
message, and `check --ticket` reports the same before land. A change with no
user-visible effect (a design document, an internal refactor, a test-only
change) is closed with `--no-changelog --reason TEXT` instead (~Y8ZYBDW): both
flags are required together on `ticket close` and `land`, there is no
exemption by file type, and the person or agent states why. The exemption
by ticket type is `[pm] changelog_exempt_types` (~YYJGRFJ), default `["epic", "docs"]`:
an epic is closed by its children and a docs change rarely has a user-visible
effect, so neither is asked for a fragment (the close guard and the per-ticket
REL003 check skip a missing one); `[]` requires a fragment for every type, a
fragment an exempt ticket does carry is still validated, and other and custom
types stay strict. Measured evidence is likewise not asked of epic, docs, chore
and custom tickets (the evidence guard's code-changing list), so a docs ticket
closes with neither fragment nor evidence unless the repository opts in. The reason is
recorded as a `changelog-exempt` event with the actor, written before the close so a crash cannot leave a closed ticket without its record (a refused close leaves the event on the open ticket; a retry with the same reason reuses it), satisfies
`changelog_fragment` and REL003 for that ticket (`check --ticket` included, and
`land` passes the exemption to its own check), and is shown by `ticket show`,
`ticket show --format md`, the close and land reports and `release status`, which lists the
exempted tickets of the milestone. A done close also needs the work on the base (`branch_merged`, ~CKZS2R3, code `E-DONE-UNMERGED`): `ticket close --outcome done` and `fixed` are refused while `ticket/<handle>` holds commits not reachable from the base branch, naming the first of them and the remedy, `frob land` or, audited, `--no-land --reason TEXT` (a `land-exempt` event, written before the close). `land` merges before it closes and so never trips the guard; a ticket whose branch was deleted after landing has nothing unmerged and closes cleanly; `wont-fix`, `duplicate` and `invalid` are exempt like the other done guards. `ticket doctor` reports every done or fixed ticket whose branch still holds unmerged commits and has no `land-exempt` event as `E-DOCTOR-UNMERGED`. The "no change to the scope paths on the base since the ticket started" doctor check is not built yet.

`objective_target_met` passes for a ticket that is not a
quality objective, and `docs_touched_or_excepted` and an objective's target
are Unresolved today (no recorded docs exception, no stored target), so they
refuse until they can be evaluated, so the default `done_requires` lists only
`criteria_evidenced`, `no_open_children` and `changelog_fragment` and listing the
other two is an explicit choice; a requirement that cannot be evaluated
never passes. Other requirements have no bypass beyond editing
`done_requires`. The running `frob` and its `grimble` sibling are allowed
command-evidence tools by canonical path without being listed in
`[evidence] allowed_tools`.

**Attestation** (~7KQSA8Z, release 0.532.0). Some criteria cannot be
measured by a tool (two outside repositories managed for two cycles with
no data loss). `--provider attestation --statement TEXT [--fact F]...`
(ticket and milestone `evidence add`) records a person's statement: the
text, the attesting identity (git `user.email`) and the facts it rests on
(https URLs, commit ids and ticket handles or ULIDs; shape is checked and
commits and tickets must exist). It is recorded as measured and passed
only when the identity is listed in `[evidence] attesters` and the call
comes from a TTY on stdin and stdout with no known agent marker in the
environment (`CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CODEX_SANDBOX`,
`CODEX_CI`, `GEMINI_CLI`, `CURSOR_AGENT`, `OPENCODE`, `FROB_AGENT`); the
pattern of shared/security.md 2.3 (no `--yes`; the refusal is exit 3 with the
JSON `requires_human = true` and a prose remedy, never a command for an
agent; nothing is written). The knob `[evidence] attesters` is
materialized: `frob init` and `frob config sync` write the repository
owner (git `user.email`) into it, and an empty list means nobody may
attest (fail closed; the refusal says so). The statement is ledger data
(origin `ledger`, shared/security.md 2.10): JSON keeps it exact, every text
render goes through `Attestation::label` which escapes it and shows
`[attested by X: "statement"]`, so an attestation never reads as a tool
measurement in `ticket show` and `brief`, `milestone show`, `milestone
evidence list` and `release status`. Binding uses the ordinary rule
(latest record per provider, ref and criterion), the ref being a digest
key of the statement. The TTY check stops scripts and obedient agents,
not a goal-seeking process running as the same user (shared/security.md 2.3).

**Design clause anchors as facts** (~AMNDCCT, grmb-spec 9.1, 12.8, D202, D207).
Built for the fact shape and the row verdict (status below). A fact may also be a design clause
anchor `KIND/NAME/verified_by[i]` (grmb-spec 9.1: the entity's logical
location plus the i-th `verified_by` clause), the tie that lets a passed
attestation be the pass verdict of a `manual` `verified_by` row. Like the
`implements` link (section 3) the anchor is validated only through
`grimble graph --json` (the entity exists and has a `manual` clause at that
index) and is Unresolved, never accepted on shape alone, when grimble is
absent. The overlay (grmb-spec 17.3) reads a passed attestation carrying the
anchor on a live ticket that implements the entity or a design ancestor as
that row's verdict; otherwise the row is `not-run`. Evidence and
attestation records already store the `body_digest` of the design entity
a `frob:ticket` directive ties to the ticket (section 6; grmb-spec 12.8
WINDOW, PM048, D207); a record without it is outside every WINDOW and
never makes PM048's digests differ. Status: the digest, the anchor fact
shape and the row verdict are built. `attest` accepts an anchor on its
shape (`frob-evidence` `attestation::anchor_facts` reads them back) and
`frob_ledger::design::manual_row_verdict` returns `Pass` only for a passed
attestation carrying the row on a live ticket that implements the entity
or a design ancestor, else `not-run`; an entity the graph lacks is
`not-run`. The grimble existence check stays with the overlay.

## 7. Landing

Reduced to the transaction v1 kept proving it needed: validate (close
preconditions, scope, passenger directives, deletion filter), compose
the squash in a detached worktree, run the full `frob check` and bound
tests synchronously (fast now), compare-and-swap publish the ref with
the same bounded retry as ledger commits (re-read the tip, rebuild,
retry), update the index and worktree of any checkout that has that ref
checked out (for the landed paths only), record events, print
LAND-PROOF. The whole transaction runs in the foreground of the calling
process under the land lock (`.git/frob/land.lock`); there are no jobs
and no job records (D25). No merge queue daemon, no deferred sweep, no
mirror, no rapid debt; `land --wait <secs>` bounds only the wait for the
land lock and exits 3 `E-WAIT-TIMEOUT` (retryable) when it expires.
The lock is taken before the base merge and the check, so a queued land does no heavy
work and the base cannot move under the holder's check (~78ATXCB). The holder file
`.git/frob/land.lock.holder` is JSON (pid, holder, start, stage, last progress, build profile);
`frob land --status` prints it. A watchdog thread in the holder releases the lock and exits 75
when no stage has progressed and no child process runs for `FROB_LAND_STALL_SECS` (default
1200); a waiter terminates a frob holder idle for twice that bound, and replaces the lock file
when a dead holder's descendants still pin it, logging the reason. A debug build warns.
The land envelope carries `stages`, the wall time of each stage in order: `lock-wait`, `merge`,
`check` with its `check:scoped`, `check:tool:<name>`, `check:head` and `check:base-findings`
parts, `recheck` (with `recheck:` parts) or `retry-reuse` on a stale-base retry, and `publish`
(~NPGXR8M). The cargo stages already narrow themselves to the affected packages (`{packages}` in
`[[check.tool]]`) and are served from the tool memo when their inputs are unchanged; a stale-base
retry whose base delta misses the ticket's cone reuses the whole first check (`retry-reuse`).
The land check is a ratchet (~QAFRXM3): it refuses only blocking findings
that are new relative to the base tip by fingerprint (docs/design/shared/rules.md section 6).
Findings already on the base are reported as `pre_existing`, fixed ones as
`resolved`, and neither blocks. When `--wait` re-merges a moved base the base
side is recomputed for the new tip.
The land also gates on CI of the base (~GHMWDGG, audit H1). Before merging it reads
the check runs of `refs/remotes/origin/<base>` (the commit GitHub has run CI for; the local
tip when there is no remote-tracking ref) through the GitHub CLI, by way of `frob_release::ci`,
behind an injectable `CiReader` so tests never touch the network. A failing check that counts
refuses with `E-LAND-BASE-RED` (exit 3) naming each check and its run URL. Which checks count is
the `[land]` table read from the committed base `frob.toml`: `ci_required` (name patterns,
`*` wildcard, case-insensitive; empty means every check) minus `ci_ignore` (default
`*publish*` and `*release*`, jobs that test no code, so a broken dev-tag step cannot freeze
every land). A pending check only warns. An unreadable state (no `gh`, no network, no origin,
no checks) is never green: by default it is reported as `Unresolved` in the warnings and the
land proceeds; `block_on_unknown_ci = true` refuses with `E-LAND-BASE-CI-UNKNOWN`.
`require_base_green = false` turns the gate off. `--override-base-ci --reason <text>` lands
anyway and records the reason as a decision comment on the ticket. The dry run applies the gate.
`[land] verify = "ci"` and the quarantine that goes with it are
Milestone 2 or later (D36). Push is opt-in (the `frob land --push` flag). Version bump
and changelog fragments stay land-owned; the fragment check is rule
REL003 (notes/research/documentation.md section 5.5).

Flags of `frob land` (from `frob land --help`; the output flags are shared by every verb):

- `[TICKET]...`: one or more ids, handles or aliases, landed in order in one foreground run and
  continuing past a refusal; defaults to the ticket leased by this worktree.
- `--dry-run`: report what would change without changing it.
- `--push`: push the base branch to origin after landing.
- `--wait <SECS>`: wait up to this many seconds for the land lock and retry when the base moves
  (default 0).
- `--status`: show who holds the land lock, at which stage and for how long; land nothing.
- `--keep-worktree`: keep the worktree and branch after landing.
- `--relaunch`: merge the remote base into the kept branch of a ticket landed locally on a
  diverged base; never rebases; with `--push`, checks the result and pushes it to the `[sync]`
  remote.
- `--train`: land through the batched train: enqueue, then wait for the train to land the ticket.
- `--enqueue-only`: implies `--train`; run the ticket-local gates, queue the ticket and return at
  once (the ticket leaves the WIP count while queued).
- `--no-evidence`: close without measured evidence; needs `--reason` and is audited.
- `--no-changelog`: close without a changelog fragment; needs `--reason` and is audited.
- `--override-base-ci`: land despite a red or unreadable base CI; needs `--reason` and is audited
  on the ticket.
- `--reason <TEXT>`: why no evidence or no changelog note is recorded (with `--no-evidence`,
  `--no-changelog` or `--override-base-ci`).
- `--outcome <VALUE>`: outcome the ticket is closed with (`fixed`, `wont-fix`, `duplicate`,
  `invalid`, `done`; default `done`).
- `--profile`: report per-stage timings with the slowest stage flagged.
- `--timing`: print every land stage with its seconds and, for check tool stages, whether the
  memo hit or missed.
- `--schema`: print the JSON schema of the verb's data and exit.
- `--format <auto|json|text|md>`, `--json`, `--text`, `-q/--quiet`, `-v/--verbose`,
  `--color <auto|always|never>`, `--cwd <DIR>`: shared output and invocation flags.

Land train and the lock (D137, docs/design/shared/build-test-ci.md section 4 "Land train"). The train driver holds
`land.lock` for the whole train (build, every check round, publish), so the lock stays the single
serialization point: a fallback single-ticket `frob land <t>` simply waits on it. The driver
reports `train:build`, `train:check round k` and `train:publish` through the lock progress, so
`land --status` and the stall watchdog keep working. There is no separate `train.lock`; the train
state file is written only by the lock holder. Still no daemon and no job store.

## 8. Verbs (see shared/cli-contract.md for the full surface)

```
frob ticket new|show|list|doable          # `show --format md` is the brief, `list --category triage` the inbox, `lease list --contention` the hot files (D104)
frob ticket update|link|unlink|comment|accept|evidence|attach|body
frob ticket evidence [add|fetch] | done-report   # two-word path, action positional (shared/cli-contract.md section 2)
frob ticket triage accept|decline|snooze|duplicate   # four verbs (section 8.1); the listing is `ticket list --category triage`
frob ticket start|requeue|review|close|drop|reopen
frob ticket component ... | reconcile | doctor
frob work <id> | frob land <id> | frob cycle ... | frob forecast ...
frob merge-driver            # hidden; git invokes it (section 2)
```

### 8.1 The triage inbox

The inbox is the set of tickets in category `triage` that are not snoozed
(~PM0HX6M). Five verbs, each its own two-word-plus-action path like
`ticket evidence add`:

| Verb | Writes | Needs |
|---|---|---|
| `ticket triage accept` | `transition` triage to todo, then `triage` (accept) | tickets or a query; `--reason` optional |
| `ticket triage decline` | `transition` to done with outcome `wont-fix`, then `triage` (decline) | tickets or a query; `--reason` required |
| `ticket triage snooze` | `triage` (snooze) with `until` only; the ticket stays in `triage` | tickets or a query; `--until` required (a date `2026-11-01`, midnight UTC, or an RFC 3339 time, strictly in the future); `--reason` optional |
| `ticket triage duplicate` | `link` (`duplicates`, skipped when the edge exists), `transition` to done with outcome `duplicate`, then `triage` (duplicate) | one ticket and `--of <ticket>`; `--reason` defaults to `duplicate of <target>` |
| `ticket list --category triage` (hidden alias `ticket triage list`, one minor) | nothing | optional `--label`, `--type`, `--at <date or time>` (the inbox as of that instant), `--all` (also snoozed tickets, with `snoozed_until`) |

Selection: the verbs that take tickets accept several positionals, or a
query over the inbox (`--label`, `--type`; a query never selects a snoozed
ticket), not both and not neither (usage, exit 2). One call is one ledger
commit for every ticket it decides (a single ticket's commit is named
`tickets(triage-<action>): <handle> <title>`, a batch
`tickets(triage-<action>): <n> tickets`), and the report
(`data.entries`) lists every ticket with `status` `applied` or `already`,
its category and outcome after the call, plus the `commit`.

Idempotence and refusal: a ticket whose latest `triage` event is this same
decision (same action and, for a snooze, the same `until`) is `already` and
writes nothing; a call whose tickets are all `already`, or a query that
selects nothing, exits 0 with `already` set. A ticket that is neither in
`triage` nor already given this decision is refused with
`E-TRIAGE-NOT-IN-TRIAGE` (exit 3) and the remedy `frob ticket list --category triage`;
one refusal aborts the whole call before anything is written, so a batch
is all or nothing. Decline and duplicate do not run the close guards (like
`ticket drop`, they close without done), and a newer snooze replaces an
older one. A snooze hides the ticket while `at < until`; the inbox reads
the ticket's latest `triage` event, so no frontmatter field records it.

Roughly 35 verbs against v1's 65 parser nodes; every setter is `set`;
`--json` and `--reason` are universal; mutating verbs are idempotent on
repeat (same request, same result, exit 0).

## 9. Measurement runs are read-only (~W91G8EK)

Every verb that runs `frob check` to measure (`close`, `evidence --check`, `land`
pre-checks, `verify`) leaves `RunOptions::fix` false; only a top-level
`frob check --fix` applies Deterministic fixes. As a backstop the pipeline
re-digests every file a Deterministic fix would edit after a run without `--fix`
and fails with `E-CHECK-READONLY` (an internal error) naming any file that no
longer matches its analysed digest. `check_verb.rs` holds the positive control:
a fixable `DSL003` tree stays `git status` clean under `frob check` and changes
under `frob check --fix`.

Under `--ticket`, `--fix` edits only files the lease covers (its scope globs plus
`[lease] shared_files`; dependents pulled in by `ticket_hops` are checked but never
edited). A fix with an edit outside that set is left whole, unapplied, and listed in
`fix.skipped_scope` with the `frob lease widen <ticket> --glob <path>` command that
would cover it. A diff scope (`--diff-base`) edits only the files the diff names.

## 10. Ledger hygiene conventions (~339DX5F)

The PM hygiene rules (PM003, PM005, PM007, PM008) warn about ledger shape, and
the fixes below are the intended ones; none of them delete a ticket.

- **A story is for a user-visible outcome.** A story carries `persona`,
  `capability` and `outcome_text` (each at least three words, PM003) and at
  least one acceptance criterion in Given/When/Then form (PM005). Purely
  internal engineering work (a rule family with no criteria yet, a refactor, a
  provider) is a `task`, retyped with `frob ticket update <t> --set type=task`.
- **Free-form criteria.** A criterion that cannot be phrased Given/When/Then
  starts with `free-form:` and a reason, which PM005 accepts.
- **`no-story` exemption.** A task whose scope touches user-visible paths but
  that has no story parent (PM007) takes the `no-story` label and states the
  reason in its body. Children of a story that is later retyped to a task fall
  under this rule too.
- **Stale todo (PM008).** A ticket past `[pm.max_age_days]` is finished,
  requeued or dropped with a reason; `frob ticket drop` is reopenable, so
  unscheduled wishlist items with a dead scope are dropped rather than left
  to age. An in-progress ticket whose work landed is closed with
  `frob ticket closeout`, which needs bound evidence, a reason and a
  changelog fragment.

## 11. Where a ticket file lives, and the reindex commit

### 11.1 The path function

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

### 11.2 Moves happen only in reindex commits

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

- **Replay check (TICK007, Error).** Run the reindex in memory on the
  parent commit's tree with the frob version named in the trailer; the
  resulting tree id must equal the commit's tree id. This proves the
  commit is the pure output of the reindex function, with no room for a
  hidden edit, because tree ids cover every byte. It needs no
  similarity heuristics: a moved ticket file keeps its blob id.
- **No moves elsewhere (TICK008, Error).** A ledger commit without the
  trailer may not rename or delete a ticket file or touch an event file
  it did not add.
- **No misfiled tickets (TICK009, Error, machine fix).** On the tip of
  the branch every ticket file is at its computed path; the fix is
  `frob ticket reindex`.

When the frob version in the trailer is not available locally, TICK007
reports Unresolved (reason `generator-version`) instead of guessing; CI
pins the frob version, so CI always decides it.

### 11.3 Moving an existing ledger onto the ticket branch

Milestone 1 repositories (this one before its migration) kept tickets at
`tickets/<id>/` on the code branch. `frob ticket migrate --to-branch`
is a one-shot, verifiable move:

1. Build the orphan branch from the current tree: each
   `tickets/<id>/ticket.md` becomes `<top-epic-slug>/<slug>.md`, each
   `tickets/<id>/events/<ulid>.toml` becomes `.events/<id>/<ulid>.toml`,
   then run the reindex generators over that tree, so the migration
   commit already carries the README (replacing the init placeholder),
   per-epic pages, indexes, glossary, guide and TOUR. `--dry-run` prints
   the mapping.
2. Verify before anything else changes: for every ticket, the fold of
   the branch copy equals the fold of the original (the doctor check on
   both), and the event counts match; any difference aborts.
3. Commit the branch, then one commit on the code branch that removes
   `tickets/`, sets `[tickets] ref_mode = "orphan"` (commits go on the
   orphan ticket branch `[tickets] branch`; `trunk` advances the
   configured `ref` and `branch` writes to the checked-out branch, so
   neither is the migrated layout), and adds the README region. Leases,
   evidence and land read the ledger through frob-ledger, which reads
   the configured `ref_mode`.
4. Rollback is reverting that one code commit; the branch can be
   deleted. The migration ticket is the first user of the reindex
   replay check (TICK007), run on the initial branch commit.

### 11.4 Why this is the least confusing option

A newcomer opening `parser-rewrite/` sees every ticket of that epic and
nothing else; no ticket says "I actually belong elsewhere". History
survives the move (`git log --follow` sees an identical blob). The cost,
broken links to old paths, is removed by never linking paths (section 2.3).

### 11.5 New rules and verbs (summary)

| Id or verb | Kind | Meaning |
|---|---|---|
| TICK006 | Error, P+, machine fix | ledger-path-reference: a path used as a ticket reference |
| TICK007 | Error, P+ | reindex-not-pure: replay of a reindex commit does not reproduce its tree |
| TICK008 | Error, P+ | move-outside-reindex: a non-reindex ledger commit moved, deleted or edited existing ticket or event files |
| TICK009 | Error, P+, machine fix | misfiled-ticket: a ticket file is not at its computed path |
| TICK010 | Error, P+ | ledger-branch-workflow: a `.github/` file on the ticket branch other than the byte-exact generated nudge workflow |
| TICK011 | Error, Unresolved when the API cannot answer | ledger-branch-unprotected: the hosting API says the ticket branch allows force pushes or deletion (`frob doctor` and `frob check`, the latter skipped without a GitHub token, shared/security.md 2.11) |
| PM031 | Error | good-first-incomplete |
| PM032 | Warning | good-first-pool-low |
| `E-TICKET-PATH` | CLI error | a file path was given where a ticket id is expected |
| `frob ticket reindex [--check] [--code-readme]` | verb | regenerate the ticket branch (and the README region) |
| `frob ticket url <id>` | verb | current web URLs for a ticket |
| `frob profile newcomer\|experienced` | verb | local presentation profile |
| `frob tour` | verb | the repository tour in the terminal |

### 11.6 Owner decisions (2026-10-04)

1. Sub-epics are flattened into the top epic's directory; no hierarchy
   below it.
2. A title change renames the file (section 11.1), through a reindex
   commit like any other move. Freezing slugs was rejected: with ids as
   the only references and the reindex proven pure by replay, a frozen
   slug's only effect would be a file name that disagrees with its
   title.

## 12. The one-way mirror: what it does

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

The mapping is `frob_mirror::config::MappingConfig` (a `version` and one
route per field: `label` with a prefix, `field`, `issue_type`, `state` or
`drop`), validated by `frob_mirror::mapping::Mapping::load`. Every
mappable projection field (`ticket_type`, `labels`, `priority`,
`points`, `milestone`, `epic`, `category`, `outcome`, `owner`,
`assignee`) must be routed or dropped; a missing one is a config error
naming the field. `Mapping::apply` turns a projection into `PlannedOps`
(labels, custom fields, issue type, state inputs).

### 12.1 The producer is platform agnostic: the issue projection

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

**Decision: identities are tracker user ids, never logins.** Both
`[mirror.identities]` (frob identity to tracker user id) and
`[mirror] bot_ids` hold numeric user ids: a login can be renamed,
released and claimed by someone else, an id cannot. A login string where
an id belongs is a config error, and two identities may not share an id.
An unmapped owner or assignee leaves the issue unassigned and adds a
note line. The tracker key (`PROJ-123`) is added to the ticket's aliases
so a lookup by that key resolves. Implemented in
`crates/frob-mirror/src/identity.rs` (`IdentityConfig`, `resolve_people`,
`add_tracker_alias`, `resolve_reference`). The `frob mirror recreate`
verb still reads `bot_ids` as logins until it is moved to ids.
| `provenance` | last event ULID, render digest, producer version | the digest is what divergence detection compares |
| `private` | fields withheld by `[mirror] exclude` | never sent; recorded so a reader knows something was withheld |

Each adapter declares a `capabilities` record (native sub-issues,
native links, custom fields, state reasons, markdown dialect) and the
mapping is checked against it at load: a projection field the mapping
neither routes nor explicitly drops is a configuration error, so no
information disappears silently. The trait and record are
`frob_mirror::adapter::{TrackerAdapter, Capabilities}`; `route_relations`
sends parent and child edges to native sub-issues when declared, and
every other edge to native links when declared, else to body links.
The projection's JSON schema is
generated from the Rust type (`cargo dev gen schemas`, file
`docs/schemas/issue-projection.json`);
`frob mirror render <ticket>` prints a projection, so a GitLab or Jira
adapter can be developed and tested from recorded projections without
touching the producer.

## 13. The protocol (audited and model-checked)

Evidence: notes/review/mirror-audit.md (an adversarial audit: 1 critical,
9 high, 17 medium, 6 low findings MIR-AUD-01 to 33; 30 GitHub facts
verified against GitHub's documentation, 16 marked UNVERIFIED) and
docs/design/mirror/ (a TLA+ model checked with TLC: the first
version of this protocol violated no-loss, convergence, no-duplicate
and map integrity; with the fixes F1-F9 below every safety property
holds in every checked configuration, up to 12.8 million distinct
states). The model's README has the properties, the counterexamples
and an inductive argument for the safety properties beyond the model's
bounds.

No part of this protocol ever fails a check or blocks a land (owner
decision). Failures surface as MIR001 (mirror behind, with a reason)
and in `frob mirror status`.

### 13.1 Who runs it, and with which credentials (MIR-AUD-01, 26, 31)

- The mirror job is defined only on the default branch and runs on
  `schedule`, `workflow_dispatch` and `repository_dispatch`, which
  always use the default branch's workflow file. It is never triggered
  by a push to the ticket branch: a push-triggered job would run the
  workflow file from the ticket branch, which every ledger writer can
  edit. A secret-free nudge workflow on the ticket branch may send a
  `repository_dispatch` ("something changed"); it carries nothing the
  mirror trusts.
  Implemented in `crates/frob-ledger/src/nudge.rs`: `render` emits the
  workflow as a pure function of the ticket branch and the bot ids (sorted,
  deduplicated), so the TICK rule can byte-compare it; it uses no secrets
  and no environment (the token is `github.token`), and its `if:` skips
  pushes whose `github.actor_id` is a mirror bot id, so the mirror's own
  ledger commits send no dispatch. Scheduled runs also catch tracker edits made when the
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
  Implemented in `crates/frob-mirror/src/lock.rs`: `acquire` takes the
  lock record (`writer-lock`, run id and time) by CAS; a live holder
  returns `Busy` (exit without work, no error), one older than the TTL
  (`lock_ttl_minutes`) is taken over and logged; `release` frees it only
  if still ours. `pending_commits` returns the ledger commits after the
  stored `watermark`, minus the mirror's own (`triggers_run` is false
  for those).
- MIR001 is time-based: "no successful run for N hours" (scheduled runs
  are delayed, dropped, and disabled after inactivity), plus the
  per-scope reasons below.
  Implemented in `crates/frob-obligations/src/mir.rs`: `mir001` takes the
  recorded `MirrorRunState` (last successful run, per-scope reasons), the
  clock and N, and returns Advisory findings only: one when the last
  success is older than N hours or absent (stating the age), one per
  reason (`rate-limited` with the next window, `budget-too-small`,
  `token-blind`, `marker-key-unknown`, `render-limit`,
  `write-not-sticking`). A fresh success with no reasons emits nothing.

### 13.2 What a run looks at: feed, sweep and budget (MIR-AUD-02, 10, 27, 33; F8)

- **Change feed.** One GraphQL query per 100 issues lists the bot's
  issues updated since the stored cursor, ordered by update time; only
  issues whose update time passed the stored observed value get a
  history read. Ledger-driven work comes from tickets with unpublished
  events. Both sources select work (F1: not only ledger changes).
  Implemented in `frob_mirror::feed`: `read_feed` pages a `FeedSource`
  (GraphQL `filterBy {createdBy, since}`, `orderBy UPDATED_AT ASC`, 100 per
  query), sorts by update time and returns the new cursor; `parse_page`
  fails the page on any `errors` entry or partial data, so the cursor does
  not advance. `needs_history` selects only issues whose update time is
  past the shard's observed `updated_at`.
- **Sweep.** Each run also reconciles the next K issues of a persisted
  round-robin cursor, so every issue is visited within ceil(N/K) runs
  even when the feed misses a change (repository-level renames do not
  bump issue update times). `frob mirror status` states that bound.
  `frob-mirror::sweep::next_batch` selects the batch (sorted ULIDs after
  the cursor, wrapping) and `visit_bound` computes ceil(N/K).
  `frob-mirror::status::build` assembles the `mirror status` report (last
  success, MIR001 reasons per scope, the ceil(N/K) bound, gaps, contested
  fields, create-uncertain tickets with start time, unmirrored tickets) and
  `StatusReport::render` prints it.
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
  Implemented in `frob-mirror::progress`: `ProgressWriter` writes the
  pending shards and then the index round-robin cursor every K
  operations, so a crash repeats at most K operations and never one
  already behind the cursor.
- **Selection cursors (F8).** `frob_mirror::run` persists one resume point
  per work class (the last completed item) under the `run-cursors` store
  key (`load_cursors`, `save_cursors`) and every run selects with them, so
  Update, Create and Reconcile rotate round robin across runs instead of
  always serving the lowest-sorted ticket. The sweep keeps its own cursor
  there and gives its batch ages in `next_batch` order, so with `sweep_k`
  above what the budget covers the run serves a prefix and the next run
  continues after the last one served. A missing record (an older store)
  starts fresh and the sweep falls back to the index cursor; a cursor whose
  ticket is gone resumes at the next larger key and wraps. The record is
  rewritten only when a cursor moved, after the progress commit.
- **Outbox** (work class 2). Implemented in `frob_mirror::outbox`: each
  ledger event is a `LedgerEvent` keyed by ticket ULID plus event ULID and
  sets one field to one value. `plan_ops` selects oldest first (incremental:
  events past the shard's `last_event`; `Mode::FullResync`: latest value
  per ticket and field, rotated after the round-robin cursor, bounded by
  the budget); `run` skips a value equal to the shard's normalized observed
  value without any request, stores the tracker's normalized value after a
  write, holds a failed ticket's later operations for the next run, defers
  tickets with no issue to the create class, and stops on a rate limit.

### 13.3 Identity: markers, creates and duplicates (MIR-AUD-04, 05, 09, 15, 16, 24; F3-F6; spoofed marker)

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
  Implemented in `frob_mirror::marker`: `format_marker`, `parse_marker` and
  `evaluate`, which returns a `MarkerVerdict` (`Adopted`, `Spoofed` for
  MIR003, `Rejected` for a bad MAC or MIR001 unknown kid, `Unreadable`,
  `None`).
- **Lookup is read-your-writes.** The mirror finds a ticket's issues by
  listing the bot's issues (by creator, newest first), never through
  search, which lags (F5). The tracker is the identity authority; the
  map file is a cache of it.
  On GitHub this is `github::lookup::lookup_since`: it pages the creator
  listing (page 1 upward, newest first) and stops at the first page that
  holds an issue created before the create-start time, or at an empty
  page. The `ListingSource` trait has no search method. An ignored live
  test checks a creator listing saved right after a create
  (`FROB_GH_PROBE_LISTING`, `FROB_GH_PROBE_NUMBER`); its result is recorded on the ticket as the
  verification of the read-your-writes fact.
- **Create protocol.** Before a create the run derives a nonce and
  records "create started" in the journal. A create whose outcome is
  unknown (timeout, 5xx, crash) makes the ticket create-uncertain: no
  further create for it until recovery has listed the bot's issues back
  to the create's start time and matched the nonce. GitHub's create has
  no idempotency key, so a duplicate can still appear (a timed-out
  create that lands after its retry); the model confirms this cannot be
  prevented, only bounded: at most one extra issue per uncertain create.
  Implemented in `frob_mirror::create`: `create_issue` persists the
  uncertain flag and commits the journal entry before the tracker is
  called, `recover` adopts the issue whose bot-authored marker carries
  the nonce (or reports it not landed), and `CreatedIssue::store_cursor`
  stores the history cursor taken before listing, only after the commit
  proof.
- **Duplicates are found every run, not only on first sync** (F6): if
  two bot issues carry valid markers for one ULID, the lowest issue
  number is canonical; the others are closed as duplicates of it, keep
  their markers (so they are never re-adopted), and their history is
  still read so edits made on them are captured (F3: the history cursor
  is taken before the ticket's issues are listed and kept across a
  create).
  Implemented in `frob_mirror::dups`: `plan_duplicates` picks the lowest
  issue number per ULID from the adopted markers (`claims_from_verdicts`),
  `close_duplicates` closes the others with reason duplicate (a reopened
  one is closed again, an already closed one is left alone), and
  `read_duplicate_history` reads their history so human edits are captured.
- **Status codes.** 301 (moved or transferred) updates the cached
  location after verifying the marker; 404 is never read as "deleted"
  (a token that cannot see the issue also gets 404); 410 (deleted)
  marks the ticket unmirrored and reports it. The mirror never
  recreates an issue without a person running `frob mirror recreate
  <ticket>`. A blindness check (the token sees the repository and its
  own recent issues) runs first; if it fails the run stops with MIR001
  `token-blind`.
  Implemented in `crates/frob-mirror/src/blind.rs`: `classify` maps
  adapter errors to a `Disposition` (moved, not visible, unmirrored; none
  may create), `handle_moved` swaps the cached location only when the
  marker verifies at the new one, and `check_blind` reads the repository
  and the bot's newest issue and returns MIR001 `token-blind` on failure.
  Recreate is implemented in `crates/frob/src/mirror_recreate_cmd.rs`:
  `recreate` probes the old issue, proceeds only on a 410 (drops the
  shard's tracker identity, then runs the create protocol), and refuses a
  404 ("may be invisible, not deleted"), a live issue and a moved one.
  The verb `frob mirror recreate <ticket> [--repo OWNER/NAME]` wires it
  to `BranchShardStore` (on the ledger ref, under `.mirror/map`) and
  `GithubAdapter` over the native `NativeTransport` (`ureq`/rustls). It
  needs `GH_TOKEN` or `GITHUB_TOKEN`, and the marker key in
  `FROB_MIRROR_KEY`; the key id, repository and bot login come from
  `[mirror] kid` (default `k1`), `repo` (default `origin`) and `bot_ids`
  (default the token's user id).
- **Own writes.** A dedicated App identity (`[mirror] bot_ids`, by
  user id). Before each mutation the run journals (issue, field, value
  digest, run id); a history entry is "own" only if its actor is a bot
  id and its value digest matches a journaled write. Any other bot
  entry is an edit by "unknown automation". Unconfirmed journal entries
  are re-read at the start of the next run.
  Implemented in `crates/frob-mirror/src/journal.rs`: `journaled_write`
  commits the entry (CAS) before the send closure runs;
  `Journal::classify` returns own, unknown automation, or other (not a
  bot id); `Journal::recover` re-reads unconfirmed entries at run start
  and marks each confirmed or lost (a failed read stays unconfirmed).
  The journal is stored under the key `journal-<ULID>` next to the
  ticket's shard; 30-day pruning is not yet implemented.

### 13.4 Reconcile, never block (owner decision; MIR-AUD-03, 06, 11, 20, 25; F2, F7, F9)

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
  Implemented in `frob_mirror::normalize`: `ReadBack::plan` (skip or write),
  `ReadBack::record` (the one read-back; a value that did not change is
  MIR001 `write-not-sticking`).
- **The cursor is the history position actually read** (an event id,
  never a time), advanced only after the proposals it covers are
  committed (F2, MIR-AUD-25).
  Implemented in `frob_mirror::cursor`: `HistoryCursor` (an event-id
  newtype), `begin_read` (history after the stored cursor, yielding a
  `PendingCursor` held outside the shard so it survives a create) and
  `PendingCursor::advance`, which needs a `Committed` proof.
  Implemented in `frob_mirror::reconcile`: `reconcile_issue` turns an `IssueView`
  (projection, current values, history after the cursor, journal, read-back)
  into `Reconciled`: `Revert`s to the projection, `Edit`s to record as
  proposals and capture gaps. Own writes are skipped; a bot id with no
  journaled write is unknown automation; tracker-owned fields are untouched.
  It returns data and never an error, so MIR002 stays Advisory.
  Revert wars end in `frob_mirror::contest`: `ContestBook::observe` takes what a
  run saw for one (item, field) and returns `Decision`. The n-th re-application
  by the same actor is reverted only after 2^n runs saw it (1, 2, 4) and at most
  once a day; the third makes the field contested (MIR002 Advisory): no more
  reverts and `Decision::Propose` carries the latest value for the one pending
  proposal. `ContestBook::clear` (ledger event on the field, accept or decline)
  ends the contested state; `ContestBook::contested` lists `ContestedField`s for
  `frob mirror status`.
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
  Read-time capture is `frob_mirror::capture`: `capture_issue` keeps every
  retained history entry with its author, captures an unexplained change
  with `Fidelity::Gap` and no author, and `GapListing` collects the gaps
  (unexplained, beyond retention, rename, project field, deletion) for
  `frob mirror status`.
  Implementation: `frob-mirror::github::read` merges timeline events and
  body revisions into ordered history entries and returns a fidelity
  gap, never an error, for truncated or deleted revisions.
- **GitHub writes** (`frob-mirror::github::write`). `GithubWriter` sends
  only the diff between the issue as read and the rendered projection:
  title and body in one patch, then `frob:` labels one add or remove
  call at a time (labels outside `frob:` are never touched, the set is
  never replaced), then a close carrying a `state_reason` derived from
  the outcome (`completed`, `not_planned`, `duplicate`) and the reason
  text. `WriteTransport` has no delete call. Relations use native
  sub-issues or links when the capabilities say so; the rest are body
  links already in the render. Mutations are serial and at least one
  second apart by an injected `Clock`. A failed write (5xx, throttle)
  is recorded `Failed`, no effect is assumed, the issue's remaining
  writes stop, and the next run recomputes the same diff.
- **The GitHub adapter** (`frob-mirror::github::adapter`).
  `HttpTransport` performs one raw REST or GraphQL call (live through
  the native `github::http::NativeTransport`, a `ureq`/rustls client with no
  subprocess, or recorded for offline tests); `GithubRest` maps the
  `WriteTransport`, `HistorySource` and `ListingSource` contracts onto
  endpoints; `GithubAdapter` implements `TrackerAdapter` on top, signing
  the creation marker with the `Keyring` and spacing mutations by the
  injected `Clock`. Create returns `Unknown` on timeout, 5xx or throttle
  and `Failed` only on a definite rejection. Update reuses the marker
  already in the body and refuses a body with none. Body revisions come
  from GraphQL `userContentEdits` (REST has none). Listing uses the
  creator filter, never search. Capabilities: native sub-issues, no
  native links (so only parent and child go native), native state
  reasons. Labels and assignees are additive; there is no delete call.
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

**Field ownership guard (implemented in `frob-mirror/src/fields.rs`).**
The raw `[mirror.fields]` table deserializes into `FieldsConfig` (an
owner per projected field plus `tracker_owned` custom field names).
`FieldOwnership::load` checks it covers exactly the projected fields:
an unowned projected field is `Unowned`, an owner entry for a field
that is not projected is `Unknown`; both are returned as errors.
`FieldOwnership::authorize` is the only way to build a `WriteOp`, so
a write to a tracker-owned target cannot be expressed: a label outside
the `frob:` prefix and a field listed in `tracker_owned` are refused
with `TrackerOwned`. `plan_writes` turns a rendered `PlannedOps` into
authorized writes and drops (logging at debug) every refused one;
`plan_project_writes` does the same for requested project fields.

**Map shards (implemented in `frob-mirror/src/mapfile.rs`).** One JSON
shard per ticket, keyed by ULID, holds issue number, node id, cached
location, last observed normalized values, history cursor, last event
hash and the create-uncertain flag (nonce, start time); a small `index`
shard holds the round-robin and change-feed cursors. Writes are
compare-and-swap on the content hash. `resolve` checks the cache, then
the tracker listing (lowest number wins), and only then allows a create;
an uncertain create forces recovery first. The driver advances the
change-feed cursor only after a clean, completed run that reconciled
every feed item, so an unprocessed issue is never skipped.

### 13.5 Proposals (MIR-AUD-07, 08, 12, 22; F9)

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
  section 2.4.

#### Recording proposals

`frob_mirror::proposals::record(sink, existing, edits, actor, now, per_run)` turns tracker
edits (each with its tracker event id and full value) into `proposal` and `proposal-superseded`
events and hands all of them to `ProposalSink::commit` in one call. Edits whose tracker event id
is already in the ledger fold (any state) are skipped, as are edits not newer than a recorded
proposal of the same field. Several edits of one field in a run collapse to the latest. A cap
(`per_run`, or an (issue, field) already recorded today) holds an edit back and `advance_to`
stops before it. The excerpt is the first 200 characters, escaped with origin `tracker`; the
digest covers the full value.

#### GitHub rendering

`frob_mirror::github::render::render(projection, marker)` turns a projection
into a `RenderedIssue` (title, body, labels, digest). Each section becomes a
`##` heading in projection order (scope, evidence and the managed notice are
the generated read-only block), the hidden marker string supplied by the
marker keyring is the last line of the body, and the only label is
`frob:managed`. Acceptance lines are rendered as `Bound:` / `Unbound:` list
items, never task-list checkboxes. The digest is the projection's own render
digest, and rendering is a pure function, so the same projection yields
byte-identical output. Neutralisation and render limits layer on top.

#### Reading and declining proposals

`frob ticket proposals list [TICKET]` shows every pending proposal: tracker
item id, field, actor id, time, digest, the origin (always `tracker`) and an
excerpt. The excerpt is untrusted tracker text, so it is escaped for its
origin and capped at 200 characters before it is printed.
`frob ticket proposals accept TICKET TRACKER_EVENT` is TTY-only and refuses an agent marker; it refuses editors without a `[mirror.identities]` tracker user id and edits to scope, acceptance, evidence or links, fetches the full value, shows the escaped diff and, once confirmed, updates the field citing the tracker user id and appends `proposal-accepted`. A value gone from the tracker closes the proposal as unavailable (`proposal-expired`, reason `unavailable`).
`frob ticket proposals decline TICKET TRACKER_EVENT --reason TEXT` appends a
`proposal-declined` event carrying the reason; the proposal then leaves the
pending list, and repeating the command is a no-op. `frob check` prints the
count of pending proposals as a note and in `pending_proposals`; it is advisory
and never changes the exit status. Accepting a proposal is a separate step.

### 13.6 Publishing safely (MIR-AUD-18, 19, 21, 23, 28, 30, 32)

- Render limits are checked before any write: body size (65536
  characters), label count and length, sub-issue limits. A ticket that
  cannot be published is isolated (MIR001 for that ticket only); one bad
  ticket never stops the run. Implemented in `frob-mirror` `limits`:
  `check` tests one rendered issue (body 65536 characters, 100 labels of
  at most 50 characters, 100 sub-issues) and `plan` splits a run into
  publishable and isolated tickets, each isolation carrying its reason.
- Mirrored text cannot trigger GitHub side effects: `@` mentions and
  team mentions are neutralised, closing keywords (`fixes #12`) and
  cross-repository references are rendered as plain text, no task-list
  checkboxes are rendered. Closing keywords in code-branch commits that
  close a mirrored issue are treated as a tracker edit (reverted and
  proposed), never fought silently.
  Implemented in `frob_mirror::closing`: `reconcile_closing` reopens the issue
  (a `state` revert to open) and records the closure as a proposal while the
  ledger is open; with the ledger done nothing is reverted.
- Publication is irreversible (edit history is readable by anyone with
  read access): `[mirror] exclude` and redaction apply before the first
  publish; evidence is published as verdicts and links, never
  transcripts.
- Schema checks run before any write. `github::schema::validate` compares
  the mapping with the repository's labels, issue types and project fields
  and fails once with a single MIR001 `schema-missing` diagnostic listing
  every missing item and its remedy. `project_field_access` makes `Status`
  the only writable project field. `inventory::reconcile` compares the
  stored id-to-name inventory of labels, milestones and issue types with a
  fresh read; a rename or removal is recorded once as a `Fidelity::Gap`
  and reconciling again reports no change. Neither is wired into a run
  path yet.
- One managed label (`frob:managed`), not one label per ULID. Projects
  fields are written only with an App that has project access, and
  only status is reconciled; other project fields are read-time only.
- Transfer, conversion to a discussion, lock and pin are classified and
  reported, never acted on blindly.

**Privacy scrub (implemented in `frob-mirror/src/privacy.rs`).**
`project_private` sanitizes every free-text field of the facts before
`project` runs: lease worktree paths become `[worktree]`, registered
secret values and secret-shaped text (via `gob-log` redaction) become
`[REDACTED]`. `[mirror] exclude` is still applied by `project`.

**Write gate (implemented in `frob-mirror/src/fields.rs`).** The
`WriteOp` type is only constructible through `FieldOwnership::authorize`,
so the publishing path cannot build a write to a tracker-owned target.
The rules it enforces: only labels in the `frob:` namespace
(`frob:managed` among them) are writable; custom fields named in
`tracker_owned` are refused; and of the project fields only `status`
(`PROJECT_STATUS_FIELD`) is writable, any other project field fails
with `ProjectFieldReadOnly`. `plan_writes` (for rendered labels and
custom fields) and `plan_project_writes` (for requested project
fields) return only the authorized operations.

### 13.7 Operational details (closing the re-cut's gaps)

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
- **TICK010 ledger-branch-workflow** (Error): a `.github/` tree on the
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
  Implemented in `crates/frob-mirror/src/github/neutralise.rs`: a
  mention (`@name`, `@org/team`), an issue reference (`#12`), a
  cross-repository reference (`owner/repo#5`) or a closing phrase
  (`fixes #12`, `Closes: o/r#3`) becomes a single code span; email
  addresses are not mentions. Task-list lines (`- [ ] x`, `* [x] y`,
  `1. [x] z`) become `- Unbound: x` / `- Bound: y`. Existing code spans
  and fenced blocks are left verbatim, and the pass is idempotent.
- **Verifying the tracker facts.** The audit left 16 GitHub facts
  UNVERIFIED (among them read-your-writes listing, the nudge's
  permission, autolink limits); one ticket verifies each against the
  live API in a sandbox repository before the first live run, and the
  adapter's capabilities record cites the result.

The git-ref-backed shard store is `frob_mirror::shardstore::BranchShardStore`:
each key is `<prefix>/<key>.toml` on a ref (`issue = N` for the ledger's
reader, plus the exact shard bytes in a `payload` string), `put_if` is a content-hash
compare-and-swap, and a lost ref race is re-read and re-checked rather than
blindly retried.

The shard JSON also carries the per-field `read_back` record and the
tracker `event_values` the mirror retained (omitted while empty, so older
shards decode unchanged). `LedgerTickets::state` reads both back through
`Ledger::mirror_payload`; a missing or undecodable payload yields empty
values and reconcile falls back to the current tracker value.

### 13.8 Stated properties and assumptions

Properties (formal statements and TLC results in
docs/design/mirror/model.md):

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
wrongness (audit section 14, TA1-TA15): the run is the legitimate single
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

## 14. Later: bringing material decisions back

Field ownership decides conflicts, not timestamps: code-coupled fields
(scope, acceptance, evidence, links, done-by-land) are always owned by
the repository; a short list of planning fields (priority, cycle,
assignee, drop or reopen with a reason) may be declared tracker-owned;
everything else changed in the tracker arrives as a proposal event that
someone accepts or declines with `frob ticket proposals`. Tracker users
map to identities in configuration; unmapped users' changes are always
proposals. This phase needs polling or webhooks and is not part of the
first version.

## 15. Owner decisions and open questions

Decided 2026-10-04:

1. GitHub Issues first, behind the platform-agnostic projection
   (section 12.1); GitLab and Jira adapters route from the same
   projection later.
2. Tracker edits never block: one owner per field, repository-owned
   fields reverted deterministically, edits captured as proposals within
   the stated bounds (section 13.4). Replaces the earlier skip-and-report.

3. The code repository's pointer is a generated region of README.md,
   not a `TICKETS.md` (shared/documentation.md 3.2).

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D7

Ledger commits are built by frob, not mined from history; no mirror, no splice, no merge queue daemon (writer story refined in D23)

### D8

Synchronous land with fast check; deferred-verification machinery not rebuilt

### D14

Jira concepts kept with changed mechanisms: categories plus outcome, typed links with topology, cycles as events, fractional rank, triage inbox, saved queries as boards

### D23

Ledger writer story (audit H1): ledger commits advance the configured ledger ref (`[tickets] ref`, default the trunk branch); the commit tree is built from that ref's tree plus the changed ticket directory, never from any index; the ref is updated by CAS with bounded retry; when a checkout has the ledger ref checked out, frob updates its index and worktree for the ledger paths only; `[tickets] ref = "branch"` mode puts ledger commits on the current branch for protected-trunk and fork flows; TICK rule flags a referenced ticket absent from the base

### D24

Ids (audit H2): the full 26-char ULID is the only persisted form in directives, links, trailers and fragments; the human handle is the unique suffix of the random part (shown as `~xxxxxxx`, minimum 7 chars), accepted by every verb; a fixer expands handles on write and a TICK rule flags abbreviated ids in tracked text

### D26

Leases (audit H4, M9): `work` and `start` are idempotent only for the same holder (actor plus worktree path); another caller gets exit 3 `E-LEASE-HELD` naming the holder; acquisition runs under one lock file in the git common dir; overlap is glob intersection OR resolved-set intersection; TTL and WIP limits are materialized knobs with WIP off by default; leases are single-clone

### D33

Ticket model (audit M7, M8, M29): statuses are categories plus close guards, no transition graph; the terminal field is `outcome`; priority is `low|medium|high|critical`; `blocked` is derived; `milestone` is a release object, not a ticket type; the planning unit is `cycle`; one canonical link table with inverses; one event-kind table; non-ticket events live under `events/` at the repo root; frontmatter integrity means "equals the fold of events"; the merge driver unions events and re-folds, and `frob init` or `doctor` installs it

### D46

Ledger (T-0018): `create` is the birth event kind; `rev` is the event-format revision; `spawned` is a link kind; epics are excluded from doable; reconcile commits on concurrent event writes; the merge driver reads events from disk and from every merge head; `~suffix` handles display at 7 or more characters; `ticket new --alias`; `error_set` stays in frob-ledger (D22 trial outcome); evidence events are written by frob-evidence with a re-fold until `EventBody::Evidence` exists (Milestone 2)

### D47

Leases and worktrees (T-0019): lease files under `<common_dir>/frob/leases/` with one `leases.lock`; overlap is a conservative glob-text intersection with a resolved-set backstop; steal only for the same ticket; worktrees are `../<repo>-wt/<handle without ~>` on branch `ticket/<handle>`; `start` records the checkout root as holder path

### D48

Evidence and tests (T-0020, T-0031): task, bug, security, story, incident and invariant tickets need a Measured record; `--no-evidence --reason` is audited as `evidence-bypass`; an https store is record-only; tests are detected by attribute scan, `tests` module or `tests/` directory; selection reach adds a unique-name caller backstop; TEST001 is owned by frob-tests and COV003 is registered but never emitted

### D92

Zero acceptance criteria (coordinator decision 2026-10-04, owner delegated, ~H1NWDN9, replaces tickets.md section 6's "passes with a warning"): closing done or fixed, or landing, a story, bug or security ticket with no acceptance criteria is refused (`E-DONE-NO-CRITERIA`, naming the type), the silent-zero principle of ~A6C2R1C; chore, docs, epic and the other types are exempt (an epic's criteria are its children); no bypass, so the refusal lands on the offending close

### D99

Coordinator decision 2026-10-06 (~PVJ9SQM): a scope glob matching no file tracked at HEAD warns and never refuses, naming a near tracked path when one exists (same file name elsewhere, or one typo away); repositories with no tracked files are never judged; a ticket that will create files declares each entry with the ledger label `creates:<glob>` (`--new-scope`, `--add-new-scope`, `lease widen --new-glob`), so no schema change and the declaration persists

### D79

Accepted with changes (owner decision 2026-10-04, ~J8PJHKX): ledger on the orphan branch frob-tickets with a human layout and machine event logs; one-way mirror run by one CI writer with an idempotent outbox; GitHub Issues first behind a platform-agnostic producer (the typed IssueProjection, routed by per-tracker adapters with declared capabilities; unrouted fields are a config error); tracker edits never block anything: one owner per field, repository-owned fields reverted deterministically and every edit captured from the tracker's history as a proposal event (MIR002 Advisory; owner revision 2026-10-04, ~J7ZYSVZ); schema validation before writes; Unresolved when behind; protocol rewritten from an adversarial audit and a TLA+ model (~HV53M66): default-branch-only job on schedule and dispatch, change feed plus round-robin sweep and budget planner, cursor = history position read, read-time capture with gap reporting, nonce create protocol with duplicate closing, markers only in the bot-authored creation revision, never recreate without a person, revert backoff and contested fields, proposals by reference keyed by tracker event id

### D81

Navigation (owner decisions 2026-10-04, ~AMBGYQ4): ticket paths are presentation and never references (TICK004, E-TICKET-PATH, indexes/by-id); a ticket file lives at `<top-epic-slug>/<slug>.md` (sub-epics flattened; the slug follows the current title) and moves only in a reindex commit proven pure by replaying it to the same tree id (TICK005-007); generated pages are committed, marked in three layers and gated by GEN001; the code repository's ticket pointer is a generated README region; docs/SUMMARY.md is generated from docs/order.toml; newcomer and experienced profiles in the guide and the CLI (presentation only); good-first tickets are linted (PM031, PM032); a generated repository tour (TOUR.md, frob tour) from templates and pinned real examples
