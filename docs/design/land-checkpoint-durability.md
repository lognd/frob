# Land checkpoint durability: the gap beyond the sweep window (T-1554)

T-0907 and T-1523 each close one killable window in `frob ticket land`
with a durable marker + reconcile-on-next-invocation pattern. This
document maps every window that remains, evaluates the two options T-1523
left open (full durability vs. a resumable verify-only step), and
recommends one.

## What is already covered

`land()`'s real work happens in two phases, each with its own marker:

1. **Pre-commit staging** (`src/frob/tickets/_land.py`, T-0907's
   `_write_land_repair_marker`/`_clear_land_repair_marker`): written
   before `_land_squash_apply` mutates `root`, cleared the moment it
   returns. A SIGTERM here leaves a marker the NEXT `frob ticket land`
   invocation reconciles before touching anything else.
2. **Post-land verification tail** (T-1523's
   `_write_post_land_verify_marker`/`_clear_post_land_verify_marker`,
   same file): written immediately after `land()` returns a real,
   non-dry-run success (the commit already exists on `root`), cleared
   once `_land_cmd._land`'s tail -- the post-land unscoped-error sweep,
   the `LAND-PROOF:` line, and (with `--finish`) worktree removal --
   actually completes. `_stale_post_land_verify_markers` reconciles a
   leftover marker at the START of the next `frob ticket land` call
   against the same `root`.

Both follow the identical write-before/clear-after-unconditional-finally
shape; the reconciliation logic never assumes success from a marker's
mere presence -- it always re-derives the true state from `git`/the
ledger.

## The gap: what "post-land verification tail" durability does NOT cover

T-1523's own marker treats "the tail completed" as one atomic fact. It is
not one fact -- it is three sequential steps
(`_finish_land_after_success`, `src/frob/app/ticket_runner/_land_cmd.py`),
and a kill partway through any of them leaves the marker CLEARED (if the
kill lands after `_clear_post_land_verify_marker` runs in the sweep's own
`finally`) or PRESENT-but-imprecise (if before), in either case losing
track of exactly which sub-step actually finished:

1. **The post-land unscoped-error sweep itself.** Already durable in
   its own right (T-1694's `.frob/verify-in-flight.json` in-flight
   marker, reused unchanged by `run_coalesced_verification` -- not
   re-invented for land). This sub-step is NOT the gap; it is cited here
   only because it sits inside the window T-1523's marker wraps, and a
   reader auditing "is everything durable now" needs to know this piece
   already is.
2. **Printing `LAND-PROOF:`** (`_print_land_proof`). Purely a stdout
   write plus two read-only checks (`git merge-base --is-ancestor`, the
   ticket's `state_on_main`) -- idempotent and side-effect-free. A kill
   here loses nothing: re-running `frob ticket land` (or even just
   `frob doctor`) can re-derive and reprint the identical line from `git`
   state alone. **Not a real gap** -- flagged in T-1523's body as
   "believed safe" and this document's own audit confirms why: it reads,
   never writes.
3. **`--finish`'s worktree removal** (`_finish_worktree`) and, for
   `--retire-on-proof`, **branch deletion** (`_delete_worktree_branch`).
   THIS is the real remaining gap. Unlike step 2, this step performs
   irreversible git-state mutations (`git worktree remove`,
   `git branch -D`) with no marker of its own:
   - A kill between `_finish_worktree` succeeding and
     `_delete_worktree_branch` running (only reachable via
     `--retire-on-proof`) leaves the worktree gone but the branch alive
     and unreferenced by any worktree -- recoverable by hand
     (`git branch -D <name>`) but nothing surfaces that it is needed.
   - A kill DURING `git worktree remove` itself (T-1715's own guard
     already refuses if the worktree is "provably in use," but a refusal
     check is not a transaction -- the external `git` process can still
     be killed mid-removal) can leave `.git/worktrees/<name>`'s
     administrative files in a torn state. `git worktree list` on a
     torn entry is git's own well-known failure mode
     (`git worktree repair`/`prune` are git's answer, not this repo's) --
     this repo's own `frob worktree sweep` (section 12b of the agent
     playbook) already treats a dirty-or-torn worktree conservatively
     (kept, not force-removed), so the blast radius of a torn removal is
     "an extra manual `git worktree prune`," not silent data loss. Still
     un-marked, un-reconciled, and un-tested against a real SIGTERM
     injection -- exactly the gap T-1554's body names.

Net: the ACTUAL surviving gap is narrower than T-1554's Option A implies.
Step 2 needs no new mechanism (it is already idempotent). Step 1 already
has one (T-1694, reused). Only step 3 -- `--finish`/`--retire-on-proof`'s
own two git mutations -- is genuinely unmarked and untested.

## Option A (full): durable/self-describing state at every instant

