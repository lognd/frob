# Tickets: the project-management core

Status: DRAFT (T-0001, a v1-format id that migrates with an alias).
Inputs: notes/v1/tickets.md (data model, 25 incident classes, Jira gap
list), notes/rust-ecosystem.md section 3, notes/v1/ops-and-integrations.md
(telemetry), notes/jira.md and notes/v1/agent-usage.md (sections 7 and 8).

## 1. Thesis

v1's 52k lines of ticket code are mostly defenses against one cause:
branch-local ledgers with many concurrent writers. Four patches exist
for that cause (display overlay, cross-worktree lease side channel,
mirror commits, land-time splice) and 109 of 300 main commits were
mirror churn. v2 picks ONE writer story and builds Jira-class features
on top of it.

## 2. Storage and identity

Layout note (D79, D81): the ledger moves to the orphan branch
`frob-tickets` with a human layout, `<top-epic-slug>/<ticket-slug>.md`
for tickets and `.events/<ULID>/` for event logs (mirror.md 1,
navigation.md 2). The `tickets/<id>/` layout below is the milestone-1
machine layout still in use until that migration lands; everything else
in this section (ULID identity, handles, aliases, events) holds for
both. In either layout a path is presentation and never a reference
(navigation.md 1).

- One directory per ticket, `tickets/<id>/`, containing `ticket.md`
  (TOML frontmatter + markdown body), `events/<ulid>.toml` (append-only
  state changes, field changes, comments, evidence, reviews), and
  `attachments/`. Terminal tickets are not moved; `archive` is a view.
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
  events of kind `comment`. See section 2a for the full model.

### 2a. Events

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
commits on the ledger ref (CAS); no crate writes event files directly
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
| `lease` | ticket | op (take, renew, release, steal), holder, scope | start, work, requeue, close | contention, wave |
| `review` | ticket or exception | subject, verdict, reviewer | review, `exceptions` review of an accept | EXC012, cycle report |
| `exception` | ticket | kind (accept, defer, hotfix), rule, site | check --fix, land --hotfix | ticket page, close guard |
| `cycle` | ticket | cycle id, op (assign, carried, over-commit), reason (required for over-commit) | cycle assign, cycle close | velocity, forecasts, cycle report |
| `attempt` | ticket | outcome (failed, abandoned), reason | requeue --failed, a failed land | brief, doctor |
| `triage` | ticket | action (accept, decline, snooze, duplicate), until | ticket triage | inbox |
| `cost` | ticket | tokens in, out, cache, cost, wall seconds | harness hook, land | stats, forecasts |

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
  out, frob updates that checkout's index and worktree for `tickets/`
  only, and refuses with a remedy if those paths have local edits.
  `[tickets] ref_mode = "branch"` puts ledger commits on the current
  branch instead, for protected-trunk and fork flows (`ref_mode =
  "trunk"`, the default, commits to `[tickets] ref`, default
  `refs/heads/main`). A reconcile commit is made when concurrent event
  writes leave the frontmatter behind the fold. No mirror step, no
  overlay. In the default mode a land carries no ledger diff because the
  ledger was never branch-local.

### 2b. CI, forks and offline clones

CI is a fresh clone and sees only pushed commits. Ledger commits on the
trunk must therefore be pushed before or with any PR whose code
references the ticket (`frob land` pushes when `[land] push` is true;
otherwise `frob ticket doctor` lists unpushed ledger commits). The TICK
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
| classification | priority (low, medium, high or critical), component (registry, monorepo.md), labels, area |
| hierarchy | parent, children (derived), links (typed, section 4) |
| planning | cycle (object; membership is an event), milestone (a release object, never a ticket type), points, due, rank (fractional, LexoRank-style) |
| state | status (category plus status name, section 5), outcome (done, wont-do, duplicate, cannot-reproduce, absorbed), blocked (derived from open blockers) |
| scope | scope (globs), scope_mode (exclusive, append, none), scope_ack reason, evidence_scope |
| acceptance | criteria list with bound evidence ids |
| evidence | evidence records (runnable id, kind, last verdict, verified_at, at commit) |
| agent | worktree, branch, lease (derived), tokens (in, out, cache), cost |
| audit | events (external files) |
| custom | per-repo declared typed fields (string, int, enum, date, symref, ticket ref) |

