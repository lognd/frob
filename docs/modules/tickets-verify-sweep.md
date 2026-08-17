# frob.tickets -- verification and sweep: watermark, backpressure, quarantine, rapid profile

Part of the `frob.tickets` reference, split out of `docs/modules/tickets.md` by T-1780 so this subject's own lease no longer blocks every other ticket working a different one; see [`docs/modules/tickets.md`](tickets.md#split-files-t-1780) for the full split index.

## Merge queue (T-1345, first portion)

<!-- frob:describes src/frob/tickets/_land_queue.py::QueueEntry -->
<!-- frob:describes src/frob/tickets/_land_queue.py::QueueError -->
<!-- frob:describes src/frob/tickets/_land_queue.py::enqueue -->
<!-- frob:describes src/frob/tickets/_land_queue.py::drain_next -->
<!-- frob:describes src/frob/tickets/_land_queue.py::queue_status -->
<!-- frob:describes src/frob/tickets/_land_queue.py::file_lock -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_land_enqueue -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_land_drain -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_land_core -->

`frob.tickets._land_queue` formalizes the coordinator-lands-serially
discipline `docs/guides/agent-playbook.md` already documents as process
into checkable tooling: `enqueue(root, ticket_id, worktree, branch)`
appends a `queued` entry to `.frob/land-queue.json` and returns
immediately (a caller never blocks waiting for `land()` to actually run);
`drain_next(root, land_fn)` pops the oldest `queued` entry (FIFO) and runs
it through a caller-supplied `land_fn` (normally a thin wrapper around
`land()` itself), recording the outcome (`landed` + commit sha, or
`failed` + the `LandError` value) back onto the entry rather than
dropping it. `queue_status(root)` is a read-only snapshot of the full
queue, any status, for a caller that wants to show state.

**CLI surface (T-1444, the follow-up T-1345 disclosed):**

- `frob ticket land <id> --worktree <path> --queue` -- enqueue instead of
  landing immediately (`_land_enqueue`); prints the assigned queue
  position and returns right away.
