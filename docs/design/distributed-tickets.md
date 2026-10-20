# Distributed tickets: many people and agents on one ledger

Status: draft
Owner: frob
Decisions: none (proposal for owner review)
Audience: contributor

Provenance: research pass 2026-10-20 against the `experimental` tip
556d2260d5, the release binary and the open ledger. It answers: when do
tickets live on the orphan ticket branch, how code branches relate to
it, and how several people and agents share claims, freshness and
conflicts without redoing work. It builds on mirror.md section 1,
tickets.md sections 2 and 2b, and the owner decisions recorded on the
open epic 01M1WJMD5GVZZHKDJRBRR15A7Z (multi-contributor claims); where
this document and that epic disagree, the epic's owner decisions win.

Every statement in section 1 is marked VERIFIED (read in code, config
or a ledger event) or INFERRED (absence found by search, or reasoning).

## 1. Current behaviour

### 1.1 Where tickets live

- VERIFIED. Three ledger modes, `[tickets] ref_mode`
  (crates/frob-ledger/src/config.rs:18-25, ledger.rs:28-35): `trunk`
  (default) commits to `[tickets] ref`; `branch` commits to the
  checked-out branch; `orphan` commits to `refs/heads/<[tickets] branch>`
  (default `frob-tickets`) in the human layout, while `ref` stays the
  code base that `work` branches from and `land` advances
  (tickets.md:33-38).
- VERIFIED. Orphan mode is implemented and tested end to end:
  `frob ticket branch init` (crates/frob-ledger/src/branch.rs),
  `ticket migrate --to-branch`, the doc-tested guide
  docs/guides/ticket-branch.md, and the merge-driver test
  crates/frob/tests/it/merge_driver_branch.rs. It is opt-in, not default.
- VERIFIED. This repository is NOT on it: frob.toml:112-119 sets
  `ref = "refs/heads/experimental"`, `ref_mode = "trunk"`; no
  `frob-tickets` ref exists locally or on origin; 2070 ticket
  directories sit under `tickets/<ULID>/`. That is why every ledger verb
  makes a `tickets(<verb>): ~ID` commit on `experimental`.