Types replace v1's kind x tier conflation: `epic | story | task | bug |
security | docs | invariant | incident | chore | custom`. A milestone is
a release object (releases.md 1, 8), not a ticket type. A story has
`flavour = user_story | quality_objective` and carries the structured
fields that pm-enforcement.md requires (section 2 and 2a there). Each type
declares its evidence policy (bug needs a repro that fails at parent,
docs accepts command evidence), its land commit type, and whether it can
be worked directly (epics cannot, and `doable` excludes them).

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
| `implements` | none stored | target is an invariant or a grimble entity; a grimble entity is validated only through `grimble --json`, and is Unresolved when grimble is absent |
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
landing (outcome wont-do, duplicate, cannot-reproduce, absorbed, or
evidence-only work). A repo can choose the guard set; it cannot remove
the integrity guards on `done`. Post-actions (`release_lease`,
`record_land`) are fixed behaviour. `fail` is not a state: it is an
`attempt` event plus a `requeue` back to `ready`.

- Scope is a write lease taken at `start`, stored in
  `<common_dir>/frob/leases/<id>.toml` (single clone: shared by its worktrees,
  invisible to other clones and machines; cross-clone safety is the
  ledger CAS plus the SCOPE rule at land). The holder is the actor plus
  the worktree path; an agent harness sets `FROB_AGENT` so parallel
  agents are distinct holders. `work` and `start` are idempotent only
  for the same holder; any other caller gets exit 3 `E-LEASE-HELD`
  naming the holder.
- Acquisition is atomic: read all leases, compute overlap, write the
  new lease, all under one lock file (`<common_dir>/frob/leases.lock`,
  an flock) in the git common dir; `--steal` takes the same lock and is
  allowed only for the same ticket (it never takes another ticket's
  lease), recording the previous holder in the lease history.
- TTL is the knob `[lease] ttl_secs` (default 7200); the lock wait is
  `[lease] lock_timeout_ms` (default 5000), and append-shared files such
  as `Cargo.lock` are exempt from overlap through `[lease] shared_files`
  (every verb that opens the lease store passes the same config; the old
  `[tickets] registry_files` alias is gone). The heartbeat is renewed by any frob verb run from that
  worktree and, when it exists, by the daemon, so a 40-minute build
  with no frob call stays inside the TTL; a stale lease can be taken
  with `--steal` and a reason. Leases release automatically on every
  terminal transition and on `requeue`.
- Overlap is glob intersection OR resolved-set intersection (in code, a
  conservative intersection test over the glob text, with the resolved
  file set as a backstop): two
  tickets scoped to `src/newmod/**` overlap even though no file exists
  yet (v1's glob-overlap proof is kept), and a glob that is disjoint
  from another's text but resolves to a shared file also overlaps.
  `doable` excludes overlaps; `wave --agents N` partitions;
  `contention` names the hot files. The per-holder WIP limit is
  `[pm.wip] in_progress_per_identity` (the former `[lease] wip_per_holder`
  was removed so there is one knob), and `work` and `start` also refuse
  with `E-WIP-REPO` past the repository limit `[pm.wip] in_progress`,
  naming every holder; expired leases do not count and are reported as
  stale.
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

## 7. Jira mapping and pinch points

Source: notes/jira.md (data model, 22 pinch points with evidence, 27
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
| resolution | mandatory `outcome` written atomically with the terminal status: done, wont-do, duplicate, cannot-reproduce, absorbed | Done-without-resolution, "Unresolved" counted as resolved (9) |
| priority | `low`, `medium`, `high`, `critical` enum | - |
| components | registry in config, each with path globs and optional owner; double as the product selector in the monorepo | free-text drift |
| versions / fix version | milestone = release object (never a ticket type) with state, date, notes, derived from git tags where present | release cut outside tickets |
| labels | declared in config; unknown label is a write error | typo-prone free text (19) |
| issue links and inverses | typed edges with inverses and topology constraints, one canonical table in section 4 | multi-parent requests, unmanaged link types (19) |
| sprints | optional time windows (`cycle` objects) with start, end, goal; membership is an event, so carry-over is computed and velocity counts only the completing cycle | Sprint field accumulating, commitment distortion (8) |
| boards, swimlanes, quick filters, WIP limits | saved queries plus group-by; rendered by CLI, TUI and web GUI (gui.md) | unmapped statuses vanishing, cross-project sprint leakage (gui.md) |
| backlog rank | per-queue fractional index stored in the ticket; a rebalance is an ordinary commit | LexoRank rebalancing lock and stuck migrations (6) |
| story points, time tracking, worklogs | optional `points`; measured tokens, cost and wall-clock from events; no hand-logged hours | estimation theatre, duplicate point fields (7) |
| comments | typed events: note, decision, question, answer, evidence; the body stays the spec | ticket-as-chat, decision at comment 27 (17) |
| watchers, notifications | none; `doable`, `ticket log --since`, SSE in the GUI, one optional webhook | inbox noise (pm-enforcement.md) |
| changelog, history | event files plus git history; query predicates `was`, `changed after` | - |
| automation rules | hooks and policy rules in `frob.toml`, versioned, run locally | opaque rules, step quotas |
| JQL, saved filters | `frob ticket query` with a small language over the SQLite projection: field predicates, history predicates, graph functions (`blockedBy`, `childrenOf`, `doable`); saved queries in config | index lag, missing totals, token pagination (pinch points 14, 15) |
| dashboards, gadgets | `frob stats` and the GUI dashboards over the same queries | - |
| permissions, security levels | repo access; agent identities with capability flags in config | five permission layers (git-io.md) |
| team- vs company-managed | one implementation | migration losses (20) |
| Plans: dependencies, capacity | dependency graph native; capacity is points per cycle (pm-enforcement.md section 4); agent concurrency is the WIP limit | - |
| REST API, webhooks | the JSON envelope (cli.md) is the API; MCP and HTTP wrap it | rate limits, /search churn (15) |
| triage inbox (Linear) | agent-filed tickets land in `triage`; `accept`, `decline`, `snooze`, `duplicate` verbs; triage rules in config | agent noise in the backlog |
| auto-archive, stale close | thresholds in config; archive is a query, ids never reused | done items vanishing, key renumbering (18) |
| bulk edit | `query | update` applied as one commit with `--dry-run` diff first | 1000-issue cap, per-group transitions (4) |
| markup | CommonMark only | wiki vs ADF (16) |
| offline, CLI | the CLI is the product; git is the sync | no offline mode (5) |
| session objects (Linear agents) | the lease plus worktree is the session: holder, started, heartbeat, and `question` comments that mark the ticket blocked on an answer | "who is working on what, blocked on which question" |

Explicitly not adopted: notification schemes, issue security levels,
screens and field configurations, multiple parents, hosted multi-tenant
anything.

## 8. Agentic usage versus human Jira usage

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

## 9. Evidence and closure

Kept from v1: closure requires resolvable evidence that passes at the
closing commit, bound to acceptance criteria, in scope; bugs need a
repro that fails at the parent commit; done report auto-composes
Changed and Evidence sections.

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
event file after `gob-log` redaction (architecture.md section 5); a
TICK rule scans events for unredacted secret patterns. The GUI renders blobs through
the same fetch. Changed: evidence providers are a trait
(`pytest`, `cargo test`, `ctest`, `vitest`, `junit`, `command`) so
Rust-only or docs-only repos close tickets natively (milestone 1 ships
`nextest`, `command` and `file` providers; the `command` provider may
run only programs in `[evidence] allowed_tools`); the close guard
requires a Measured record for the code-changing types task, bug,
security, story, incident and invariant, and `ticket close
--no-evidence --reason` bypasses it with an audited `evidence-bypass`
event; evidence verdicts
are `Passed | Failed | Unmeasured` and Unmeasured never reads as Failed.

**Done requirements** (~XGAS05X, release 0.532.0). A close or land with
outcome `done` or `fixed` also evaluates every entry of `[pm] done_requires`
(pm-enforcement.md section 3) through the close guard `done_requires`, in
the configured order, and refuses on the first that fails.
`criteria_evidenced`: every acceptance criterion is bound (a measured
passing record or an attestation, latest per provider, reference and
criterion, through the moved maps); a ticket without criteria passes with a
warning; `--no-evidence --reason` bypasses this requirement only and records
the `evidence-bypass` event. `no_open_children`: every child is done.
`changelog_fragment`: `changelog.d/<ULID>.<type>.md` exists (the full REL003
rules are ~HE2EX99). `objective_target_met` passes for a ticket that is not a
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
pattern of security.md 2.3 (no `--yes`; the refusal is exit 3 with the
JSON `requires_human = true` and a prose remedy, never a command for an
agent; nothing is written). The knob `[evidence] attesters` is
materialized: `frob init` and `frob config sync` write the repository
owner (git `user.email`) into it, and an empty list means nobody may
attest (fail closed; the refusal says so). The statement is ledger data
(origin `ledger`, security.md 2.10): JSON keeps it exact, every text
render goes through `Attestation::label` which escapes it and shows
`[attested by X: "statement"]`, so an attestation never reads as a tool
measurement in `ticket show` and `brief`, `milestone show`, `milestone
evidence list` and `release status`. Binding uses the ordinary rule
(latest record per provider, ref and criterion), the ref being a digest
key of the statement. The TTY check stops scripts and obedient agents,
not a goal-seeking process running as the same user (security.md 2.3).

## 10. Landing

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
`[land] verify = "ci"` and the quarantine that goes with it are
Milestone 2 or later (D36). Push is opt-in (`[land] push`). Version bump
and changelog fragments stay land-owned; the fragment check is rule
REL003 (documentation.md section 6).

## 11. Verbs (see cli.md for the full surface)

```
frob ticket new|show|list|query|board|doable|wave|contention|brief|log
frob ticket update|link|unlink|comment|accept|evidence|attach|body
frob ticket evidence [add|fetch] | done-report   # two-word path, action positional (cli.md section 2)
frob ticket triage accept|decline|snooze|duplicate
frob ticket start|requeue|review|close|drop|reopen
frob ticket component ... | reconcile | doctor
frob work <id> | frob land <id> | frob cycle ... | frob forecast ...
frob merge-driver            # hidden; git invokes it (section 2)
```

Roughly 35 verbs against v1's 65 parser nodes; every setter is `set`;
`--json` and `--reason` are universal; mutating verbs are idempotent on
repeat (same request, same result, exit 0).