- `frob ticket land --drain` -- serially process every `queued` entry,
  one process, one invocation (`_land_drain`), not a long-running poll
  loop; call it repeatedly (a scheduler, a coordinator loop) to keep
  draining. Needs neither `<id>` nor `--worktree` -- both are no longer
  argparse-`required`, enforced instead in the app layer for every OTHER
  mode (`_require_land_args`/`_land_plan_cmd`'s own check).
- `_land_core` is the shared merge-check-splice-close-commit-sweep chain
  both a direct `frob ticket land <id>` call and `_land_drain`'s per-entry
  `land_fn` run -- the SAME `LAND-PROOF:` line prints on every real,
  non-dry-run success either way (T-1345's own acceptance criterion,
  "preserve the existing LAND-PROOF contract"). Unlike the old inline
  `_land` body, `_land_core` never calls `sys.exit`: a post-land
  unscoped-error-sweep revert returns
  `LandError.PostLandUnscopedSweepFailed` instead, so `_land_drain` can
  attribute a mid-batch failure to the one ticket that caused it
  (dequeued, logged, NOT retried -- `drain_next`'s own policy, unchanged)
  and continue draining the rest of the queue.

**Deferred (disclosed, not silently dropped -- see T-1444's Done report
for the real follow-up ticket id):** `_land_core`'s pre-/post-land
unscoped-error sweep and baseline capture still run PER TICKET inside
`_land_drain`'s loop, exactly as a direct `frob ticket land <id>` call
would -- this ticket's acceptance criterion also asked for "one baseline
capture + one full sweep per drain of N tickets" (shared across the whole
batch) and "sublinear total verification wall-clock", neither of which
this increment implements. Every entry's own delta validation is real and
attribution is preserved; the batch-level sharing optimization is the
scoped-out remainder.

**Policy decisions, recorded here per the ticket's own design questions:**

- **Where the queue lives.** `.frob/land-queue.json`, guarded by a
  dedicated `fcntl` flock (`.frob/land-queue.lock`) -- same posture as
  `_land._land_lock`'s `.frob/land.lock`, a deliberately separate file so
  the two concerns (serializing the actual git-heavy `land()` body vs.
  serializing queue-file bookkeeping) never share a lock. A crashed
  drainer leaves the file exactly as it was at its last successful write;
  the next `drain_next` call simply resumes.
- **A queued branch that no longer merges cleanly.** Rejected back to the
  agent: `drain_next` marks the entry `failed` with the `LandError`
  recorded and dequeues it (no longer a `drain_next` candidate), but never
  removes it from the JSON history and never auto-rebases-and-retries.
  Auto-retry risks landing a diff the agent never actually re-verified --
  the same class of gap `docs/guides/agent-playbook.md` section 9's
  deletion-filter rule exists to catch for a stale-base merge.
- **Concurrency.** The queue-file lock is held only across the
  pop-and-mark-landing step and the record-outcome step, NOT across the
  `land_fn` call itself -- `land_fn`'s own `_land_lock` already serializes
  the expensive part. Running exactly one drainer process per `root` is
  an operational invariant this module documents but does not itself
  enforce; a second concurrent drainer would be safe (the queue lock
  prevents two drainers popping the same entry) but wasteful (both
  contend on `_land_lock` for nothing).
- **LAND-PROOF.** `drain_next` returns the updated `QueueEntry` (carrying
  `commit_sha` on success), and `land_fn`'s own `Result[LandReport,
  LandError]` is available to whatever wrapper the caller supplies -- a
  future CLI drainer verb can print the same `LAND-PROOF:` line `frob
  ticket land` already does today, from the `LandReport` its `land_fn`
  closure captured. This module does not print anything itself (no CLI
  surface in this scope), so the contract is preserved by construction:
  nothing here bypasses or reimplements `land()`'s own reporting.

## T-1686 epic status: landing independent of verifying

T-1686's own stated design intent: a check stays on the land critical
path only if its failure damages someone OTHER than the author (ledger
integrity, LAND-PROOF, lease/lock discipline); everything else defers to
a batch verification pass behind a durable watermark. The CONNECT-WHAT-
EXISTS mechanism this rests on is complete, end to end, as of T-1736:

1. **Durable record** (T-1687) -- `.frob/verify-queue.json` (append-only
   intent log) and `.frob/verify-watermark.json` (single current
   watermark), independent of any worker.
2. **Enqueue side** (T-1736) -- `frob.tickets._land._land_locked` calls
   `record_intent` once, right after every real land's squash-apply
   commit, with that commit's own touched-symbol set.
3. **Drain side** (T-1688) -- the daemon's coalescing worker
   (`frob.serve._daemon._poll_verify_worker`, already wired into the
   daemon's own poll loop) reads the queue to its tip, verifies once, and
   advances the watermark past the whole batch on green.
4. **Attribution** (T-1690) -- a red batch's findings resolve to the
   specific land commit whose touched symbols reach them, via graph
   reachability, never a lexical file-touched-it guess.
5. **Circuit breaker** (T-1693, wired T-1791) -- a red batch raises
   quarantine (`frob.verify._quarantine.raise_quarantine`, called from
   `_file_regression_ticket`, the seam both the per-land sweep and the
   coalescing worker share) and suspends deferred landing until every
   finding is filed or dismissed -- never auto-cleared by a later green
   run.
6. **Crash safety** (T-1694) -- an in-flight marker means a worker killed
   mid-verification can never leave the watermark advanced past a batch
   it did not finish confirming.

**What remains, disclosed and filed separately, not silently folded into
this epic's "done":**

- **The profile dial itself** (T-1696, queued, blocked_by T-1692/T-1693
  -- both already landed) -- `fortress`/`standard`/`rapid` are still
  three separate code paths in `src/frob/app/ticket_runner/_land_cmd.py`
  (`rapid_land = effective is ProfileName.RAPID` and its downstream
  branches) rather than one depth-parameterized settings record; the
  machinery above benefits `rapid` today, T-1696 is the deliberately-
  last leaf that collapses `fortress`/`standard` onto the same
  watermark-backed mechanism (`_land_cmd.py` was never in T-1686's own
  declared scope: `_land_queue.py`, `_daemon.py`, `_rapid_sweep.py`,
  `_land.py`, this doc).
- **CLI visibility** (T-1697, queued, not yet built) -- `frob verify
  status`/`now`/`explain` for a human or CI step to see the unverified
  window (depth, age, quarantine, attribution) without reading
  `.frob/*.json` by hand. Deferred verification with an invisible
  backlog is indistinguishable from no verification; this leaf is what
  keeps the mechanism above honest.
- **Batch test selection** (T-1689, queued) and **bisecting
  unattributable residue** (T-1691, queued) -- the two remaining tier-3
  refinements T-1686's own body names (running a batch's union
  touched-set in one pytest process; bisecting the findings tier-2
  attribution cannot resolve to exactly one commit).

This epic ticket itself cannot close while T-1689/T-1691/T-1695/T-1696/
T-1697 remain open (tier=epic, `frob ticket close`'s own
`OpenDescendant` refusal) -- it stays `in-progress`, carrying this
status summary, until its last descendant lands.

## Verification watermark (T-1687, foundation of the T-1686 epic)

<!-- frob:describes src/frob/verify/_watermark.py::SCHEMA_VERSION -->
<!-- frob:describes src/frob/verify/_watermark.py::VerifyQueueEntry -->
<!-- frob:describes src/frob/verify/_watermark.py::Watermark -->
<!-- frob:describes src/frob/verify/_watermark.py::WatermarkError -->
<!-- frob:describes src/frob/verify/_watermark.py::record_intent -->
<!-- frob:describes src/frob/verify/_watermark.py::queue_status -->
<!-- frob:describes src/frob/verify/_watermark.py::load_watermark -->
<!-- frob:describes src/frob/verify/_watermark.py::advance_watermark -->
<!-- frob:describes src/frob/verify/_watermark.py::compact_queue -->

T-1686's epic makes landing independent of synchronously verifying in
every profile: a check must stay on the critical path only if its
failure damages someone OTHER than the author (ledger integrity,
LAND-PROOF, lease/lock discipline); everything else (coverage floors, doc
drift, arch thresholds, ...) can defer to a batch verification pass. That
requires a durable record of what has and has not been verified yet,
independent of whatever worker eventually drains it -- the frob.verify
package is that record, and `frob.verify._watermark` (T-1687) is its
whole content today: no daemon, no worker, no CLI verb. Landing the
record first, standalone, is deliberate: retrofitting a durable store
under an already-running worker is strictly harder than building the
worker on a store that already exists.

**Two persisted files, two independent concerns:**

- **`.frob/verify-queue.json`** -- an append-only intent log. One
  `VerifyQueueEntry` per land: `commit_sha`, `ticket_id`, `touched_symbols`
  (see below), `enqueued_at`, and `profile`. `record_intent(root, *,
  commit_sha, ticket_id, touched_symbols, profile)` appends exactly one
  entry and refuses (`WatermarkError.EmptyTouchedSymbols`) on an empty
  symbol set -- a land with nothing for tier-2 attribution to reach would
  otherwise make every later finding at that commit permanently
  unattributable. `queue_status(root)` is a read-only snapshot, oldest
  first.
- **`.frob/verify-watermark.json`** -- one record: "main is verified
  through `commit_sha`, at `verified_at`, by `run_id`, against
  `baseline_digest`". `advance_watermark(root, *, commit_sha, run_id,
  baseline_digest)` unconditionally overwrites the prior record --
  this module trusts the caller's own "fully green batch" decision and
  does not re-derive it. `load_watermark(root)` reads it back.

**Touched SYMBOLS, never file paths.** `VerifyQueueEntry.touched_symbols`
is a tuple of symref-shaped symbol ids (the same id shape
`frob.graph.GraphSnapshot.symbols` keys on), never a path list. Tier-2
attribution (T-1686's own design: "a finding anchored at symbol S
attributes to the commit whose touched symbol set REACHES S in the
reference graph") is a graph reachability query over symbol ids -- a
path-keyed record cannot answer it once a symbol moves between files
without misreporting the move itself as a regression. Computing the
touched-symbol set from a real `Diff`/`GraphSnapshot` pair is deliberately
OUT of this module's own scope (frob.verify never imports `frob.graph`)
-- a caller with graph access (a later leaf's land-time wiring) resolves
and passes the set in; this module only validates the shape (non-empty)
and persists it verbatim.

**One shared lock implementation, not two.** Both files use
`frob.tickets._land_queue.file_lock` (T-1687 extracted the merge queue's
own fcntl advisory-lock mechanics into this reusable, `label`-tagged
context manager so `_queue_lock` above and frob.verify's two locks all
share one implementation) -- "two lock protocols over adjacent state in
one repo is a deadlock waiting to be discovered in production" per this
ticket's own scope note. The queue lock and the watermark lock are still
two SEPARATE lock files (never reuse a lock/state file across a different
concern, matching `_land_queue`'s own rule for `.frob/land.lock` vs
`.frob/land-queue.lock`), just built from the same primitive.

**Append-only, compacted below the watermark, never rewritten in
place.** `record_intent` only ever appends. `compact_queue(root)` is the
one operation that shortens `.frob/verify-queue.json`: it drops every
entry at-or-before the CURRENT watermark's `commit_sha` (a no-op,
`Ok(0)`, if there is no watermark yet or that commit is not present in
the queue) and never rewrites or reorders a still-pending entry. Both
operations still write the whole file in one `write_text` call under
`file_lock`, the identical "not atomic-replace, but never torn under
normal operation" posture `_land_queue._save_queue`'s own docstring
documents.

**"Cannot verify" is never "verified".** `load_watermark` treats a
missing watermark file (nothing verified yet) and a CORRUPT watermark
file identically at the read boundary: both return `Ok(None)`, logged at
WARNING in the corrupt case so the corruption itself stays visible even
though the read degrades safely -- a caller must never be able to
mistake a corrupted record for a stale-but-real one. `queue_status`, by
contrast, propagates a corrupt QUEUE file as
`Err(WatermarkError.StoreCorrupt)` rather than degrading to an empty
tuple: an unreadable intent log misread as "nothing pending" is itself a
false "how far is main verified" claim, just as dangerous as a stale
watermark reading as current. `record_intent`/`compact_queue` (the two
mutators) both refuse outright on that `Err` rather than risk silently
discarding or duplicating intent records on top of an unreadable file.

**What this ticket does NOT do (disclosed, next leaves in the epic):**
no daemon-side coalescing worker (T-1688), no CLI wiring that calls
`record_intent` from a real `land()`, no tier-1/2/3 attribution logic, no
profile-to-queue-depth dial. This module is purely the data model plus
its read/write primitives, verified in isolation
(`tests/unit/verify/test_watermark.py`).

**The enqueue side, wired (T-1736).** `record_intent` had no real caller
until this leaf: T-1688's worker only drains/advances/compacts an
EXISTING queue, so without this the coalescing worker never had anything
to verify no matter how many lands happened. `frob.tickets._land.
_record_verify_intent_for_landed_commit` is the call site --
`_land_locked` invokes it once, right after a REAL (non-dry-run)
`_land_squash_apply` success, never inside `_land_squash_apply` itself
(that file is outside this ticket's own declared scope,
`src/frob/tickets/_land.py` alone). It computes the landed commit's own
diff via `frob.gitio.working_diff(root, pre_land_tip)` -- `pre_land_tip`
is `root`'s tip captured before the squash-apply started, a direct
ancestor of the just-sealed commit, so `merge-base(HEAD, pre_land_tip)`
IS `pre_land_tip` and the resulting diff is exactly this land's delta,
not some other window -- resolves it against a `frob.graph` snapshot
(load-or-build, the same `.frob/cache.db` every other graph-backed
caller in this repo shares) into a touched-symbol set via a local
span-overlap match (`_touched_symrefs_for_intent`, a deliberate,
disclosed `frob:waive DUP001` duplicate of `frob.gates._touched_symrefs`/
`_overlaps` -- `src/frob/gates/__init__.py` is outside this ticket's own
scope too, so fixing the duplication at its source is a follow-up, not
this leaf's job), and calls `record_intent` with it.

Best-effort end to end: a diff-compute failure, a graph-build failure, an
empty touched-symbol set, or a `record_intent` failure are each logged
(WARNING/INFO) and swallowed, never raised -- the land already succeeded
and sealed a real commit by the time this runs; an unfed verify queue is
a visible, bounded liability (T-1697 surfaces queue depth/age), never a
reason to fail an already-sealed land.
<!-- frob:describes src/frob/tickets/_land.py::_record_verify_intent_for_landed_commit -->
<!-- frob:describes src/frob/tickets/_land.py::_touched_symrefs_for_intent -->

## Coalescing verify worker (T-1688)

<!-- frob:describes src/frob/verify/_worker.py::WorkerError -->
<!-- frob:describes src/frob/verify/_worker.py::WorkerOutcome -->
<!-- frob:describes src/frob/verify/_worker.py::run_coalesced_verification -->
<!-- frob:describes src/frob/verify/_worker.py::CoalescingWorker -->
<!-- frob:describes src/frob/serve/_daemon.py::_poll_verify_worker -->
<!-- frob:describes src/frob/verify/_worker.py::_write_in_flight_marker -->
<!-- frob:describes src/frob/verify/_worker.py::_clear_in_flight_marker -->
<!-- frob:describes src/frob/verify/_worker.py::_reconcile_stale_in_flight_marker -->
<!-- frob:describes src/frob/verify/_worker.py::_in_flight_marker_path -->
<!-- frob:describes src/frob/verify/_worker.py::_IN_FLIGHT_MARKER_REL -->

The trailing-edge-debounce half of the T-1686 epic, and where the
wall-clock saving actually comes from: `frob.verify._worker.
run_coalesced_verification` is the whole job on one wake -- read the
verify queue, look at ONLY its tip entry, verify ONCE, and on a
genuinely green result advance the watermark past every entry the queue
currently holds and compact them away.

**Coalesce, not iterate -- structurally, not by convention.** The
function never loops over queue entries; it reads `entries[-1]` and calls
its `verify_fn` exactly once, so five (or five hundred) queued lands
produce exactly one verification call. This is provable directly:
`tests/unit/verify/test_worker.py::TestRunCoalescedVerification::
test_five_queued_entries_call_verify_exactly_once` enqueues five entries,
injects a call-counting `verify_fn`, and asserts the count is 1 -- an
invocation count, not a timing measurement (a timing-based test proves
nothing about whether coalescing actually happened, only about how fast
it was).

**`None` can never advance the watermark -- structurally.** `verify_fn`
returning `None` (T-1703's own contract for `_unscoped_error_findings`: a
budget-truncated or otherwise partial check is unmeasurable, never
"clean") hits an early `return Err(WorkerError.Unmeasurable)` that sits
BEFORE every other branch in the function, including the one branch that
calls `frob.verify.advance_watermark`. There is no flag to remember to
check -- the only textual path to `advance_watermark` in this file is the
final branch of a chain no `None` result can fall through to.

**Four possible outcomes**, distinguished by `WorkerOutcome.status`:

- `"empty"` -- nothing queued, `verify_fn` never even called.
- `"baseline-established"` -- a real, measured result, but with no PRIOR
  rolling baseline to diff against; "no new findings" cannot be asserted
  with nothing to compare to, so this is deliberately NOT treated as
  green (watermark untouched) even though the check itself succeeded.
- `"red"` -- new findings vs the rolling baseline; files a regression
  ticket (reusing `frob.app.ticket_runner._rapid_sweep.
  _file_regression_ticket`, T-1684's own filer) and leaves the watermark
  untouched -- a red batch quarantines, it does not revert (T-1686's own
  recorded decision).
- `"green"` -- no new findings vs a real prior baseline; the watermark
  advances to the tip commit and `compact_queue` drops every entry the
  queue held (they are all covered by the same tip verification).

**Reused, not reinvented.** The rolling-baseline read/write/diff
machinery is `frob.app.ticket_runner._rapid_sweep`'s own
(`_read_baseline`/`_write_baseline`/`_file_regression_ticket`, built for
T-1684's per-land spawn) -- this module imports those three functions
directly rather than re-deriving the same comparison a second time; the
only genuinely new decision layered on top is "and if it's green, advance
the watermark and compact the queue", which T-1684 had no reason to know
about.

**Touched symbols stay symbolic.** This module never reads
`VerifyQueueEntry.touched_symbols` at all (attribution is deliberately
out of this leaf's scope -- T-1686's own framing: verifying at the tip
proves the batch is green as a whole, but does not by itself attribute
any one finding to any one commit) and never reduces the field to a file
path for its own convenience; that data stays intact for T-1690's
attribution leaf to consume later.

**Wake conditions and where they actually live.** `CoalescingWorker`
holds the debounce/floor DECISION state (`notify()` records a wake,
`tick()` decides whether to actually run); it never runs on a timer of
its own -- `frob.serve._daemon._poll_verify_worker` drives it from the
daemon's existing `DEFAULT_POLL_INTERVAL_S` (20s) cycle, calling
`notify()` when `main`'s HEAD has moved since this job last looked (the
"queue append" wake proxy: a land IS a HEAD move) and calling `tick()`
unconditionally every cycle (cheap -- it is a no-op unless the trailing-
edge debounce window has gone quiet, or the periodic floor has elapsed).
**T-1737 closed the scope cut.** The FS-watch push signal `frob.serve.
_watch.WatchThread` provides IS now wired to `notify()`: `WatchThread` is
instantiated in `frob.serve._socketd.run_socket_daemon` (outside this
ticket's own `src/frob/serve/_daemon.py` scope, so the wiring lives in
`_socketd.py` itself), and its `on_change` callback calls both the
existing `graph-changed` event publish (T-1096) and `_get_verify_worker(
root).notify()` -- the SAME cached worker instance `_poll_verify_worker`
polls, since both look it up through this module's own `_VERIFY_WORKERS`
cache keyed by `str(root.resolve())`. A watch tick observing a real
on-disk change now resets the debounce window immediately, an earlier
trigger for the identical decision `tick()` already makes -- not a third,
independent wake condition with its own state.

**Crash safety: a dead worker can never advance the watermark on a batch
it did not finish verifying (T-1694).** The watermark is a claim that
work was done; every way it can advance without that work having actually
completed is a correctness hole exactly as serious as a ticket reading
`done` with its code absent. `run_coalesced_verification` closes this
with a single in-flight marker (`.frob/verify-in-flight.json`), reusing
the T-0907/T-1523 write-marker-before/clear-marker-after pattern rather
than inventing a second one:

- `_reconcile_stale_in_flight_marker` runs FIRST, before this call reads
  the queue or writes its own marker, so a marker left by a PRIOR dead
  run is always reconciled before any new work starts.
- `_write_in_flight_marker` records the tip commit BEFORE `verify_fn` is
  even called -- the moment this run starts making a claim about that
  commit. Written write-temp-then-`os.replace` (atomic rename) so a crash
  mid-write can never leave a torn, half-written marker behind for the
  next reconciliation to misread.
- `_clear_in_flight_marker` runs unconditionally (a `finally` block) once
  this call reaches ANY stable outcome -- green, red, baseline-
  established, unmeasurable, or a raised exception -- covering every
  named kill point in one guard: death between the queue read and
  verification start (no marker was ever written -- nothing durable was
  claimed, so the next run just starts clean), death between a green
  result and the watermark write, and death between the watermark write
  and `compact_queue` (both leave the marker present at the next
  startup).
- Reconciliation never assumes green from the marker's mere presence. If
  the marker's commit already equals the CURRENT watermark's commit, the
  prior run's `advance_watermark`+`compact_queue` sequence evidently
  completed and only the marker's own clear was lost -- logged as
  recovered, nothing re-verified. In every other case (no watermark, a
  different commit, or an unreadable marker file) the batch is logged
  UNVERIFIED; nothing needs to be explicitly re-queued, since
  `compact_queue` only ever drops entries the watermark actually reached
  -- if that never happened, the queue still holds them, and the next
  `run_coalesced_verification` call verifies them again exactly as if no
  prior attempt had ever started.
- Two workers must never verify concurrently for one root: this reuses
  the daemon's existing `frob.serve._socketd.acquire_singleton_lock` (at
  most one daemon process per root) rather than adding a second exclusion
  mechanism -- `CoalescingWorker.tick()` only ever runs from that single
  daemon's own poll loop.

**Trailing-edge debounce, concretely.** Each `notify()` call pushes the
deadline to `now + debounce_window_s` (default 90s) -- a steady trickle
of lands keeps deferring the run, so a burst of five lands inside the
window produces exactly one verification once the burst actually goes
quiet. The periodic floor (default 300s) is measured from when work FIRST
became pending, independent of how many notifies arrived since -- a
continuous stream of notifies that never lets the debounce window go
quiet still forces a run once the floor elapses, so a busy repo cannot
starve verification indefinitely.

### Resource budget: never starve foreground agents (T-1695)

<!-- frob:describes src/frob/verify/_worker.py::DEFAULT_LEASE_CEILING -->
<!-- frob:describes src/frob/verify/_worker.py::DEFAULT_MIN_AVAILABLE_MEMORY_MB -->
<!-- frob:describes src/frob/verify/_worker.py::_worker_backpressure_reason -->
<!-- frob:describes src/frob/verify/_worker.py::_ensure_reduced_priority -->

A permanent background verifier competing with foreground agent work for
CPU/memory is not theoretical on this box: the 2026-07-29 session losses
were OOM kills, and the standing cap is 3-4 concurrent agents. Two
ceilings, both checked in `_worker_backpressure_reason` AFTER
the debounce/floor decision already says "ready to run" but BEFORE
`run_coalesced_verification` is actually called:

- **Lease ceiling** (`DEFAULT_LEASE_CEILING`, default 3): the worker
  yields while the cross-worktree ticket lease count is at or above this
  value, reusing `frob.tickets._profile._concurrent_lease_count` -- the
  SAME signal `frob worktree sweep` already reads to tell a live
  multi-agent session from a solo one, never a second "how busy is this
  repo" notion.
- **Memory floor** (`DEFAULT_MIN_AVAILABLE_MEMORY_MB`, default 1024):
  the worker yields while available memory (T-1672's `/proc/meminfo`
  `MemAvailable` reader, reused via `frob.testing._coverage_refresh.
  _available_memory_mb`) is below this floor. `None` (unmeasurable, e.g.
  non-Linux) never blocks a run -- guessing wrong here would be worse
  than not checking at all.

A yield is never silent: `tick()` logs at INFO naming the exact cause
("lease count N >= ceiling M" or "available memory XMB < floor YMB") and
how long the work has been pending, and leaves the debounce/floor pending
state completely untouched so the very next poll cycle re-evaluates
fresh -- neither losing the pending work nor double-counting it. A worker
that silently never runs would be indistinguishable from one that is
keeping up; this is the mechanism that makes that impossible.

**Priority reduction, not just deferral.** Even when the worker DOES run,
it must not compete for CPU/IO priority with foreground work.
`_ensure_reduced_priority` lowers this process's own `os.nice` value (by
10) and, where the `ionice` binary exists, sets I/O scheduling class 3
(idle) for this process -- applied at most ONCE per process (guarded by a
module-level flag, since `os.nice` is cumulative and a second call would
compound rather than idempotently reapply the same reduction), called
from `CoalescingWorker.tick()` right before its own `run_
coalesced_verification` call -- deliberately NOT inside `run_
coalesced_verification` itself, so `frob verify now`'s synchronous,
human/agent-invoked call straight into that function (`src/frob/app/
verify_runner.py`) stays unthrottled, since that command is foreground
work by definition, not the permanent-background competitor this ticket
is about. Every `frob check` subprocess a verification pass spawns after
that point inherits both values automatically via ordinary POSIX
fork/exec priority inheritance -- no per-subprocess wiring needed
anywhere else in this codebase.

## Batch test selection (T-1689)

<!-- frob:describes src/frob/verify/_selection.py::BatchSelectionError -->
<!-- frob:describes src/frob/verify/_selection.py::BatchSelection -->
<!-- frob:describes src/frob/verify/_selection.py::select_batch_tests -->
<!-- frob:describes src/frob/verify/_selection.py::run_batch_selected_tests -->
<!-- frob:describes src/frob/app/graph_runner.py::_run_select_batch_tests -->

The second, independent half of the T-1686 epic's wall-clock saving,
alongside T-1688's coalescing gate pass: N separate `frob test`
invocations over the queue's overlapping touched sets pay N cold pytest
startups and re-run every test two tickets both touch once PER ticket;
computing the batch's UNION touched set first and selecting once against
it collapses this to one collection, one conftest evaluation, one set of
session fixtures.

**Reuse, not reinvention.** `frob.verify._selection` does not re-derive
symbolic reachability -- `frob.testing._select.select_tests` (touched
symbols -> the tests that reach them) and `frob.testing._runners.
run_selected` (spawn each language's selection in ONE process) already
exist and already have this shape; the one genuinely new piece is
`_synthetic_diff_for_touched_symbols`, which bridges a batch's union
`touched_symbols` (`VerifyQueueEntry`'s own durable record -- symrefs,
never raw diff hunks) into `select_tests`'s hunk-based `Diff` input by
building a `Hunk` spanning exactly each touched symbol's own definition
span. `select_tests`'s own first step (`_touched_symbols`, span-overlap
against the snapshot) re-derives that SAME symbol back out, so this is a
faithful round-trip through the existing machinery, not an approximation
of it.

**Never a narrower fallback.** `run_batch_selected_tests` returns
`Err(BatchSelectionError.GraphUnavailable)` (or `RunnersUnavailable`) the
moment the graph or `test.runner` config cannot be loaded/built -- it
never silently selects fewer tests than the touched set actually implies.
The caller (`frob.app.graph_runner._run_select_batch_tests`, wired as
`frob graph select-batch-tests`) is the one place that decision resolves:
on `Err` it falls back to the FULL suite (every runner's `ALL_SENTINEL`
selection, the same shape `frob test --all` already produces) with a
loud WARNING naming why, never to running nothing or a partial set.

**Reads the same durable queue T-1688 reads.** `_run_select_batch_tests`
reads `.frob/verify-queue.json` via `frob.verify._watermark.
queue_status` -- the identical `VerifyQueueEntry` records `run_
coalesced_verification` reads for gate verification, so a batch's test
selection and its gate verification are computed from the SAME notion of
"what this batch touched", never two independently-drifting ones. An
empty queue is a no-op (INFO, not an error) -- there is nothing to
select.

## Symbolic attribution (T-1690)

<!-- frob:describes src/frob/verify/_attribution.py::AttributionError -->
<!-- frob:describes src/frob/verify/_attribution.py::Attribution -->
<!-- frob:describes src/frob/verify/_attribution.py::attribute_batch -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::_attribute_new_findings -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::_ticket_is_open -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket -->

The hard leaf T-1686's own design called out first: when a batch
verification goes red, map each finding to the commit that caused it,
without ever guessing.

**The rule.** A finding anchored at symbol S attributes to the batch
commit whose `VerifyQueueEntry.touched_symbols` REACHES S in the
reference graph (`frob.graph.callgraph.build_reference_graph`'s
caller-symref -> callee-symref edges, walked forward). "The commit that
touched the same file" is the lexical shortcut this module refuses: it is
wrong the moment a change breaks a CALLER rather than the symbol itself,
and it misreports a pure symbol-move between files as a regression the
instant the moved symbol's file changes out from under a path-keyed
identity. `frob.verify._attribution.attribute_batch` never compares a
path string to decide "does this commit explain this finding" -- every
decision walks real symrefs.

**Ambiguity is a first-class outcome.** Exactly one candidate commit
reaching the finding's symbol is `Attribution(status="attributed", ...)`;
zero candidates, or more than one, is `status="unattributed"` -- a
distinct, equally real state, NEVER resolved by picking the newest commit
as a tiebreak (T-1686's own standing decision: a confident wrong
attribution costs more than an honest "unknown", because it sends someone
to read a diff that is not the cause). `candidate_commits` names every
commit that DID reach the finding for the ambiguous case (empty for the
zero-candidate case), so a reader can tell "nobody could have caused
this" apart from "too many could have" at a glance.

**The reachability path is logged, not just the verdict.**
`Attribution.reachability_path` is the actual symref chain the BFS walked
from the owning commit's touched symbol to the finding's own symbol;
`attribute_batch` logs it at INFO for every attributed finding and logs
every candidate commit at WARNING for every unattributed one. An
attribution nobody can audit is an assertion, not evidence (T-1686's own
standing constraint) -- this is how that constraint is actually met, not
just stated.

**Symbol resolution degrades honestly when line information is
missing.** T-1690's declared scope (`_attribution.py`, `_rapid_sweep.py`)
does not include `_land_cmd.py`/`_verify.py`, so the `(rule_id, file)`
finding identity those modules already produce still carries no line
number. When a finding's line IS known, `_resolve_symbol` picks the
single enclosing symbol from `SymbolRecord.span`. When it is NOT known,
every symbol `GraphSnapshot.symbols` records against that file becomes a
candidate target -- strictly better than a bare file-level identity
comparison (a per-symbol reachability check still runs against each
candidate), but weaker than true line-precision: a multi-symbol file
where only one function actually broke can widen the candidate set enough
to manufacture ambiguity that line-precision would have resolved. This is
a disclosed, deliberate degradation, not a silently narrowed guess --
extending the upstream finding identity to carry a line number is future
work outside this ticket's scope.

**"Cannot verify" is never "verified", extended to attribution.** A
reference graph that fails to build/load at all makes EVERY finding's
attribution impossible; `attribute_batch` returns
`Err(AttributionError.GraphUnavailable)` for the WHOLE batch rather than
silently attributing some findings and skipping others.

**Wired into the filer, not a separate report.**
`_rapid_sweep._file_regression_ticket` (T-1684's own regression filer,
called from both the rapid deferred sweep and T-1688's coalescing worker
red branch) now runs every new finding through
`_attribute_new_findings` first (reads the CURRENT durable verify queue
as the batch -- the commits landed since the last watermark advance,
exactly the set a red sweep could have been caused by) before deciding
what to file:

- A finding attributed to EXACTLY ONE commit whose OWNING ticket is
  still open (`_ticket_is_open`: loaded, and not `done`/`dropped`) is
  logged and left OFF the regression ticket entirely -- it already has a
  home, and re-filing it would just be noise.
- Everything else -- attributed to a closed/dropped ticket's commit, or
  genuinely UNATTRIBUTED -- is filed, with the full attribution audit
  trail (commit, symbol, reachability path, or the specific reason
  attribution failed) written into the ticket body so a reader never has
  to re-derive what `attribute_batch` already computed.
- Attribution UNAVAILABILITY (`_attribute_new_findings` returns `{}` when
  the queue is unreadable/empty or the graph cannot be built) degrades to
  the pre-T-1690 behavior verbatim: every finding filed, no attribution
  lines -- "cannot attribute" must never suppress a real regression's own
  ticket.

**T-2208: filing now disposes, in the same operation.** Before T-2208,
`_file_regression_ticket` raised quarantine (T-1791, above) for a red
batch and filed a regression ticket naming it, but never called
`clear_quarantine` -- a human had to hand-restate the exact fact the
system already knew via `frob verify dispose --file-ticket
F=T-XXXX`, once per red batch, and deferred landing stayed off
fleet-wide until they did. `_auto_dispose_filed_findings`, called right
after the ticket commits, disposes exactly the `(rule_id, file)` pairs
the just-filed ticket covers (`unfiled_pairs`) as `("filed",
regression_id)` -- the identical disposition shape and `clear_quarantine`
call `frob verify dispose --file-ticket` itself makes, so the WARNING-
level "CLEARED" audit log is indistinguishable from a manual disposal.
`clear_quarantine`'s own contract is atomic (refuses to write anything
unless EVERY currently-raised finding is disposed), so a batch where some
findings attribute to a DIFFERENT already-open ticket this call never
touched leaves quarantine fully raised -- an undisposed finding with no
tracking ticket is exactly what quarantine exists to surface, and this
call auto-disposing it just because it happened to run would reopen the
hole T-1693 closed.

**What this leaf does NOT do.** The bisect leaf T-1686's own design names
as the handoff for UNATTRIBUTED findings ("tier 3: bisect only the
residue tier 2 cannot attribute") is not built yet -- an unattributed
finding today is filed as an ordinary regression ticket with its
candidate commits named in the body, for a human to read; there is no
automated bisect trigger. This is a disclosed scope cut, not a silent
gap: the bisect leaf is future work this ticket does not claim to close.

**T-1753 follow-up (post-land sweep hygiene).** T-1690's own land
tripped the deferred post-land sweep: `attribute_batch` split along its
tier-1/tier-2/tier-3 seams (`_parse_finding`, `_matching_batch_entries`,
`_attribute_one`) to clear ARCH001's 60-line function threshold, two
lines wrapped under 88 chars (E501), and `_attribute_new_findings`'s
`pairs` parameter widened from `list[tuple[str, str]]` to
`list[tuple[str, str] | tuple[str, str, int]]` -- the annotation was
narrower than what `attribute_batch` itself already accepted, and a real
`ty` invalid-argument-type finding on the test exercising the 3-tuple
(line-bearing) shape caught it. No behavior changed; the split is a pure
extraction and the widened type is a correction, not a new capability.

**T-1754 follow-up (the SAME ty finding, moved not fixed).** T-1753's
own `list[...]` widening on `_attribute_new_findings`'s `pairs`
parameter only moved the invalid-argument-type mismatch to the CALL
SITE: `list` is INVARIANT in Python's type system, so
`_partition_findings_by_attribution`'s own `pairs: list[tuple[str,
str]]` was never actually assignable to `_attribute_new_findings`'s
`list[tuple[str, str] | tuple[str, str, int]]` parameter, no matter how
that parameter's own element-type union was phrased. The real defect was
the CONTAINER type, not the element type: `pairs` is only ever iterated
in `_attribute_new_findings` (never mutated), so the correct, sound type
is a covariant `collections.abc.Sequence[tuple[str, str] | tuple[str,
str, int]]` -- callers passing a `list[tuple[str, str]]` (every
real caller in this module; no caller has ever produced a line-bearing
3-tuple) are naturally accepted, exactly as they should be.
## Backpressure (T-1692)

<!-- frob:describes src/frob/verify/_backpressure.py::BackpressureError -->
<!-- frob:describes src/frob/verify/_backpressure.py::BackpressureCeilings -->
<!-- frob:describes src/frob/verify/_backpressure.py::BackpressureStatus -->
<!-- frob:describes src/frob/verify/_backpressure.py::ceilings_for_profile -->
<!-- frob:describes src/frob/verify/_backpressure.py::current_status -->
<!-- frob:describes src/frob/verify/_backpressure.py::block_until_watermark_advances -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_apply_backpressure -->

Deferral is a credit line, not free money. Without this leaf, T-1687's
durable queue plus T-1688's coalescing worker is a mechanism for
accumulating unbounded unverified debt with a pleasant user experience --
strictly worse than the synchronous sweep it replaces. `frob.verify.
_backpressure` is what makes the deferral BOUNDED.

**Two independent ceilings, either one sufficient to trip.**
`BackpressureStatus.tripped` is `True` the moment EITHER axis is
exceeded:

- DEPTH: the number of entries currently in the verify queue exceeds
  `max_depth`. Depth alone is not enough -- one commit can sit unverified
  all weekend behind a dead worker without depth ever growing past a
  small number.
- AGE: the oldest unverified entry's `enqueued_at` is older than
  `max_age_s`. Age alone is not enough either -- a burst of forty lands
  in quick succession stays inside any reasonable age window while depth
  grows unbounded.

Both axes are read from the SAME durable queue T-1687/T-1688 already
maintain (`frob.verify.queue_status`) -- no new storage.

**Block, never fail.** `block_until_watermark_advances` is the land-path
entrypoint (wired into `frob.app.ticket_runner._land_cmd._land_core_
prepare` via `_apply_backpressure`, called once profile resolution
completes and skipped entirely under `--dry-run`). At the ceiling it does
not refuse the land -- a refusal just makes the developer re-run the
whole thing. It BLOCKS, logging the trip LOUDLY at WARNING (current
depth, age, and the watermark commit being waited on -- T-1686's own
standing rule: "blocking silently is the one unacceptable outcome"), and
ACTIVELY drives the coalescing worker itself
(`frob.verify.run_coalesced_verification`) on each iteration rather than
passively waiting for some other process to drain the queue -- "a block
simply pays back the deferred cost at the moment it came due" (T-1686's
own framing). This is what keeps the design correct even with no daemon
watching the queue: the blocked land IS the thing that unblocks itself.
A persistently red (quarantined) batch that never clears trips
`block_until_watermark_advances`'s own last-resort timeout
(`_DEFAULT_BLOCK_TIMEOUT_S`, 30 minutes) -- logged at ERROR, and the land
PROCEEDS anyway rather than wedging every future land behind one
unresolved batch forever; the loud WARNING trail already logged is the
safeguard, not a second refusal on top of it.

**Per-profile ceilings are the profile-collapse dial.**
`ceilings_for_profile` resolves `fortress` to depth 0 / age 0
(synchronous -- any queued-but-unverified commit trips it, though this
module still BLOCKS rather than refuses even here), `standard` to a
bounded depth/age pair (`_STANDARD_DEFAULT_MAX_DEPTH`=5,
`_STANDARD_DEFAULT_MAX_AGE_S`=3600s, overridable via `frob.toml`'s
`[profile] backpressure_max_depth`/`backpressure_max_age_s`), and
`rapid` to `None`/`None` on both axes -- unbounded, so rapid NEVER
blocks, by construction rather than a separate `if profile == rapid:
skip` branch at every call site.

**Disclosed scope cut.** The full profile-to-queue-depth collapse
(deleting every remaining `if rapid:` seam scattered through the land
pipeline, T-1686's own "payoff" framing) is not this leaf's job --
`_apply_backpressure` is additive, wired alongside the existing
rapid/standard branching `_land_core_prepare` already has, not a
replacement for it. That collapse is later work this ticket does not
claim to close.

**T-1756 follow-up (post-land sweep hygiene).** T-1692's own land
tripped the deferred post-land sweep: 4 E501 lines wrapped under 88
chars across `_land_cmd.py`'s `_land_core_prepare` and
`_backpressure.py`'s `BackpressureError`/`current_status`. No behavior
changed.

## Quarantine circuit breaker (T-1693)

<!-- frob:describes src/frob/verify/_quarantine.py::QuarantineError -->
<!-- frob:describes src/frob/verify/_quarantine.py::QuarantinedFinding -->
<!-- frob:describes src/frob/verify/_quarantine.py::QuarantineRecord -->
<!-- frob:describes src/frob/verify/_quarantine.py::load_quarantine -->
<!-- frob:describes src/frob/verify/_quarantine.py::is_quarantined -->
<!-- frob:describes src/frob/verify/_quarantine.py::raise_quarantine -->
<!-- frob:describes src/frob/verify/_quarantine.py::clear_quarantine -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_quarantine_override_ceilings -->

The single most important rule in the T-1686 epic (this ticket's own
text). Landing on top of a known-broken base is what makes attribution
cost explode: every subsequent land widens the candidate set and adds
findings that are consequences rather than causes, not new problems of
their own.

**Raise, on red.** `frob.verify._quarantine.raise_quarantine(root, *,
batch_commit_shas, findings)` persists a durable `.frob/quarantine.json`
record the moment a batch verification (T-1688's coalescing worker, or
any other caller that has just run one) comes back red -- `findings` is
T-1690's own `Attribution` shape, narrowed to what this module acts on
(`QuarantinedFinding`: rule/file/line, the T-1690 attribution if one
exists, and a `disposition` that starts empty). Logged at ERROR, naming
the batch and every finding -- T-1686's own standing rule that a
state-changing event on the land path must never be silent.

**While raised, deferred landing is off.** `is_quarantined(root)` is
`True` the moment a raised record's `cleared_at` is still `None`.
`frob.app.ticket_runner._land_cmd._quarantine_override_ceilings` is the
land-path enforcement point: called right before T-1692's own
`ceilings_for_profile` result is handed to `block_until_watermark_
advances`, it OVERRIDES those ceilings to `BackpressureCeilings(max_depth=
0, max_age_s=0.0)` -- the same shape `fortress` profile already gets --
whenever quarantine is raised, regardless of what profile this
particular land is actually running under. This reuses T-1692's EXISTING
block/drain mechanism rather than adding a second, parallel gate: a
`max_depth=0` ceiling trips on ANY queued-but-unverified commit, which is
exactly "either run fully synchronous verification, or block" (this
ticket's own acceptance wording) -- the credit line is suspended, the
work itself is not. `is_quarantined`'s own `Err` (an unreadable/corrupt
`.frob/quarantine.json`) is treated identically to `True` at this call
site -- "cannot verify is never verified" extended one hop further:
an unreadable quarantine store must never be misread as "not raised",
the one direction that would silently let deferred landing resume.

**Clears ONLY on attribution, never on green.** This is the property the
whole module exists to enforce, and it is deliberately not the obvious
design: a naive circuit breaker clears itself the next time a check
comes back green. That is wrong here -- a green run after more lands
means the tree is clean NOW, it says nothing about whether the ORIGINAL
regression was ever understood; auto-clearing on green is how a circuit
breaker silently becomes decoration (this ticket's own words).
`clear_quarantine(root, *, dispositions, reason, actor)` is the ONLY
function in this module that clears a raised record, and it requires a
`dispositions` entry for EVERY finding the raise recorded -- each either
`"filed"` (a real ticket id now tracks it) or `"dismissed"` (a human's
recorded reason) -- refusing with `QuarantineError.FindingsNotDisposed`
otherwise, never a partial clear. There is no "record a green
verification" entrypoint anywhere in this module, by design: a green
result structurally cannot reach the clear path at all.

**Durable across a worker restart.** `.frob/quarantine.json` mirrors
`frob.verify._watermark`'s own single-current-record persistence shape
(pydantic `frozen=True, extra="forbid"`, schema-versioned) -- `is_
quarantined` reads it fresh every call, never an in-memory flag a daemon
restart could lose. A quarantine that evaporates on restart is worse
than none, because it is trusted (this ticket's own words).

**Wired into the batch-verification driver (T-1791).** `frob.app.
ticket_runner._rapid_sweep._raise_quarantine_for_red_batch` calls
`raise_quarantine` from inside `_file_regression_ticket` -- the shared
"a red batch verification came back" seam BOTH T-1684's per-land
deferred sweep and T-1688's coalescing worker call through
(`_file_regression_ticket` is `run_coalesced_verification`'s own filer
too, T-1688's docstring names it directly), so wiring the raise at this
one call site covers both drivers without a second integration point.
`batch_commit_shas` comes from the CURRENT verify queue
(`frob.verify.queue_status`) -- the exact set of lands the red result
could have been caused by, the same batch `_attribute_new_findings`
itself reads for the ticket body's attribution trail; an empty or
unreadable queue skips the raise (logged) rather than naming a
fabricated batch. Each `QuarantinedFinding` reuses the SAME `Attribution`
mapping `_file_regression_ticket` already computed for its own ticket
body (`_attribute_new_findings`, called once, threaded into both this and
`_partition_findings_by_attribution` rather than a second graph build).
Quarantine raises even when every pair in the batch already attributes
to a still-open ticket and no NEW regression ticket gets filed -- the
breaker's question is "did the tree go red", not "did filing produce a
new ticket", and conflating the two would let an all-already-tracked red
batch slip past the breaker with deferred landing still enabled. A
`raise_quarantine` failure is logged at ERROR and swallowed: the
regression ticket this function files either way is still the durable
record, and a caller filing a real regression must never be blocked by
the quarantine flag failing to persist.
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::_raise_quarantine_for_red_batch -->  

<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::_warm_tree_clears_unattributed_native_noise -->
**A warm-tree re-check drops cold-worktree native-extension noise before
raising (T-1847).** A fresh worktree's `ty check`/import resolution can
fail on a declared native (`strata_core`, `frob_core`) simply because
`frob natives build`/`make core` has not run yet -- an environment
artifact, not a regression (`docs/guides/agent-playbook.md` section 1
says the same about the identical symptom in a different context). Left
unfiltered, that noise reaches `_raise_quarantine_for_red_batch` exactly
like a real finding and can raise quarantine over nothing. Before naming
a red batch, each `(rule, file)` pair is passed through
`_warm_tree_clears_unattributed_native_noise`, which drops a pair ONLY
when BOTH hold: the finding is UNATTRIBUTED (no real commit behind it
yet -- an attributed finding is never overridden by this re-check,
regardless of rule id) and its rule id is in
`_NATIVE_EXTENSION_ADJACENT_RULE_IDS` (deliberately narrow --
`unresolved-import` only, the one shape T-1847 actually observed). When
both hold, it re-checks RIGHT NOW whether every declared native still
fails to import (`frob.strata._native_staleness.unimportable_natives`);
if none are broken anymore, the finding is dropped from the set that can
raise quarantine (still filed as a regression ticket by the caller --
this only changes whether it also reaches the quarantine dispose queue).
If a native is STILL unimportable, the finding is kept and the raise
proceeds unchanged -- this re-check only clears TRANSIENT cold-worktree
staleness, never a durably broken environment. If dropping cold-worktree
noise empties the batch entirely, the raise is skipped altogether and
logged at INFO, the same "nothing to name" shape
`_raise_quarantine_for_red_batch` already uses for an empty verify
queue.

**Identity-less findings are refused at write time, and an already-stuck
store can be recovered (T-2207).** A live incident: something upstream
persisted a `QuarantinedFinding` with `rule_id=""` and `file=""` both
empty -- a finding naming no rule and no file. That record could never
be cleared: `clear_quarantine`'s `dispositions` mapping is keyed by
`(rule_id, file, line)`, and the CLI's own `RULE:FILE:LINE` addressing
(`frob.app.verify_runner._parse_finding_arg`) structurally can never
produce the key `("", "", None)` -- an empty `file` component is always
rejected as malformed, by construction of that syntax. With no way to
dispose it, `clear_quarantine` correctly refused forever
(`FindingsNotDisposed`), leaving deferred landing off fleet-wide with no
CLI recovery path.

Two fixes, both in this module. PRODUCER: `raise_quarantine` now drops
any finding whose `rule_id` AND `file` are both empty before persisting
(`_is_unidentifiable`), logging at ERROR -- the same shape as the
`_NATURALLY_UNATTRIBUTABLE_RULES` filter just above it in the function
body, applied one step later. A batch whose only findings are
identity-less now returns `Err(QuarantineError.EmptyFindings)` instead
of writing an unrecoverable record to disk. CONSUMER:
`retire_unidentifiable_findings(root, *, reason, actor)` is the explicit,
logged recovery verb for a store that already reached this state before
the producer fix existed (or reaches it again some other way this fix
did not anticipate) -- it dismisses every identity-less finding in the
current record by targeting the SHAPE directly rather than a
caller-supplied key (no caller-supplied key can ever address it), then
applies `clear_quarantine`'s own "clear only if every finding -- not
just the identity-less ones -- is disposed" rule. A well-formed
undisposed sibling still blocks the actual clear afterward: this retires
only the identity-less records, never a bulk dismiss, and it does not
reopen the hole T-1693 closed (a real unaddressed finding still gates
landing).
<!-- frob:describes src/frob/verify/_quarantine.py::retire_unidentifiable_findings -->

## `frob verify` CLI (T-1697)

<!-- frob:describes src/frob/app/verify_runner.py::VerifyQuarantineFindingView -->
<!-- frob:describes src/frob/app/verify_runner.py::VerifyStatus -->
<!-- frob:describes src/frob/app/verify_runner.py::build_status -->
<!-- frob:describes src/frob/app/verify_runner.py::run -->

Before this ticket, a raised quarantine (the previous section) could only
be inspected or cleared by calling `frob.verify._quarantine`'s private
Python functions directly -- a safety mechanism operable only through a
private API is not operable. `frob verify` is the CLI that makes the
whole T-1686 unverified-window epic auditable and actionable from a
shell.

**`frob verify status [--json]`.** Assembles one `VerifyStatus` snapshot
(`build_status`): the watermark commit and its age, the current queue
depth, the oldest unverified entry's commit/ticket/age, and quarantine
state -- while raised, every recorded `QuarantinedFinding` renders as a
`VerifyQuarantineFindingView` carrying a `key` string
(`RULE:FILE:LINE`) that round-trips straight into `frob verify
dispose`'s own `--file-ticket`/`--dismiss` arguments, so a human/CI
reader never has to hand-encode one. **Porcelain rule:** exits non-zero
while quarantine is raised, so a shell or CI step can gate on "is this
repo's verification healthy" without parsing prose. `--json` serializes
`VerifyStatus` directly -- the pydantic model IS the wire contract, not a
hand-maintained parallel dict.

**`frob verify now [--json]`.** Drains and verifies the queue
synchronously right now (`frob.verify.run_coalesced_verification`), for
a human who wants the unverified window closed before walking away.
Exits non-zero on a `"red"` outcome.

**`frob verify explain RULE:FILE[:LINE] [--json]`.** Re-runs
`frob.verify.attribute_batch` for exactly one finding against the
CURRENT verify queue and prints the reachability path an `"attributed"`
result carries, or the candidate-commit list an `"unattributed"` result
carries -- so an attribution is auditable evidence a human can read, not
a bare assertion. Exits non-zero on anything but a clean attribution.

**`frob verify dispose --file-ticket RULE:FILE:LINE=TICKET | --dismiss
RULE:FILE:LINE=REASON --reason TEXT [--actor NAME] [--json]`.** The
operable dispose path this ticket's own critical requirement calls for:
applies one or more dispositions (repeatable `--file-ticket`/`--dismiss`,
keyed by the same `RULE:FILE:LINE` shape `status` prints back) and, once
every currently-quarantined finding is disposed, calls
`frob.verify._quarantine.clear_quarantine` -- the only path that ever
clears a quarantine. `--reason` is `clear_quarantine`'s own overall
narrative; `--actor` defaults to the OS user. A partial disposition set
(fewer `--file-ticket`/`--dismiss` entries than findings raised) refuses
the whole clear, exactly like `clear_quarantine`'s own contract -- there
is no "half-cleared" CLI shortcut.

**`frob verify dispose --retire-unidentifiable --reason TEXT [--actor
NAME] [--json]` (T-2217).** Wires the CONSUMER recovery verb described
above (`retire_unidentifiable_findings`) into the CLI -- the only dispose
mode that can clear an identity-less finding at all, since
`--file-ticket`/`--dismiss`'s `RULE:FILE:LINE` addressing structurally
cannot key `("", "", None)`. Mutually exclusive with
`--file-ticket`/`--dismiss` in the same invocation (refuses outright
rather than silently picking one): the identity-less recovery path
targets a SHAPE, never a caller-supplied key, so combining it with one
is always a mistake, not a valid request. Same "no half-cleared" contract
as the ordinary path -- a well-formed, still-undisposed sibling finding
blocks the actual clear exactly as before; only the identity-less
record(s) are retired, and a follow-up ordinary `--file-ticket`/
`--dismiss` call disposes the rest.
<!-- frob:describes src/frob/app/verify_runner.py::_run_dispose -->

**Live validation (2026-08-08).** This ticket's own end-to-end proof: the
repo's `.frob/quarantine.json` was raised on an `unresolved-import`
finding at `tests/unit/strata/test_capacity.py`, `commit_sha=None` (T-1690's
own UNATTRIBUTED shape -- no single batch commit's touched symbols reached
it). Investigation confirmed every imported name resolves (`hasattr`
checks pass, `import strata_core` succeeds) and `uv run ty check
tests/unit/strata/test_capacity.py` reports "All checks passed!" -- the
signature of cold-worktree native-extension noise, not a real import
break (which would attribute to whichever commit removed the symbol).
`frob verify dispose --dismiss` cleared it with that reasoning recorded
as the disposition, and `frob verify status` confirmed `quarantine:
clear` immediately after (exit 0).

Should an UNATTRIBUTED finding raise quarantine at all, or be re-checked
in a warm tree first? This ticket's own answer: yes, keep raising on
UNATTRIBUTED as-is. A quarantine that silently skips itself on
"couldn't attribute" reintroduces exactly the failure mode T-1690's
docstring warns against -- "cannot verify is never verified" applies to
the breaker's own trigger condition, not just to the findings it
records. The actual risk this session surfaced is different: a
quarantine that fires on cold-worktree noise and gets dismissed
routinely trains an operator to treat `--dismiss` as a rubber stamp,
which erodes the signal for the real finding the breaker exists to
catch. The fix for that risk is not "don't raise" -- it's making the
COLD-WORKTREE-NOISE SHAPE ITSELF DETECTABLE before a human has to
eyeball it (an unattributed finding whose rule/file is native-extension-
adjacent, checked once in a warm tree before the raise persists). That is
new work, not a change to this ticket's dispose path -- filed as a
follow-up rather than done here, since narrowing scope mid-ticket to add
a second detection mechanism would blur what this ticket's own evidence
actually proved (the dispose path works end-to-end).

## Development profiles (`frob.toml [profile]`, T-1575)

<!-- frob:describes src/frob/tickets/_profile.py::configured_profile -->
<!-- frob:describes src/frob/tickets/_profile.py::effective_profile -->
<!-- frob:describes src/frob/tickets/_profile.py::downgrade_profile_ratchet -->

`frob.tickets._profile` reads `frob.toml`'s `[profile] profile = "..."`
(`ProfileName`: `rapid` | `standard` | `fortress`) -- `standard` is the
default, today's unchanged behavior, whenever `[profile]` or `frob.toml`
itself is absent, so an existing repo's ceremony is never silently
relaxed just because `frob` shipped this feature.

The ticket's own motivation: a small/new repo pays the same fixed land
ceremony (TEST016, the T-1514 double sweep, the T-1463 baseline snapshot
worktree, REL001) as a 950-file repo, and that ceremony is fixed-cost,
not proportional to repo size. `rapid` trims it:

- **No TEST016 on the land path at all.** `_land.py::_check_mutation_
  evidence` checks `effective_profile(worktree)` before its T-1518
  `SYNC_BLOCKING_KINDS` branch; `rapid` skips BOTH the synchronous
  `security`-kind mutation subprocess and the deferred batch-sweep
  enqueue. BUG002 (`bug_repro_violations`) is unaffected by the profile
  and still runs/blocks for bug/security kind regardless of profile.
- **No pre-commit sweep.** `_land_cmd.py::_land` passes
  `pre_commit_sweep=None` to `land()` when rapid.
- **No synchronous post-land sweep, and no baseline thread** (T-1684):
  the post-land sweep runs DETACHED and files a ticket instead of
  reverting; the T-1463 baseline-capture thread is not started at all,
  because the deferred sweep carries its own rolling baseline. See
  "Deferred post-land sweep" below. `standard` keeps both the
  synchronous revert-on-red sweep and the baseline thread verbatim.
- **Evidence/done-report leniency for `kind in {docs, chore}`, and
  REL001 off under rapid** are likewise disclosed as deferred follow-up
  in T-1575's Done report, not wired in this increment -- the ticket's
  land-pipeline seams for both exist but were judged too invasive to
  land safely in the same pass as the two seams above without dedicated
  regression coverage of their own.

**Never relaxed in any profile, `rapid` included:** ledger integrity
checks and LAND-PROOF verification -- neither is gated by
`effective_profile` anywhere.

**`fortress`** parses and round-trips as a `ProfileName` member but has
NO behavioral wiring yet -- a placeholder for a stricter tier a follow-up
ticket defines.

**One-way auto-ratchet.** `effective_profile(root)` -- the read path
every seam above calls, never `configured_profile` directly -- applies a
ONE-WAY ratchet on top of the configured value: if `rapid` and any of
three live thresholds trips (repo file count > 300, total ticket count >
200, concurrent lease count > 5 -- see `frob.tickets._profile`'s module
docstring for the exact primitives each reads and why those numbers),
the ratchet persists to `.frob/profile-ratchet.json` and every future
`effective_profile` call returns `standard` regardless of what `frob.
toml` still says or whether the tripped condition later reverses (files
deleted, tickets archived). `downgrade_profile_ratchet(root, reason=...)`
is the only way back -- an explicit, loudly-logged call, never invoked
from any land-pipeline seam automatically.

<!-- frob:waive DOC006 reason="'frob.toml.j2' is a bare jinja template filename (src/frob/scaffold/data/**), not a dotted code-symbol path -- DOC006's kind-4 matcher has no non-code-extension exclusion, so a bare basename with a 'frob.' prefix reads as a project-namespace symbol lookup and misfires" -->
**`frob scaffold` defaults new repos to `rapid` (T-1576).** Every
`frob.toml.j2` template under `src/frob/scaffold/data/**` writes
`[profile] profile = "rapid"` into a freshly scaffolded project's
generated `frob.toml` -- a brand-new repo is exactly the under-threshold
case `rapid` exists for, and the one-way auto-ratchet above upgrades it
to `standard` automatically the moment it grows past the thresholds.
This does NOT affect an EXISTING repo's `frob.toml`: an absent `[profile]`
key still means `standard` (`configured_profile`'s own documented
default), unchanged by this ticket -- only the scaffold's OWN generated
template content changed.

## Rapid debt and the ratchet override (T-1681)

<!-- frob:describes src/frob/tickets/_profile.py::ratchet_override_enabled -->
<!-- frob:describes src/frob/tickets/_evidence.py::record_rapid_debt -->

The size auto-ratchet above made `rapid` unreachable for exactly the
repos where the ceremony costs the most -- frob's own tree trips the file
and ticket thresholds many times over, so configuring `rapid` here was a
silent no-op. `[profile] override_ratchet = true` (read by
`ratchet_override_enabled`) is the explicit owner decision to keep
`rapid` anyway. Deliberately a config key and not an env var: it lives in
a tracked file, so `git log frob.toml` states exactly which commits were
produced under relaxed rules.

`record_rapid_debt(root, ticket_id, skipped)` is the other half of that
bargain -- every check `rapid` skips appends one self-contained JSON line
(`ticket`, `skipped`, `commit`) to `rapid-debt.jsonl`. TRACKED, not under
`.frob/`: the debt must survive a clone and a `frob clean`, and must be
reviewable in a diff. Best-effort by construction (failing to record debt
never fails a close) but logged at ERROR, because an unrecorded
relaxation is the one outcome that makes the cleanup pass unreliable.
The T-1681 re-verification pass drains that file rather than
re-deriving what happened from git archaeology.

## Deferred post-land sweep (`rapid` only, T-1684)

<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::spawn_deferred_post_land_sweep -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::RapidSweepError -->

`standard`'s post-land sweep is synchronous and reverts a just-made land
commit when it finds new unscoped errors. Correct when lands are rare,
but it puts a full-repo `frob check` (2-8 minutes on this repo) plus the
T-1463 baseline check on the critical path of every land -- and a
five-minute land is its own correctness risk, because the queue stops
draining and work batches into giant unreviewable lands.

Under `rapid`, `_land_core_finish_post_land` calls
`spawn_deferred_post_land_sweep` instead. That:

1. appends a `rapid-debt.jsonl` line
   (`post-land-unscoped-sweep-deferred`) BEFORE spawning anything, so
   "this commit landed unverified" is a machine-readable fact from the
   instant it is true, even if the child never starts;
2. spawns `frob ticket sweep-async <id> --commit <sha>` detached
   (`start_new_session=True`), logging to
   `.frob/rapid-sweep/<id>-<sha12>.log`;
3. returns immediately -- the land does not wait.

The child runs `run_deferred_post_land_sweep`, which pays exactly ONE
unscoped check by diffing against a **rolling baseline**
(`.frob/rapid-sweep-baseline.json`, the previous deferred sweep's
absolute `(rule_id, file)` set) rather than measuring a fresh pre-land
baseline. Semantics:

- **No baseline yet** (first sweep in a repo, or a corrupt file): record
  one, file nothing. An absent baseline is `None`, never an empty set --
  comparing against assumed-clean would report every pre-existing error
  as newly introduced, which is exactly how an automated filer earns
  being ignored.
- **Unmeasurable check** (refused spawn, timeout, unparsable output):
  `Err(Unmeasurable)`, and the baseline is left untouched, so the next
  sweep still diffs against a set we actually trust.
- **New pairs found:** one `bug` ticket at `high` priority naming every
  new `(rule_id, file)` pair and the commit, scoped to the offending
  files. The commit STANDS -- rapid never rewrites published history,
  because under rapid other agents are already branching from it.
- **Every sweep, red or green, rewrites the baseline.** An error already
  filed as a ticket must not be re-filed by the next land; from then on
  the filed ticket is the record.

**The debt line commits itself (T-1698).** `rapid-debt.jsonl` is tracked
on purpose, and the deferred-sweep record is written AFTER the land
commit is sealed (it names that commit), so it cannot ride along in it.
`_commit_rapid_debt` therefore gives it its own tiny follow-up commit,
staging that one path and nothing else. This is not cosmetic: without it
every rapid land left the shared root checkout dirty and the NEXT land
from ANY agent refused with `DirtyMain` -- one uncommitted line
deadlocked a whole three-agent wave. It stages `rapid-debt.jsonl` alone
rather than `git add -A`, because concurrent lands are racing on that
same root and a blanket add would swallow another agent's in-flight work.
Relatedly, a `DirtyMain` refusal now NAMES the offending paths
(`porcelain_dirty_paths`/`describe_root_dirt`): the original message
said only "root has uncommitted changes", and three agents each burned
minutes without learning it was a single one-line file. T-1740 sharpened
this further: `describe_root_dirt` now calls out STAGED state
explicitly and first ("N STAGED (likely a prior land's leftover index,
T-1740)") whenever any of the dirty paths are staged rather than merely
modified in the working tree -- exactly this deferred-sweep commit's own
failure mode (a killed/refused `_commit_rapid_debt` or land leaving
`rapid-debt.jsonl`/a squash-apply's own content staged) is precisely the
shape that used to read as undifferentiated "uncommitted changes" and
sent an agent looking for working-tree edits instead of the real cause.

`frob ticket sweep-async` is a real subcommand rather than a `-c` code
string so the deferred sweep is inspectable, re-runnable by hand against
any commit, and covered by the same CLI surface tests as every other
verb. It exits non-zero only when the sweep was unmeasurable, so a human
re-running it can tell "verified" from "could not verify".

**The filed regression ticket ALSO needed its own commit (T-1755).**
`_file_regression_ticket`'s `new_ticket(root, spec)` call is the second
tracked-file write the detached sweep makes, and -- unlike the debt
line -- it went uncommitted for the same reason the debt line originally
did: nothing committed it. Root-caused directly (not assumed): `frob.
tickets._new_renumber.new_ticket` is the LIBRARY function -- it takes
`ledger_lock`, calls `write_ticket`, and returns; the T-1130/T-1615
auto-commit (`commit_ticket_ledger_change`) lives entirely in the CLI
dispatch layer (`frob.app.ticket_runner`'s verb table), which a
programmatic caller like the sweep never reaches. This confirms the
THIRD candidate this incident's own investigation named as most likely:
T-1615's uniform auto-commit covers the CLI surface, not programmatic
callers -- a wider gap than this one call site, filed separately (see
this section's own citation below for the real id) so the next
detached/programmatic ledger writer does not rediscover the same hole.

`_commit_regression_ticket` closes THIS call site: after `new_ticket`
succeeds, it calls `commit_ticket_ledger_change` directly -- the SAME
scoped `git add <ledger pathspecs> && git commit -- <ledger pathspecs>`
primitive `frob ticket new`/`drop`/`fail`/`start` already funnel
through, never a bare `git commit`/`git add -A` (T-1740's own incident:
a blanket add on a root checkout concurrent lands are racing against
published 1416 lines of another agent's in-flight work under an
unrelated commit message). A commit failure is logged at ERROR, naming
the regression ticket id and stating explicitly that the next land will
refuse with `DirtyMain` -- the sweep's own regression ticket is already
durably filed by the time this runs, so a commit failure here degrades
to "dirty root, logged loudly", never to "the ticket silently
vanishes".

**`describe_root_dirt` now names the likely author, not just the
paths (T-1755).** An agent hitting `DirtyMain` from a dirty `tickets.md`/
`rapid-debt.jsonl` is, per this incident's own root-cause read, always
correctly isolated from root and structurally unable to investigate WHO
left it dirty -- naming the paths alone (T-1698) still left "now what"
unanswered. When EVERY dirty path matches the sweep's own known writes
(`rapid-debt.jsonl`, `tickets.md`), the refusal now says so explicitly:
"likely author: a sweep child that filed something and did not commit
it". A MIXED dirty set (a sweep-owned path plus something else) is
deliberately NOT attributed to the sweep -- misattributing a genuinely
unknown second cause would send the next agent looking in the wrong
place just as surely as no attribution at all.

<!-- frob:describes src/frob/tickets/_land_git_ops.py::_staged_rapid_debt_ticket -->
**Symbolic attribution names the real ticket, not just "the sweep"
(T-1821).** `_staged_rapid_debt_ticket` reads the STAGED
`rapid-debt.jsonl` blob directly (`git show :rapid-debt.jsonl`), parses
its last line, and returns that line's own `"ticket"` field --
`record_rapid_debt` always writes one, so this is read straight off the
content the sweep itself staged, never inferred or guessed. When every
dirty path is sweep-owned and this lookup succeeds, `describe_root_dirt`
names the actual ticket: "the sweep child working T-XXXX" instead of the
generic "a sweep child that filed something and did not commit it"
T-1755 introduced. If the blob is unreadable, empty, or its last line
does not parse as JSON with a string `"ticket"` value, the function
returns `None` and the refusal falls back to "unattributed (cannot be
determined from staged content)" -- a deliberate refusal to report a
plausible-but-wrong ticket id (the T-1795/T-1799 incident this guards
against was exactly a confident wrong guess).

### Automatic stale-worktree reclamation (T-2261)

<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::sweep_stale_worktrees_after_land -->

Before T-2261, `frob worktree sweep` (`sweep_worktrees`, `src/frob/
tickets/_leases.py`) was sound but never invoked automatically -- every
call site was advisory (`frob.app.ticket_runner._land_cmd` printed "run
`frob worktree sweep` later to clean it up") or the CLI wiring itself.
Measured: 107 worktrees / 67GB accumulated, with `--dry-run --min-age 4`
showing 71 safely removable by the tool's own verdicts.

`_sweep_async` (the detached child `spawn_deferred_post_land_sweep`
already spawns per land, above) now also calls `sweep_stale_worktrees_
after_land` after the gate-check sweep, unconditionally -- STILL off the
land's own critical path (T-1684's whole point), never a second spawn.
It is a thin, faithful wrapper: `sweep_worktrees(root, min_age_hours=4.0,
dry_run=False, force=False)`, reusing its five keep verdicts
(`kept:live`/`kept:dirty`/`kept:unlanded`/`kept:lease`/`kept:age`, each
already covered by real fixtures in `tests/test_ticket_leases.py`)
unmodified rather than reimplementing or narrowing them -- `force` is
never `True` on this path. Every verdict (removed or kept, with its
reason) is logged. `min_age_hours=4.0` matches the ticket's own measured
`--dry-run --min-age 4` precedent.

### Doable-time revalidation of sweep-filed tickets (T-2006)

<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::revalidate_dispatchable_sweep_tickets -->

T-1983's auto-drop (`_close_resolved_sweep_tickets`, above) works
correctly, but its call site is INSIDE a deferred sweep, which only
runs after SOME land -- any land, not necessarily one related to the
stale ticket. In the window between a sweep-filed ticket's identities
getting fixed (by another agent, or a Tier-A auto-fix) and the next
unrelated land's sweep, the ticket sits dispatchable and unverified --
exactly when a coordinator reads `frob ticket doable` and dispatches
it. Measured twice on 2026-08-10: T-2000 (already-fixed, no later
sweep had run, dropped by hand) and T-1998 (misattributed AND
mostly-already-fixed, cost a full dispatch cycle for one real line of
work).

`revalidate_dispatchable_sweep_tickets` is called from `frob ticket
doable`'s own render path (`_query._doable`) with the full candidate
ticket set, BEFORE the dispatchable filter runs -- deliberately NOT a
full unscoped sweep (T-1684's whole point stays off this path) and NOT
gated on `start` (too late -- the dispatch decision already happened by
then). It shares the SAME drop mechanism as T-1983's
`_close_resolved_sweep_tickets` (`_maybe_drop_resolved_ticket`), just at
a different call-site timing:

- Zero-cost when `tickets` contains no sweep-filed candidate at all
  (`_parse_sweep_ticket_identities` returns `None` for everything) --
  the overwhelmingly common case, so a plain `frob ticket doable` pays
  nothing extra most of the time.
- When at least one candidate exists, spawns exactly ONE re-check
  (`_identities_still_reproducing`) scoped to the UNION of every
  candidate's own recorded identities -- never a full sweep -- and
  drops any candidate whose full identity set is now a subset of what
  vanished.
- An unmeasurable re-check (spawn refused, timeout) drops nothing,
  matching T-1983's own "never treat unmeasurable as resolved" rule.
- The measured cost of the one re-check is always logged.

