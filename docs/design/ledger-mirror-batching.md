# Ledger-mirror batching (T-3550, successor to T-3544/T-3542)

## Status

DESIGN ONLY. This document does not implement batching. It specifies the
pending-queue + per-event flush design for `mirror_ledger_change_to_primary`
mirror commits, enumerates the live-fleet hazards an implementation must
close, and re-measures where the historical "41 file commits in 300" figure
actually comes from (T-3544's premise there was wrong -- see
[Re-measurement](#re-measurement-the-41-file-commits) below).

## Background

`src/frob/app/ticket_runner/_ledger_mirror.py::mirror_ledger_change_to_primary`
runs synchronously, once per ledger-mutating verb call, from ANY worktree's
process, against the SHARED primary checkout, under `ledger_lock(primary)`.
Each call: copies the ticket's ledger pathspecs from the worktree onto the
primary, then commits them there with message
`chore(tickets): mirror <command> <ticket_id> from worktree`. A fleet running
N agents each calling `ticket scope`/`body`/`evidence`/etc. against their own
worktrees produces N such commits on the primary, one per call, interleaved
with every other ledger-writing verb's own commits (`file`, `start`, `close`,
`land`, sweep-filed regressions, ...).

T-3542 measured this class of commit (`mirror` + related per-verb ledger
commits) at 109 of the last 300 main commits; T-3544 attempted to batch it
and failed the attempt (see its Failure log) because batching correctly
requires a cross-process design this document now provides, not a
same-ticket implementation pass.

## Design: pending-mirror queue + per-event flush

### Data shape

A crash-safe, append-only pending-mirror queue under the PRIMARY checkout's
own `.frob/` directory (never a worktree's `.frob/`, since the queue's
readers/flushers must all agree on one location regardless of which
worktree enqueued an entry):

```
.frob/mirror-queue/
  <monotonic-seq>-<ticket_id>-<verb>.json
```

One file per pending mirror event, NOT one shared file every writer
appends to -- a shared file forces every enqueue to take a lock across
every concurrent worktree process, which is exactly the contention this
design exists to remove. One-file-per-event makes enqueue a single atomic
`os.replace` (write to a `.tmp` sibling in the same directory, then
rename) with NO cross-worktree lock required for the enqueue step itself
(only the flush step still needs `ledger_lock(primary)`, and only for the
duration of one flush, not one call).

Each queue file's content: `{ticket_id, command, pathspecs, worktree_root,
enqueued_at, seq}`. `seq` is a monotonic counter minted from an atomic
temp-file-then-rename creation in the queue dir (no shared counter file,
same "no cross-worktree contention on enqueue" reasoning).

### Enqueue (replaces the current synchronous commit)

`mirror_ledger_change_to_primary` still does the FILE COPY onto the
primary synchronously (worktree ledger state must still land on the
primary's working tree immediately -- see [Readers](#readers-files-vs-git-history)
below for why this half cannot be deferred), but instead of committing
immediately, it writes one pending-mirror-queue entry and returns. The
working tree is updated; the COMMIT is deferred to the next flush.

### Flush events

A flush commits every currently-queued entry as ONE
`chore(tickets): sync ledger (T-a, T-b, T-c...)` commit (ticket ids sorted,
deduplicated, one line per distinct ticket if the combined subject would
exceed a reasonable length -- reuse whatever line-wrap convention
`CHANGELOG.md` fragment assembly already uses rather than inventing a
second one). Three flush triggers, matching the ticket body's own list:

1. **A land completes.** `frob ticket land` already reconciles the primary
   at the end; flushing the pending-mirror queue as part of that same
   reconciliation window means the flush commit and the land's own commit
   share the same "primary is quiescent" moment `_land.py` already
   establishes -- no new synchronization primitive needed here, only a
   new call site inside land's existing finalize step.
2. **A sweep completion.** Same reasoning: a rapid-sweep run already has a
   quiescent moment at its own end where it is safe to touch the primary.
3. **A bounded timer.** For the case where neither a land nor a sweep runs
   for a while but ledger-mirror entries are still piling up (a long
   quiet stretch of `ticket scope`/`body`/`evidence` calls with no land in
   between) -- a background flush check, gated by "oldest queued entry is
   older than N seconds", so a queue entry is never pinned indefinitely
   waiting for an event that may not come soon. This is the one genuinely
   NEW mechanism this design introduces (the other two triggers reuse
   existing quiescent points); it needs its own crash-safety story
   independent of land/sweep (see below).

### Crash-safety of the pending queue

- **Enqueue crash** (process dies between file-copy and queue-file write,
  or mid queue-file write): the `.tmp`-then-`os.replace` enqueue pattern
  means a half-written entry never becomes visible under its real
  filename -- a crash here loses at most the one pending mirror-commit
  entry for that single verb call, exactly the same durability the
  CURRENT synchronous design already has for a crash between file-copy and
  commit (T-2714's `_write_ledger_commit_repair_marker` family already
  handles that half; the same marker discipline still applies to THIS
  design's file-copy step, unchanged).
- **Flush crash** (process dies mid-flush, after committing some entries'
  files but before the commit, or after the commit but before deleting the
  consumed queue files): a flush must (a) stage every consumed entry's
  already-on-disk files (they are already copied onto the primary by each
  entry's own enqueue step, so staging is idempotent even if a prior
  flush attempt partially ran), (b) commit, (c) delete the consumed queue
  files ONLY after the commit succeeds and is confirmed
  (`git rev-parse HEAD` names the new commit). A crash between (b) and (c)
  leaves queue files on disk describing entries that are ALREADY
  committed -- the next flush must detect this (its own working-tree
  diff against HEAD for those pathspecs is empty) and delete the stale
  queue files as a no-op cleanup rather than re-committing empty content.
  This mirrors the T-2714 stale-marker-reconciliation shape
  (`_repair_stale_ledger_commit_markers`) one level up, at the queue
  rather than the single-commit granularity.
- **Concurrent flush** (two processes both decide "time to flush" at once
  -- most likely the bounded-timer trigger racing a land/sweep trigger):
  `ledger_lock(primary)` already serializes the actual commit step (the
  current design already takes this lock per mirror commit; the flush
  design takes it once per flush instead) -- the SECOND flush to acquire
  the lock re-reads the queue directory fresh after acquiring it and finds
  it already empty (or containing only entries enqueued after the first
  flush started), so it either no-ops or flushes a smaller, genuinely-new
  batch. No new locking primitive needed beyond the existing
  `ledger_lock`.

### T-3297 merge-driver reuse

T-3297's merge driver exists specifically so a torn concurrent write
against `tickets.md`/per-ticket ledger files never produces a
`MergeConflict` at land time. A flush's commit touches the SAME class of
files (ledger pathspecs) a land splice touches -- the flush commit MUST be
made using the identical merge-aware commit path `_land.py`'s own
finalize step uses (not a bare `git commit`), so a flush landing
concurrently with an in-progress `frob ticket land` on the SAME files
resolves through the T-3297 driver instead of producing exactly the
torn-merge hazard T-3297 was built to close. Concretely: the flush's
commit call should route through the same helper `_land.py` calls for its
own ledger-file commits, not reimplement a second bare-`git commit`
call site that bypasses the driver.

### Which verbs stay per-commit

Per-verb commits stay ONLY where the commit itself is the fleet's
liveness/coordination SIGNAL, not merely a ledger-content update a reader
could tolerate seeing slightly late:

- **`block`/`unblock` edges** (`blocked_by` changes): another agent's
  `doable` computation or a land's own pre-flight check may be actively
  polling for a specific block edge to clear RIGHT NOW (a worktree waiting
  on a blocking ticket to close) -- deferring this to the next flush event
  could stall a waiting agent for the full flush-interval, not just delay
  a display. These stay synchronous, one commit per block/unblock call,
  exactly as today.
- **`land`'s own commits** (the squash + the `state=done` transition) --
  land already IS the flush's own trigger point, and land's commit is the
  fleet's actual "this ticket's code reached main" signal, never
  batchable with unrelated tickets' ledger noise.
- **`start`/`close`/`fail`/`drop`/`requeue` state transitions** are
  borderline: they change `doable`'s candidate set. Per the reader
  classification below, `doable` reads FILES, not git history, so a
  flush-lagged commit does not change what `doable` reports as soon as
  the file-copy half of enqueue has landed on the primary's working tree
  -- these are SAFE to batch into the flush, since the file state (which
  is what matters for liveness) updates immediately regardless of when
  the commit itself lands.

Everything else (`scope`, `body`, `evidence`, `done-report`, and the
`mirror` commits this document is actually about) batches into the flush.

### Readers: files vs. git history

This is the hazard the ticket body calls out explicitly and it is the
crux of the whole design: a flush-lagged COMMIT is safe exactly when
every consumer that cares about the change reads the WORKING TREE FILE,
not git history, at the moment it needs the answer.

**File readers (safe to lag the commit):**
- `frob ticket doable` / lease/liveness checks -- read `tickets.md` /
  per-ticket `ticket.md` files directly off disk, never `git log`.
- `frob ticket show` / `frob check --ticket` -- same, direct file reads.
- A worktree's OWN mirrored-onto-primary state, read back by that same
  worktree's later calls in the same session -- reads the primary's
  working tree, unaffected by whether that state is committed yet.

**Git-history readers (a flush lag MUST NOT change their answer, or the
design is broken):**
- `frob ticket land`'s own ancestry/LAND-PROOF check
  (`is_ancestor_of_main`) -- this reads commits, but it only ever asks
  about a TICKET'S OWN land commit, never a mirror commit; a pending,
  not-yet-flushed mirror entry for some OTHER ticket does not appear in
  this check's query surface at all. Safe by construction, not by
  accident -- an implementation must keep it that way (no new git-history
  query should be added anywhere that expects to see a mirror commit
  before its flush).
- `TDD001`'s "was this test committed strictly after its implementation"
  check (seen firing as a WARN-only finding on this session's own lands)
  -- reads commit ORDER for `frob:tests`-bound file pairs. A flush that
  batches several tickets' mirror commits into one commit changes the
  granularity TDD001 sees (multiple tickets' file changes now share one
  commit instead of each having its own), but TDD001 is already WARN-only
  and already tolerant of same-commit pairs (see its own message text:
  "either implementation-first, or committed in the SAME commit ...
  neither of which is test-first") -- batching does not introduce a new
  failure mode here, it just makes the same-commit case more common. No
  change needed, but worth naming so a future TDD001 tightening pass
  knows this is an expected interaction, not a regression to chase.
- `CrossTicketLeakage` / scope-closure checks that look at "which files
  did THIS ticket's commit touch" -- a flush commit spanning several
  tickets is, BY DEFINITION, a multi-ticket commit. Any check that
  currently assumes "one commit == one ticket's change" for ledger-mirror
  commits specifically must be updated to treat a flush commit's subject
  line (`chore(tickets): sync ledger (T-a, T-b, T-c...)`) as declaring
  MULTIPLE tickets' worth of legitimate ledger-only changes, the same way
  it presumably already tolerates `frob ticket land`'s own multi-file
  squash commits for one ticket. This is the one reader this design
  cannot claim "safe by construction" for -- it needs an explicit
  allowlist/pattern update, named here as an implementation-ticket line
  item, not asserted away.
- Any external tooling/dashboard that greps `git log` for
  `chore(tickets): mirror <verb> <ticket_id>` by the OLD per-commit
  message shape (none identified in this repo's own `src/`/`tests/`/
  `scripts/` at design time, but named explicitly so the implementation
  ticket's own grep-for-consumers step has a documented starting
  assumption to falsify, not a silent one).

## Re-measurement: the 41 "file" commits

T-3544's body assumed the 41 non-mirror "file" commits (of its measured
109+41 = 150 of 300) were largely SWEEP-FILED regression tickets -- i.e.,
that a single sweep run could file many tickets in a loop, each getting
its own commit, and that this loop was a batching target the same shape
as the mirror-commit problem. T-3544's own Failure log already found this
premise wrong at the code level (`_file_regression_ticket`'s two call
sites each file AT MOST ONE ticket per sweep run). This document
re-measures against the actual commit history to confirm and quantify.

**Method:** `git log --oneline -300 main`, filtered to
`chore(tickets): file ` subject lines (the commit shape both
`frob ticket new`/`_new_renumber.py`'s renumber-on-conflict path AND the
two sweep-filing call sites in `_rapid_sweep.py` produce), then
classified each by its title text: sweep-filed regression/claim-divergence
tickets carry a distinctive machine-generated title shape
(`"(post-land sweep regression from an unattributed source (sweep spawned
by T-XXXX))"` or `"(post-land claim divergence from T-XXXX)"`); every
other title is a human/agent-authored `frob ticket new` filing.