- VERIFIED. Ticket 01M3ZX82YQ43A8SWS4F128J4NT ("Migrate this
  repository's tickets ... to the ticket branch") closed `done` on
  2026-10-10 when the migrate VERB landed; the flip itself never ran.
  Its own notes list what the flip still needs (frob.toml ref, the
  worktree crate's raw `[tickets]` reader, `.gitattributes`, creating
  the local branch on fresh clones, CI and goway `with_refs`). Its
  priority was raised because 290 of 456 `experimental` commits were
  ledger commits that move the land base. Open blocker:
  01M4HQ2T0QV27JHJP0DRF7ZZHA (triage and scrub refuse the ticket-branch
  layout).

### 1.2 Events and merging

- VERIFIED. One immutable TOML file per event, named by ULID
  (`tickets/<id>/events/<ulid>.toml`, or `.events/<ULID>/` on the ticket
  branch); `ticket.md` frontmatter is a cache of the fold
  (tickets.md:79-119). Disjoint paths mean concurrent writers never
  conflict on events; the only conflict surface is the frontmatter,
  which `frob merge-driver` resolves by unioning events and refolding
  (tickets.md:189-201, crates/frob/src/ticket/merge_cmd.rs). Ledger
  commits are built from the ledger ref's tree, never the index, and
  advance the ref by CAS with `[git] cas_retries` (tickets.md:207-221).
- VERIFIED. ULIDs remove the id-allocation problem the claims epic
  discusses for v1 counters: offline clones mint non-colliding ids.

### 1.3 Leases and claims

- VERIFIED. A lease is a local file `<common_dir>/frob/leases/<ULID>.toml`
  under a lock file; "Leases are single-clone: other clones see only the
  ledger CAS and rule SCOPE001" (crates/frob-lease/src/lib.rs:4-11). TTL
  7200 s after the last renewal (crates/frob-lease/src/config.rs:63-65).
- VERIFIED. The only cross-clone trace of a claim is the `in-progress`
  transition event `frob work` appends, whose reason carries the lease
  summary (crates/frob-worktree/src/work.rs:267-285). Others see it only
  after it is pushed and they fetch. The `lease` event kind is in the
  design table but no verb produces it (crates/frob-ledger/src/event.rs:4).
- VERIFIED. `frob lease list` lists "the live scope leases of this
  clone" only (`frob lease --help`).

### 1.4 Remotes: fetch and push

- INFERRED (search found no fetch call in any frob crate; gob-git only
  spawns `git push`, crates/gob-git/src/fallback.rs:170-184). frob never
  fetches. `work` creates the worktree from and merges the LOCAL base
  (crates/frob-worktree/src/work.rs:452-489); `doable` reads the local
  index. A stale clone silently offers tickets someone else already took.
- VERIFIED. The only push is `land --push`
  (crates/frob-land/src/verb.rs:42), and the train pushes once per drain
  (crates/frob-land/src/train.rs:831-833). A push failure is a warning:
  "landed locally but the push failed" (crates/frob-land/src/land.rs:1506-1520).
- VERIFIED. Ordering bug: `finish` pushes the base (land.rs:501-503)
  BEFORE `close_after_advance` writes the `land` and close events
  (land.rs:504, 537-559). In trunk mode the pushed base therefore lacks
  the `tickets(land)` and `tickets(close)` commits until some later push;
  in orphan mode frob never pushes `frob-tickets` at all. This
  repository's latest land event records `pushed = false`.
- VERIFIED doc drift: tickets.md 2b cites a `[land] push` key; the
  `[land]` table (docs/reference/config.md) has none. It also says
  `ticket doctor` lists unpushed ledger commits; INFERRED unimplemented
  (no `unpushed` logic in frob-ledger or the doctor).
- VERIFIED. `ticket branch init` used to refuse when only
  `origin/frob-tickets` existed; ~P418XYE removed that refusal: `init`,
  `ticket doctor --fix` and `branch init` now adopt (fetching, depth 1 when
  shallow) the origin branch. No verb merges a diverged local and remote ticket branch.

### 1.5 Code branches and the tie to tickets

- VERIFIED. `work` creates `ticket/<handle>`; `land` advances the base
  by `merge --ff-only` or CAS `update-ref` to the ticket tip
  (land.rs:1360-1404). A base that moved is merged into the ticket
  branch (`chore(merge): sync <base>`) and rechecked, never rebased, so
  ticket-branch commit ids survive the land.
- VERIFIED. The `land` event records `commit`, `branch`, `base_ref`,
  `pushed`. Evidence events record provider, ref, digest, output and
  time but NO code commit (sample event under
  tickets/01M3ZX81T4DCMKXZXNSR5QDX7H/events/). Nothing checks that
  evidence was measured on the code that landed.
- VERIFIED. The mirror (mirror.md 2-3) is one-way ledger to GitHub
  Issues, run as a scheduled job; leases appear as a read-only body
  section. It gives humans visibility, not a claim channel; tracker
  edits come back only as `proposal` events.

## 2. Gaps against the goals

| Goal | Gap |
|---|---|
| Claims visible across people and agents | Leases are per clone; the `in-progress` event travels only by manual push/fetch; no remote CAS, so two clones can both `work` one ticket. |
| Freshness | No fetch anywhere; `doable` and `work` never say how old their view is; "nothing claimed" and "never fetched" look identical (the epic calls this the dominant defect class). |
| Offline | Works offline today, but by accident: there is no policy for what must refuse (taking a claimed ticket, stealing) and what may proceed with a warning. |
| Ticket-branch conflicts | No sync verb; a diverged `frob-tickets` needs a manual merge in a checkout that orphan mode never has. Generated files (README, indexes, reindex moves) are a second conflict surface besides frontmatter. |
| Code-branch conflicts | Handled locally (base merge, lockfile regeneration) but only against the local base. |
| Code and ledger in step | Push before the ledger step; orphan mode never pushes the ledger; no repair for "code on origin, ticket still open" or the reverse. |
| Evidence binding | Evidence carries no code sha; a squash or rebase on the hosting side breaks the `land` event's `commit` tie and nothing notices. |
| Identity | Actor is `git user.name` at call time (01M4M27EPRF0RAN4YBEA2J8C05); a changed identity strands a lease, worse across machines. |

## 3. Recommended design

### 3.1 When to use which mode

- `orphan`: the default whenever more than one clone (person, machine
  or goway helper that writes) touches the ledger, or when ledger churn
  slows lands. This repository qualifies on both counts: flip it.
- `trunk`: a single person in a single clone; simplest, no sync needed.
- `branch`: forks and contributors without push access; ticket events
  travel inside the PR and are unioned on merge (claims are unavailable
  to them, matching the epic's "claiming requires push access").

Tickets stay "separate from the code but tracked like code": one
orphan branch, ordinary commits, ordinary push and fetch, protected
against force pushes. Code branches never carry ledger commits.

### 3.2 Three kinds of ref, three owners

| Ref | Holds | Writer | Conflict rule |
|---|---|---|---|
| `refs/heads/frob-tickets` | events, folded ticket files, generated pages | frob only (CAS), pushed by `frob refresh` | union of event files, refold, regenerate derived files; never last-writer |
| `refs/heads/ticket/<handle>` on origin | the code of one ticket; its existence IS the claim | the claimant | create-only push; never force-pushed by anyone else |
| `refs/heads/<base>` | landed code | `land` | ff or CAS push; on non-ff fetch, merge base into the ticket branch, recheck, retry |

### 3.3 Claims: the branch is the claim (epic owner decisions)

- `frob work` creates `ticket/<handle>` at the base tip and publishes it
  with a create-only push (`--force-with-lease=refs/heads/ticket/<h>:`
  with an empty expected value, so the push fails if the ref exists).
  That push is the linearization point. The winner then appends a
  `lease` event (op `take`, actor, clone id, agent label, branch name,
  observed oid) and pushes the ledger. The local lease file stays the
  intra-clone mutual-exclusion layer, unchanged.
- `doable` on every clone excludes a ticket when EITHER the ledger shows
  a live claim OR origin has `ticket/<handle>` (an unrecorded claim
  whose ledger push has not arrived yet).
- The claim record names its branch, so a later handle lengthening
  never breaks the mapping.
- An epic claim covers its open leaves; `doable` excludes claimed
  subtrees from the cached view, offline.
- Divergent claims (two clones claimed one ticket while apart): origin
  decides; whoever's create-only push succeeded holds it. The loser's
  sync reports "claim lost to <actor> at <oid>", pushes the loser's
  commits to `parked/<handle>-<n>` (never deletes or rewrites), writes
  a comment event and suggests `requeue`.
- Steal and take-a-leaf-from-a-claimed-epic need a FRESH remote read.
  Working anyway without claiming is the epic's escape valve: a reason,
  scoped, expiring, surfaced at land.
- Allocation is atomic: `frob work --next` picks and claims in one
  step, retrying on a lost race.
- Liveness and eviction: section 4. Freshness: section 5.

### 3.4 Land and push ordering

Invariant: origin never shows a ticket `done` whose code is not on
origin's base. The reverse (code merged, ticket still open) is a
tolerated transient that sync repairs.

1. Sync (section 5). If origin's base moved, merge it into the ticket
   branch and recheck (existing `recover_stale`).
2. Push the base by CAS against the fetched oid. Non-ff: back to 1
   under `--wait`. Failure (offline, rejected): the land is local,
   `land` event `pushed = false`, the ticket branch and its remote copy
   are KEPT so the land can be redone onto a moved origin later.
3. Append `land` and close events; push `frob-tickets` by CAS with
   union-merge retry.
4. If 3 fails after 2 succeeded: any later sync or doctor sees "ticket
   branch tip reachable from origin base, ticket not done" and completes
   the close idempotently (keyed by ticket and commit). A queued local
   land is always pushed base first, ledger second.
5. Delete the remote `ticket/<handle>` only after both pushes succeed.

Trunk mode keeps code and ledger on one ref: push after the ledger
step, so one push carries both.

### 3.5 Tying code to tickets

- Evidence records gain `head` (the code commit measured). Land warns
  when a bound record's `head` is not an ancestor of the landed tip
  (a force push or rebase after measuring).
- frob lands are ff or merge, never squash or rebase. frob's own
  base-sync merges carry a `Frob-Sync: base` trailer so activity
  detection can ignore them. Hosting-side squash or rebase merges are
  detected by a `Frob-Ticket: <ULID>` trailer or patch id and recorded
  as a land.

## 4. Abandoned claims: inactivity eviction

The failure this section exists for: someone claims a ticket and then
forgets it, never starts, or goes on leave, and the ticket starves
while everyone's agents skip it.

### 4.1 Configuration

```toml
[claims]
idle_days = 3              # human claims; 0 = never evict
count = "all"              # calendar days; "weekdays" is available but not the default (decision D-3)
agent_idle_hours = 4       # claims whose holder is an agent (FROB_AGENT set at claim time)
warn_at = [0.5, 0.8]       # fractions of the window that warn
soft_max_windows = 2       # soft-only activity may extend a claim at most this many windows in a row
max_hold_days = 30
paused_max_days = 14       # blocked, in review or queued: pause at most this long
evict_human = "auto"       # "auto" (decision D-4) or "confirm" (TTY prompt or --yes --reason)
evict_agent = "auto"       # work --next may evict idle agent claims without asking
evict_rate = 5             # evictions one actor may perform per day
bot_identities = ["*[bot]", "github-actions*"]

[claims.class]             # per class of service; overrides idle_days
expedite = 1
intangible = 7
```

Resolution order: ticket field `claim_idle_days` (a `field` event, so
it is audited) > `[claims.class]` > agent or human default. `0` at any
level means never evict.

### 4.2 What counts as activity

| Signal | Kind | Notes |
|---|---|---|
| a new oid of origin `ticket/<handle>` containing at least one commit that is non-empty (tree differs from first parent), not authored by a bot identity, and not a `Frob-Sync` merge | hard | force pushes count if they bring such a commit not seen before |
| an `evidence` event by the holder | hard | |
| a `comment`, `field`, `link` or `transition` event by the holder | soft | |
| `frob claim touch <t> --note TEXT` (writes `lease` op `renew`) | soft | the explicit heartbeat; agents' harness runs it |
| an empty commit | soft | |
| events by other people, mirror proposals, reindex, doctor scrubs, bot or CI commits, base-sync merges | none | |

Soft activity resets the clock, but at most `soft_max_windows`
consecutive windows may pass on soft activity alone; then only hard
activity, a hold or a pause keeps the claim. This is the epic's "a
heartbeat alone must not hold a claim indefinitely".

Pauses (the clock stops, capped at `paused_max_days`): an open
`blocked-by` link to a ticket not done; queued on the land train
(`--enqueue-only`); a review requested and not answered; an unanswered
`question` comment addressed to someone else; a recorded land attempt
refused by base CI. Blocked is not abandoned, but a blocked claim held
by an absent person still starves its ticket, hence the cap.

### 4.3 Judging staleness without trusting clocks

- Each clone keeps `<common_dir>/frob/claims-observed.toml` (shared by
  its worktrees): per claim, the latest activity key (oid or event
  ULID) and the LOCAL time this clone first observed it. Idle is local
  now minus that, counted per `count`. Remote `at` fields and commit
  dates are displayed, never compared.
- Consequence: a clone that was away sees old activity as new and errs
  toward not evicting. A fresh clone has no observations; it may evict
  only by the fallback: remote dates older than TWICE the window, plus
  human confirmation.
- A local clock that jumps backwards clamps to zero; a forward jump can
  only make one evictor early, and eviction re-verifies by CAS (4.5).
- Hold end dates are absolute instants (end of the given day in the
  writer's timezone, stored UTC); days of skew do not matter at
  day-scale windows. Weekday counting uses the observer's timezone; two
  observers differ by hours at most.

### 4.4 Warnings

| Fraction | Holder sees (their next verb or session-start hook) | Others see |
|---|---|---|
| 50% | `W-CLAIM-IDLE: ~X idle 1.5 of 3 days; push, comment, or frob claim touch ~X --note ...; going away? frob claim hold ~X --until DATE --reason ...` | nothing |
| 80% | same, marked urgent, once per verb | board and doable: `~X evictable in 14h` |
| 100% | `~X evictable now` | doable lists it as `evictable (held by A, idle 3.2d)` below plain todo |

Holders see one aggregated line per verb, not one per ticket; `frob
claim notices` lists them; acknowledging silences until the next
threshold.

### 4.5 Who evicts, and the eviction protocol

Nobody evicts in the background: sync, doable and board only REPORT.
Eviction happens on an explicit act:

- `frob claim evict ~X --reason TEXT` (human; prompts on a TTY, or
  `--yes`), or
- `frob work ~X` on an evictable ticket (asks the same confirmation for
  a human-held claim), or
- `frob work --next` when `evict_agent = "auto"` and the claim is an
  agent's.

Preconditions: online, a fetch inside this command, the evictor's own
observed idle at or past the window (or the fallback), not held, not
paused, under `evict_rate`, not under the flap guard (4.7), not in CI.

Steps, ordered so a crash anywhere is safe:

1. Park: create-only push of `parked/<handle>-<n>` whose tip is ONE
   additive metadata commit (no tree change; message names evictor,
   holder, observed oid X, idle, window, reason) with first parent X.
   The holder's work is untouched and the ref is self-describing.
2. Linearize: delete origin `ticket/<handle>` with
   `--force-with-lease=refs/heads/ticket/<handle>:X`. If it fails
   because the tip moved, the holder is alive: delete the parked ref,
   report `E-CLAIM-ACTIVE`, stop. If the ref is already gone, another
   evictor won: drop the parked ref, report `already evicted`.
3. Record: one ledger commit with `lease` op `evict` (holder, clone,
   evictor, X, parked ref, idle, window, reason), the `in-progress` to
   `todo` transition and a comment naming the previous holder and the
   recovery command; push by CAS.
4. A crash between 2 and 3 leaves "ticket in-progress, branch absent,
   parked ref present": every sync recognises that state and completes
   step 3 from the metadata commit, attributing it to the evictor.

Then the evictor (or anyone) claims normally; `frob work ~X --from
parked/<handle>-<n>` starts from the parked work.

### 4.6 The holder comes back

- frob refresh on the holder's clone fetches before it pushes, sees the
  `evict` event naming them, and does NOT push to `ticket/<handle>`;
  it pushes their new local commits to `parked/<handle>-<n+1>` and
  shows `W-CLAIM-EVICTED: ~X evicted by B on <local date> after 3.2
  idle days; your work is safe at parked/...; frob work ~X --reclaim`.
- `--reclaim` with the ticket still `todo`: re-claims, restores the
  branch from the newest parked ref, writes `lease` op `reclaim`.
- If someone else already holds it: refused with the holder named;
  coordinate, or use the escape valve.
- `land` from an evicted local lease refuses with the same remedy.
- A raw `git push` of the old branch after eviction: if nobody
  re-claimed, it recreates `ticket/<handle>`; sync sees a branch for an
  evicted todo ticket with new hard activity by the old holder and
  auto-reclaims for them (they were not gone after all). If someone
  re-claimed, git rejects it as non-fast-forward and sync explains.

### 4.7 Holds, agents, flapping and abuse

- `frob claim hold ~X --until 2026-11-03 --reason "on leave"` writes
  `lease` op `hold`; the clock stops; all clones show "held until".
  Holds over `max_hold_days` need a fresh reason each time and are
  listed on the board. At expiry the clock restarts from zero with
  normal warnings. `frob claim resume` ends a hold early.
- Agent claims: the window is `agent_idle_hours`; the agent harness
  runs `frob claim touch` from its hook while the session lives; a dead
  agent stops touching and is evictable in hours; soft-only touching
  is capped like any heartbeat (the 19-hour polling daemon case). A
  human taking over an agent worktree re-claims (`lease` op `rekind`),
  which switches to the human window.
- Flap guard: after a reclaim the claim cannot be evicted for one full
  window; a second eviction of the same holder on the same ticket
  within 14 days always needs human confirmation and is flagged.
- Griefing: evictions are rate limited, always parked, always
  recorded, need the evictor's own observed window, and are reversible
  by `frob claim restore ~X` (holder or anyone, while nobody else has
  started) with a reason. A collaborator with push access who deletes
  branches by hand is outside frob's power (section 7).

## 5. Freshness without remembering

Goal: no human or agent has to remember to sync. Running any coordinating
verb is equivalent to having pulled within the TTL.

### 5.1 What "up to date" means

| Object | Up to date when | Other states |
|---|---|---|
| ledger (`frob-tickets`) | local contains origin's tip as of a probe younger than `[sync] ttl` | `stale` (probe older than ttl), `ahead` (unpushed local events, normal, pushed by sync), `diverged` (sync merges it), `unknown` (never probed), `local-only` (no remote) |
| base branch | local `refs/heads/<base>` equals origin's | `behind` (sync fast-forwards it when not checked out, or checked out clean), `ahead` (local lands not pushed), `diverged` (refuse land; section 6) |
| ticket branch vs base | origin base is an ancestor of `ticket/<h>` | `behind base by N` (warn on check --ticket; land merges it anyway) |
| ticket branch vs its remote copy | equal | `ahead` (WIP, pushed by sync), `behind` (pushed from another clone: fast-forward if clean, else warn), `diverged` (warn, never auto-merge code; refuse land) |
| claims view | probe younger than ttl | as for the ledger |

### 5.2 Mechanism and budget

State lives in `<common_dir>/frob/sync.toml` (one per clone, shared by
worktrees): last probe time, result class, remote oids, backoff.

1. Probe: one `git ls-remote <remote> refs/heads/frob-tickets
   refs/heads/<base> 'refs/heads/ticket/*' 'refs/heads/parked/*'`,
   timeout `[sync] probe_timeout` (2.5 s), `GIT_TERMINAL_PROMPT=0` and
   SSH `BatchMode=yes` so it can never prompt or hang. Unchanged oids:
   record the time, done.
2. Fetch: only the changed refs, explicit refspecs, timeout
   `fetch_timeout` (10 s). Git updates refs only on success, so a
   killed fetch changes nothing.
3. Integrate: plumbing union merge of the ledger (event paths unioned,
   changed tickets refolded, derived paths and pages recomputed, one
   two-parent commit; cost proportional to changed paths, not to ticket
   count); fast-forward the local base when safe; update
   claims-observed.
4. Publish: CAS push of queued ledger commits; push WIP of this
   clone's claimed ticket branches when `push_wip = true` (default),
   which is what keeps a working holder visibly alive.

Locks: `sync.lock`, non-blocking; a second sync in the same clone
returns "sync running" and uses the cache. Sync takes the land lock
non-blocking for base work and skips the base if a land holds it.

Budget: read verbs never touch the network; they stat `sync.toml` and,
when it is older than ttl, start a detached `frob refresh --background
--quiet` (one spawn per ttl per clone; this adds a line to git-io.md
section 3). Mutating verbs run the probe in the foreground within
`foreground_budget` (3 s), then fall back to the cache. Failures back
off exponentially (ttl doubling to 1 h) and reset on success.

### 5.3 Per verb

| Verb | Network | On failure or stale view |
|---|---|---|
| check, test, format, ack, explain, tour | never | nothing about freshness |
| check --ticket | never (cache) | info: `ticket/<h> is N behind <base>`, `origin <base> is N ahead (as of 7m)` |
| ticket show, list, board, stats | background kick | footer `tickets as of 2h ago (offline)` only when older than `warn_after` (1 h) |
| ticket new, update, comment, evidence | background kick | events queue; pushed by the next sync |
| doable | foreground probe | cache plus `W-SYNC-*`; past `stale_error` (24 h) each row is marked `may be taken` |
| work ~X | foreground sync, then create-only push | offline and cache younger than `stale_error` and not claimed in cache: proceed with an unpublished claim and `W-SYNC-OFFLINE`; older: refuse `E-SYNC-STALE` (remedy `frob refresh`, or `--offline --reason`); steal, evict, take-a-leaf: refuse |
| work --next | foreground sync | as work; never evicts offline |
| land | foreground sync | offline: land locally, `W-LAND-LOCAL` (pushed later, base first); ticket branch diverged from its remote, or base diverged: refuse `E-SYNC-DIVERGED` |
| doctor | foreground probe | full freshness table; never fails |
| frob refresh --status | never | one line from the cache for shell prompts (`frob:2h-stale 1-conflict`), under 10 ms |
| frob refresh [--quiet] | always | exit 0 ok, 3 retryable (offline, auth, rate limit), 1 needs action (diverged, ledger conflict) |

Message class: `<CODE>: <what> as of <age> (<cause>). <command to
fix>. <how to silence>`, for example `W-SYNC-OFFLINE: ticket view is
3h12m old (probe timed out after 2.5s). Run frob refresh when online.
Silence with [sync] warn_after.` Silencing is config, never an
environment variable a session inherits. Ranked, highest first:
diverged branch, ledger field conflict, auth failure, rate limited,
offline, base not fast-forwardable (dirty checkout), stale.

### 5.4 Hooks, so nobody has to remember

- `frob init` installs git `post-checkout` and `post-merge` hooks that
  run `frob refresh --background --quiet` (returns at once; no-op inside
  ttl). No `pre-push` hook: frob's own pushes set `FROB_SYNC_INNER` and
  would recurse.
- `frob agent sync` registers a session-start hook in each agent home
  running `frob refresh --quiet` in the foreground (3 s budget) and
  printing claim notices, evictions and conflicts to the agent.
- Loops and cron: `frob refresh --quiet`, using its exit codes.
- CI sets nothing: `CI` disables background sync and every claim verb;
  the workflow fetches the ledger ref as today.

### 5.5 Ledger conflicts are never dropped

Event files never conflict. A concurrent pair of `field` events on one
field (the fold already reports these) becomes a `ledger-conflict`
entry in the sync envelope, a board banner and a doctor finding until
someone resolves it with `ticket update`; `ticket show` marks the field
`conflict: a | b`. Generated pages and derived paths are recomputed,
never merged. A merge that would push a ticket failing the fold check
(corrupt or hand-edited event) is refused: `E-SYNC-LEDGER-INVALID`
naming the file; the rest of the queue still pushes.

## 6. Human scenarios and adversarial pass

Ticket column: proposed tickets are `DT` numbers from section 8;
`~` handles are existing tickets. "Not handled" rows are listed again in
section 7 with the reason.

### 6.1 Everyday people

| # | Trigger | What happens | User sees | Fix | Ticket |
|---|---|---|---|---|---|
| 1 | Laptop closed Friday to Monday | no activity observed; with `count = weekdays` the weekend does not count | nothing; others at most a 50% warning to the holder only | none needed; with `count = all` an 80% warning appears to others Sunday | DT12 |
| 2 | Flaky wifi | probes time out; cache used; WIP not pushed, so others see the claim idle | holder: `W-SYNC-OFFLINE` and `3 unpushed commits; others see ~X idle 2.1d` | eviction needs the evictor online AND a CAS on the tip, and the next successful sync pushes WIP | DT08, DT13 |
| 3 | Holder force-pushes the ticket branch | new oid with new commits counts as activity | nothing | evidence measured before the rewrite warns at land | DT11, DT20 |
| 4 | Two people share one git identity | claims carry clone id; activity from either counts | `W-CLAIM-IDENTITY: two clones claim as X` | set distinct identities (`~A2J8C05`) | DT10 |
| 5 | Claim on machine A, work on machine B | B runs `frob work ~X`: same actor, so resume: fetch the remote branch, new local lease, `lease` op `move` | A later sees `claim now active from clone B` | none | DT10 |
| 6 | Blocked on review, CI or another person | pause; clock stops up to 14 days | `paused: blocked by ~Y (day 4 of 14)` | past the cap: warnings resume; hold if longer | DT14 |
| 7 | Long research ticket, few commits | comments and touches are soft activity, capped at 2 windows | 50/80% warnings explaining soft cap | evidence or a commit of notes, `claim_idle_days`, class `intangible`, or a hold | DT11, DT12 |
| 8 | Claimed offline, branch never pushed | claim unpublished; nobody else sees it | holder: `claim unpublished for 2h; others may take ~X` | next sync publishes; if lost, loser flow (3.3) | DT10 |
| 9 | Ledger event pushed, branch push failed | ticket in-progress on origin with no branch | others: `claim without branch`, idle runs from first sight | sync retries the branch push; evictable normally; nothing to park | DT10, DT13 |
| 10 | Branch pushed, ledger push failed | unrecorded claim | doable excludes it on all clones | sync writes the missing `lease` event | DT10 |
| 11 | Person left the team | claims go idle and become evictable | evictable rows | `frob claim evict --holder A --reason "left"`: one confirmed batch, all parked | DT13 |
| 12 | Long leave | hold | `held until 2026-11-03 (on leave)` | at expiry: normal clock and warnings | DT14 |
| 13 | CI or bot pushes to the ticket branch | bot authors excluded | nothing | add the identity to `bot_identities` if unknown | DT11 |
| 14 | Holder pushes an empty commit daily to keep the claim | soft activity, capped | 80% warning after the cap | real work, hold, or let it go | DT11 |
| 15 | Clock skew between machines | only local first-observation times compared | nothing | none | DT11 |
| 16 | Holder and evictor in different timezones | windows are durations; weekday counting differs by hours | nothing | none | DT12 |
| 17 | New contributor clones and tries to evict | no observation history | `E-CLAIM-UNOBSERVED: observed for 0 of 3 days` | wait, or the 2x-window fallback with confirmation | DT13 |
| 18 | Agent dies mid-ticket | touches stop; evictable after 4 h | others: evictable agent claim | `work --next` evicts it automatically and parks the work | DT15, DT16 |
| 19 | One bot account runs many agents | claims keyed by actor, clone id, worktree and agent label | per-agent claims | none | DT10, DT15 |
| 20 | Agent works under the human's git identity | commits indistinguishable; window kind fixed at claim time | nothing | a human taking over re-claims (`rekind`) | DT15 |
| 21 | Pair programming, co-author trailers | any non-bot commit counts for the claim | nothing | none | DT11 |
| 22 | Git identity renamed or rotated | same clone id continues the claim with a warning; another clone is another holder | `W-CLAIM-IDENTITY` | `[identity] aliases` | ~A2J8C05 |

### 6.2 Races

| # | Trigger | What happens | User sees | Fix | Ticket |
|---|---|---|---|---|---|
| 23 | Two people `work` one ticket at once | one create-only push wins | loser: `E-CLAIM-LOST to A` | loser takes another (`work --next` retries) | DT10, DT16 |
| 24 | Two evictors at once | both park; only one CAS delete succeeds | loser: `already evicted by A` | loser's parked ref removed | DT13 |
| 25 | Evict vs the holder's late push | CAS delete fails because the tip moved | evictor: `E-CLAIM-ACTIVE` | none; the holder is alive | DT13 |
| 26 | Holder's raw push after eviction, nobody re-claimed | branch recreated; sync auto-reclaims for them | holder: `reclaimed ~X` | none | DT13 |
| 27 | Holder's raw push after someone re-claimed | git rejects non-fast-forward | holder: git error; next sync explains and parks their commits | coordinate or escape valve | DT13 |
| 28 | Two syncs in one clone | `sync.lock`; second uses the cache | `sync running` (quiet in background) | none | DT05 |
| 29 | Syncs on two clones | ledger CAS push; the loser re-fetches, re-merges, retries | nothing | retries exhausted: exit 3, next ttl | DT06 |
| 30 | Sync during land | sync skips base work while the land lock is held | nothing | none | DT06 |
| 31 | `work --next` by many agents at once | each attempt is a create-only push; losers retry the next candidate | nothing | none | DT16 |
| 32 | Evict and reclaim alternate (flapping) | flap guard: no re-eviction for one window; second eviction needs a human | board flag | none | DT19 |

### 6.3 Partial failures and crashes

| # | Trigger | What happens | User sees | Fix | Ticket |
|---|---|---|---|---|---|
| 33 | Base push ok, close-event push failed | origin: code merged, ticket in-progress | `W-LAND-LEDGER-PENDING` | sync completes the close idempotently | DT01, DT21 |
| 34 | Base push failed after a local land | `pushed = false`; branch kept | `W-LAND-LOCAL` | sync pushes base then ledger; base diverged: re-land (row 52) | DT01, DT21 |
| 35 | Crash after park, before delete | parked ref left, claim intact | nothing | sync deletes a parked ref whose metadata commit has no matching delete after a day | DT13 |
| 36 | Crash after delete, before the evict event | in-progress, no branch, parked present | nothing | sync completes step 3 from the metadata commit | DT13 |
| 37 | Fetch killed mid-way (slow remote) | refs unchanged | `W-SYNC-TIMEOUT` | backoff, next ttl | DT05 |
| 38 | Ledger push of one bad ticket rejected by the integrity gate | rest of the queue pushes | `E-SYNC-LEDGER-INVALID <file>` | `ticket doctor --fix` or reconcile | DT06 |

### 6.4 Repository shape

| # | Trigger | What happens | User sees | Fix | Ticket |
|---|---|---|---|---|---|
| 39 | No remote | sync off, `local-only`; no freshness warnings; claims are local leases only | `doctor`: local-only | add a remote | DT05 |
| 40 | Several remotes | only `[sync] remote` (default `origin`) is authoritative | nothing | set the key | DT05 |
| 41 | Shallow clone | the fold needs only the current ledger tree; a merge needs a base, so sync deepens only `frob-tickets` | nothing | none | DT02, DT06 |
| 42 | Fork contributors, PRs from forks | no push access, so no claims (owner decision); `ref_mode = "branch"` carries events in the PR | `E-CLAIM-NO-PUSH` | maintainers claim on their behalf | not handled (7) |
| 43 | Host forbids deleting `ticket/*` | eviction cannot CAS delete | `E-CLAIM-PROTECTED` | fallback: the ledger push is the CAS; the new claimant uses `ticket/<h>-2` | DT13 |
| 44 | `frob-tickets` requires reviewed PRs | ledger pushes rejected | `E-SYNC-PROTECTED` | orphan mode needs direct push; use branch mode | not handled (7) |
| 45 | Force push disabled everywhere | frob never force-pushes; create-only and delete leases work | nothing | none | DT10 |
| 46 | Squash or rebase merge in the hosting UI | the ticket tip is never in base | sync: `~X merged by squash` via trailer or patch id | recorded as land | DT22 |
| 47 | Host auto-deletes merged head branches | branch gone after a hosting merge | as row 46 | as row 46 | DT22 |
| 48 | Remote ticket branch deleted by hand, no land | claim without branch | as row 9 | as row 9 | DT13 |
| 49 | Default branch renamed on the host | probe finds no `<base>` | `E-SYNC-NO-BASE: origin has no experimental; origin HEAD is main` | update `[tickets] ref` | DT05 |
| 50 | Linked worktrees | one sync state and one probe per clone (common dir) | nothing | none | DT05 |
| 51 | Submodules with their own frob ledgers | each repository syncs independently | nothing | none | not handled (7) |
| 52 | Offline for weeks, then reconnect with local lands | base diverged from origin | one summary: `N local lands not on origin; M claims evicted; K conflicts` | `frob land --relaunch ~X` re-lands each kept branch onto origin; frob never rebases | DT21 |

### 6.5 Data

| # | Trigger | What happens | User sees | Fix | Ticket |
|---|---|---|---|---|---|
| 53 | Concurrent edits of one field | fold reports a concurrent pair | `ledger-conflict` banner, `conflict: a or b` in show | `ticket update` resolves | DT06 |
| 54 | Hand-edited `ticket.md` frontmatter | refold overwrites the cache; doctor reports drift | doctor finding | none | existing doctor |
| 55 | Corrupt or hand-edited event file | integrity gate refuses to push it | `E-SYNC-LEDGER-INVALID` | doctor | DT06 |
| 56 | Two clones reindex one ticket differently | paths are recomputed from the fold in the merge | nothing | none | DT06 |
| 57 | Tens of thousands of tickets | sync cost follows changed paths; index rebuilds incrementally | nothing | perf test | DT23 |
| 58 | Claimed ticket dropped, closed as duplicate or merged by someone else | close guard requires a reason when a live claim exists; the claim ends; work parked | holder: `~X dropped by B: claim released, work parked` | none | DT13 |
| 59 | Claimed ticket split into children | an epic claim covers new leaves; a task claim does not | holder notified | claim the children | DT17 |
| 60 | Epic claimed while a child is claimed by someone else | the child's claim stands; the epic claim covers the rest | both see each other's claim | none | DT17 |
| 61 | Ticket handle lengthens after a collision | the claim stores the branch name | nothing | none | DT10 |
| 62 | Ticket moved to another epic while claimed | identity by ULID; epic claim coverage recomputed | warning if it leaves a claimed epic | none | DT17 |

### 6.6 Policy

| # | Trigger | What happens | User sees | Fix | Ticket |
|---|---|---|---|---|---|
| 63 | Ticket in review | pause (cap 14 days) | `paused: review requested of B` | reviewer acts | DT14 |
| 64 | Blocked on an external party (vendor, legal) | no ledger signal | warnings | `blocked-by` an external ticket, or a hold with a reason | DT14 |
| 65 | Hold expires unnoticed | clock restarts at zero; 50% warning later | warnings | extend the hold | DT14 |
| 66 | Notification spam after a long absence | one aggregated notice, acked once | one line | `frob claim notices --ack` | DT12 |
| 67 | Griefing: someone evicts colleagues' work | needs own observed window, rate limit, always parked and recorded | event on the ticket, board flag on repeats | `frob claim restore ~X` | DT19 |
| 68 | Everyone sets `idle_days = 0` | never evicts | board shows claim ages | policy for the owner | DT12 |
| 69 | Holder works the escape valve on someone else's claim | no transfer; shown at land | land: `worked over A's claim: <reason>` | none | DT18 |

### 6.7 Operations

| # | Trigger | What happens | User sees | Fix | Ticket |
|---|---|---|---|---|---|
| 70 | CI with no network for sync | `CI` disables sync and claim verbs; the workflow fetches the ledger ref | nothing | as today | DT08 |
| 71 | Air-gapped machine | local-only; `git bundle` exchange by hand | local-only | not automated | not handled (7) |
| 72 | Auth expired (SSH agent, token) | probe fails fast, never prompts | `W-SYNC-AUTH: run git fetch origin to re-authenticate` (ranked high) | re-auth | DT05, DT07 |
| 73 | Host rate limits | 429 or SSH refusal: backoff to 1 h | `W-SYNC-RATE` | none; one probe per clone per ttl keeps load low | DT05 |
| 74 | Very slow remote | hard timeouts; background fetch killed at 60 s | `W-SYNC-TIMEOUT` with age | none | DT05 |
| 75 | Detached HEAD or dirty tree | ledger is plumbing, unaffected; base fast-forward skipped when its checkout is dirty | `origin <base> 3 ahead; checkout has edits` | commit or stash | DT06 |
| 76 | Hook runs while a rebase is in progress | background sync skips base and ticket-branch pushes during an in-progress git operation | nothing | none | DT09 |

## 7. Deliberately not handled

- Fork contributors claiming (row 42): owner decision, claims need push
  access.
- Review-gated `frob-tickets` (row 44): the ledger must accept direct
  CAS pushes; such repositories use `ref_mode = "branch"`.
- Malicious collaborators with push access deleting refs or
  force-pushing: hosting protection (TICK011, ~R4JF26Z) is the defence.
- Air-gapped exchange (row 71) and submodule federation (row 51): no
  demand yet; a bundle-based sync is possible later.
- Byzantine clocks (a machine lying about time to evict): bounded by
  the CAS on the tip, the rate limit and restore, not prevented.
- Humans sharing one identity on one clone: indistinguishable by
  construction.

## 8. Phased tickets and decisions

Ordered by value; each phase ships on its own. Points are rough.
Dependencies name DT numbers or existing handles. None of these are
filed yet.

Phase 0: correctness and the flip (8 pts)

- DT01 land pushes after the ledger step (2). Trunk: one push carries
  code and close; orphan: base, then `frob-tickets`; keep the ticket
  branch until both succeed.
- DT02 fresh clones and CI get a local `frob-tickets` (2). `init` and
  `doctor --fix` create it from origin instead of refusing; shallow
  clones handled.
- DT03 fix tickets.md 2b drift (1): no `[land] push` key; doctor's
  unpushed-commit claim.
- DT04 flip this repository to `ref_mode = "orphan"` (3). Reopen
  ~128J4NT or file a successor. Depends ~RF7ZZHA, DT01, DT02.

Phase 1: automatic freshness (15 pts)

- DT05 sync state and probe (3): `sync.toml`, bounded non-prompting
  `ls-remote`, backoff, lock, `frob refresh --status`, remote and base
  validation.
- DT06 `frob refresh` integrate and publish (5): fetch changed refs,
  plumbing union merge with conflict report and integrity gate, CAS
  push, safe base fast-forward. Depends DT05, DT02.
- DT07 freshness in envelopes and the `W-SYNC`/`E-SYNC` classes (2).
  Depends DT05.
- DT08 per-verb auto-sync policy (3): background kick for reads,
  foreground for work, doable and land, `stale_error`, CI off.
  Depends DT06, DT07.
- DT09 hooks (2): git post-checkout and post-merge, agent session start
  through `frob agent sync`, loop and cron docs. Depends DT08.

Phase 2: claims and eviction (30 pts; children of ~RR15A7Z)

- DT10 publish the claim on work (5): create-only push, `lease` events
  with clone id and agent label, unrecorded-claim detection, resume on
  another clone, loser flow. Depends DT06; soft ~A2J8C05.
- DT11 activity observation (3): claims-observed state, hard and soft
  signals, bot, empty and `Frob-Sync` exclusions. Depends DT10.
- DT12 idle windows and warnings (3): `[claims]` config, class and
  ticket overrides, 50/80% warnings, aggregated notices. Depends DT11.
- DT13 eviction (5): `frob claim evict`, park, CAS delete, record,
  crash completion, holder return and reclaim, batch evict, drop while
  claimed. Depends DT12.
- DT14 holds and pauses (2): `claim hold|resume`, blocked, review,
  train and CI pauses with the cap. Depends DT12.
- DT15 agent claims (2): short window, `claim touch` from the harness,
  soft cap, `rekind`. Depends DT12.
- DT16 `frob work --next` (3): atomic allocate and claim with retry.
  Depends DT10, DT13.
- DT17 epic claims cover leaves (3): children claimed separately, split
  and move. Depends DT10.
- DT18 escape valve (2): reason, scope, expiry, shown at land. Depends
  DT10.
- DT19 eviction safeguards (2): flap guard, rate limit, `claim
  restore`. Depends DT13.

Phase 3: binding and repair (9 pts)

- DT20 evidence records carry `head`; land checks ancestry (2).
- DT21 sync and doctor repair code and ledger mismatches; `land
  --relaunch` for local lands on a diverged base (3). Depends DT06.
- DT22 detect hosting-side squash and rebase lands (2). Depends DT21.
- DT23 sync at scale: perf test at 50k tickets (2). Depends DT06.

Existing tickets this plan relies on: ~RR15A7Z (claims epic, parent of
Phase 2), ~128J4NT (repository flip), ~RF7ZZHA (triage and scrub on the
ticket-branch layout), ~A2J8C05 (stable actor identity), ~R4JF26Z
(TICK011 rulesets), ~D08W4A6 (mirror push), ~CHJYNT6 (navigation
pages), ~KYD6J5K (frob serve).

Proposed 0.533.0 cut line: Phase 0, Phase 1 and DT10 to DT14 (41
points). DT15 to DT23 (21 points) are stretch and land in 0.534.0 if
the epic stays overcommitted.

Decisions made by the owner (2026-10-20):

- D-1 all phases are filed under one epic in the 0.533.0 milestone, even
  though the milestone is overcommitted. DT15 to DT23 are the first to
  slip if it must.
- D-2 verb names must not share vocabulary: `frob claim ...` for the
  claim family (claims are not leases) and `frob refresh` for the
  ledger freshness verb, because `frob sync` collides with
  `frob agent sync`. Earlier sections say `frob refresh` after this edit.
- D-3 the idle window counts calendar days (`count = "all"`).
- D-4 human-held claims evict automatically (`evict_human = "auto"`).
  The park branch and `claim restore` are the safety net. Scenario
  rows that mention a confirmation describe the optional
  `evict_human = "confirm"` mode.
- D-5 offline `work` on an unclaimed ticket proceeds with a warning.
- D-6 this repository flips to orphan mode (DT04) ahead of the rest of
  the epic.