Extend the T-0907/T-1523 marker pattern one step further: write a
`land-finish-pending/<ticket_id>.json` marker (mirroring
`_land_verify_pending_marker_path`'s own shape) immediately before
`_finish_worktree` runs, recording `{ticket_id, worktree_path, branch}`;
clear it once BOTH `_finish_worktree` and (if `--retire-on-proof`)
`_delete_worktree_branch` return. Reconcile at the top of the next
`frob ticket land` call the same way `_stale_post_land_verify_markers`
does: if the marker's worktree no longer exists AND (for
`--retire-on-proof`) the branch is already gone, log "recovered, nothing
to redo"; if the worktree still exists, log the incomplete finish and
either retry it (safe -- `_finish_worktree`/`_delete_worktree_branch` are
each individually idempotent: removing an already-gone worktree or
deleting an already-gone branch are refusals, not corruption) or surface
it for the operator to run `--finish` again by hand.

**Cost:** one more marker file, one more reconciliation function, one
more load-bearing test (a real SIGTERM injection mid-`_finish_worktree`,
matching T-1523's own precedent of testing its marker against a real
kill rather than a unit-level mock). Small, additive, same shape as two
mechanisms already in the codebase and already load-bearing-tested there.

**Benefit:** closes the LAST remaining unmarked land sub-step. After this,
"every intermediate land state is durable" (T-1554's Option A framing)
becomes literally true, not aspirationally true.

## Option B: a separately-invocable `--verify-only <sha>` resumable step

Decouple verification-and-finish from a fresh merge/commit entirely: a
new `frob ticket land --verify-only <sha>` subcommand that, given an
already-landed commit sha, re-runs exactly the tail (sweep +
`LAND-PROOF` + optional `--finish`) against it, without requiring a live
worktree merge/commit cycle to have JUST happened in this process.

**Cost:** a new CLI surface (subcommand flag, its own argument parsing,
its own tests, its own docs) plus a real behavioral question Option A
does not raise: what identifies "this commit's tail already ran" if not
a marker keyed to the SAME land invocation that made it? The honest
answer is `--verify-only` would need to consult the SAME
T-1523/(Option A) markers to know what is left to do -- meaning Option B
does not replace Option A's markers, it is a new CLI entrypoint that
also depends on them existing. Building the CLI surface before the
markers it needs is backwards; building it after makes it a strictly
additive convenience on top of Option A, not an alternative to it.

**Benefit:** a killed land's operator (or a coordinator script) gets an
explicit, nameable recovery command instead of relying on the NEXT
`frob ticket land` invocation's implicit reconciliation to notice and
fix things. Genuinely useful for the "no new land is coming soon, but I
want to confirm/finish this one now" case -- e.g. a coordinator doing
end-of-session cleanup across several worktrees, wanting to force
`--finish` resolution without waiting for the next real land.

## Recommendation

**Do Option A first, narrowly** (the `land-finish-pending` marker
described above -- not the inflated "every instant" framing, since two
of the three tail sub-steps already need no new mechanism per the audit
above). It is small, uses an established pattern, and closes the one
real remaining gap.

**Defer Option B** to a follow-up ticket, scoped as "a CLI entrypoint
that reads Option A's markers on demand" rather than a competing
mechanism -- filed only once Option A's marker exists for it to read,
so the two tickets do not race to define the marker shape independently
by two different people (this document proposes Option B's marker
dependency to prevent the CLI-first mistake, not to attach a design
timeline).

## What this ticket does NOT do

No code changes: T-1554's own scope is design, matching T-1523's
original body ("needs its own design doc before implementation, same as
T-1523's body said before it was scoped down"). The `land-finish-pending`
marker, its reconciliation function, and its SIGTERM-injection test are
follow-up implementation work for a new ticket this document's
Recommendation section scopes, not built here.

## `reclaim_orphaned_squash_residue` (T-2157/T-2170)

A narrower, already-shipped mechanism in the same problem space as this
document's Option A/B discussion above, worth cross-referencing here
rather than in a second design doc: `frob.tickets._land_git_ops.
reclaim_orphaned_squash_residue` closes the specific DirtyMain-trap case
where a land killed mid-squash-merge (SIGKILL, uncatchable) leaves
`root`'s real index/working tree staged and dirty with no safe way to
tell that residue apart from a live concurrent land's own staging.

It answers that question the same way this document's own markers would
have to: by consulting `land.lock`'s existing advisory `flock` as the
liveness oracle (a non-blocking exclusive lock attempt that SUCCEEDS
only when nothing currently holds it -- the kernel frees an `flock` the
instant its holder exits, SIGKILL included), never a recorded-pid
comparison (pid reuse makes that unsafe) and never residue age.

T-2157 shipped the primitive itself, tested and correct, but reachable
from nowhere in production. T-2170 wired it into `frob.tickets._land.
land()`'s own startup, immediately before `_land_lock` is acquired (it
must run before the lock is taken, since its own liveness probe is a
non-blocking flock on that same lock file) and before
`_refuse_if_main_dirty`'s own DirtyMain check -- so a dead land's residue
is cleared automatically at the start of the very next land attempt,
instead of requiring a coordinator to notice and clear it by hand.