**Result (measured against this repo's `main` at design time, HEAD
`42ab32443`):** of 53 `chore(tickets): file ` commits in the last 300,
**12 are sweep-filed** (regression tickets from post-land sweeps) and
**41 are ordinary `frob ticket new` filings** -- individual, distinct
filing DECISIONS made by a human or an agent across many separate
sessions (this design document's own drive alone filed T-3535, T-3536,
T-3537, T-3532, T-3551, T-3552, T-3550, each a separate commit in this
same 300-commit window).

**Conclusion: neither group is a batching target.**
- The 12 sweep-filed commits already match T-3544's Failure-log finding:
  each sweep run files at most one ticket, so each commit already IS
  "one commit per genuine filing event" -- there is no loop here
  producing N commits from one event to collapse.
- The 41 `frob ticket new` commits are not mechanical repetition at all:
  each represents an actual, distinct decision by a human or an agent to
  create a new ticket, at a different point in time, usually from a
  different worktree/session. Batching these together would mean either
  (a) holding a `frob ticket new` commit uncommitted until some UNRELATED
  future flush event fires -- which makes a freshly-filed ticket
  invisible to `doable`/dependency graphs until that event, directly
  regressing the exact "fleet liveness must not regress" constraint this
  design's own mirror-batching work is careful to avoid -- or (b)
  batching only truly-concurrent same-instant filings, which this
  106-commits-of-mirror-noise repo does not actually exhibit as a
  meaningful fraction of the 41 (no two `file` commits in the sampled
  window share a timestamp closer than ordinary human/agent working
  cadence).

So the "109+41 of last 300" framing in T-3542/T-3544's original bodies
should be read as **109 mirror commits are the real, addressed-above
batching target; the 41 file commits are not a second batching target at
all** -- they are already at the correct one-commit-per-decision
granularity, and the owner-facing "82 percent of main is chore churn"
framing from T-3542 should be revised to attribute that share to the
mirror-commit class specifically, not split across both.

## Hazard needing an owner call

The one item in [Readers](#readers-files-vs-git-history) this document
could not resolve as "safe by construction" is the `CrossTicketLeakage`
/ scope-closure family's single-ticket-per-commit assumption for
ledger-mirror commits. Before implementation lands, an owner needs to
confirm: is a flush commit whose subject names multiple tickets an
acceptable shape for those checks to special-case, or does the flush
design need to instead produce one commit per FLUSHED TICKET (still
batching within a ticket's own multiple pending verbs, just not across
tickets) to avoid touching that check family at all? This document does
not pick a default -- it is the one open question the implementation
ticket should be blocked on an owner sign-off for.

## Deliverable status

This document is the deliverable for T-3550. The implementation is filed
as a separate ticket, blocked by this document's own owner sign-off on
the hazard above (see [Hazard needing an owner call](#hazard-needing-an-owner-call)).
