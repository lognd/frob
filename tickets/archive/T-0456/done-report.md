## Done report

T-0456 is the crash/interrupt recovery epic; T-0473 (cross-worktree lease
registry + liveness guard), T-0476 (frob ticket reconcile: stale-hold
requeue + orphan-worktree flag/remove), and T-0479 (land's own-block ledger
splice + out-of-scope conflict auto-resolve) already landed most of the
acceptance surface. What remained genuinely unimplemented, per the ticket
body's own three named mechanisms:

1. ATOMIC ledger writes with fsync. `frob.tickets._store.atomic_write`
   already did temp-file + os.replace (T-0458), but never fsync'd the temp
   file before the rename -- a real gap against the ticket's own "write-temp
   + fsync + atomic rename" design line: os.replace is atomic at the
   filesystem level, but without fsync, a power loss between the write and
   the rename can leave the temp file's data unflushed, so a filesystem
   that journals renames separately from data blocks can replay a rename to
   a not-yet-durable (zero-length/truncated) file. Added `f.flush()` +
   `os.fsync(f.fileno())` before `os.replace`, with an OSError there now
   behaving exactly like an os.replace failure (Err(WriteFailed), no
   partial/leftover file) -- covered by two new tests in
   tests/unit/test_ticket_store.py's existing TestAtomicWrite.

2. INTENT JOURNAL for `frob ticket land` (genuinely missing -- no prior
   ticket built this). New module src/frob/tickets/_journal.py:
   write_intent/clear_intent/read_all_intents/LandIntent/JournalError,
   local to `root` (unlike T-0473's cross-worktree lease side channel,
   since a land only ever mutates the one worktree/root pair it was
   invoked against). land() in src/frob/tickets/_land.py now writes the
   intent record right after precheck (before any of its steps mutate
   anything) and clears it in a `finally` block wrapping the whole
   merge/finalize/squash-apply chain, so the marker is cleared on success,
   on a clean/handled Err, AND on an unhandled exception -- only a process
   that dies before reaching that `finally` (killed, OOM, power loss)
   leaves it behind.

3. Partial multi-step op recovery folded into `frob ticket reconcile`.
   reconcile() (src/frob/tickets/_reconcile.py) gained a third anomaly
   class, orphaned_land_intents: every leftover journal record is reported
   on every run (dry-run or --apply); --apply clears (aborts) them but does
   NOT attempt to automatically resume/roll-forward the interrupted land --
   this is a deliberate, disclosed scope decision, not an oversight: after
   a real crash mid-land, the git/ledger state could be at any of several
   different intermediate points (mid-merge, post-merge pre-close,
   post-close pre-squash, ...), and blindly attempting to "finish the job"
   from just a ticket-id marker risked silently completing an operation
   against un-reverified state. --apply's semantics here are "stop
   treating this as in-flight" (matching the design note's "resume OR
   abort" -- abort was chosen), leaving the ticket/tree exactly where the
   crash left it for a human/agent to inspect and re-run `frob ticket land`
   from scratch. This is the honest boundary of what this ticket's pass
   implements; a follow-up (roll-forward/resume) would need its own
   ticket if wanted, since attempting it here risked exactly the kind of
   silent-and-wrong automated recovery the epic exists to prevent.

Acceptance items already satisfied by landed work (not re-implemented
here): "kill an agent mid-work (in-progress ticket + deleted worktree);
frob ticket reconcile detects it, releases the lease, reverts to
queued... and the freed scope re-appears in doable" -- T-0473 (lease
registry + liveness skip) + T-0476 (reconcile's stale-hold requeue) already
cover this exactly, verified still passing (tests/test_ticket_reconcile.py
TestReconcileStaleHold, unchanged, all green). "The ledger is never left
unreadable" -- T-0458's atomic_write (temp+replace) already covered the
rename-atomicity half; this ticket's #1 above closes the durability half
(fsync) that was still open. Idempotency of start/evidence/close/scope-
change was already true pre-T-0456 (frob ticket start is a documented
no-op on an already-in-progress ticket per T-0474's Done report) and is
unchanged by this pass.

"A simulated crash mid-land (intent record present, merge incomplete) is
detected and cleanly resolved" -- covered by
tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent (dry-run
report + --apply clear), though "cleanly resolved" here means "the stale
marker is cleared, not that a partial merge is auto-repaired" -- see the
disclosed scope decision above; land() itself already has real conflict
handling for its OWN steps (T-0479), this ticket's journal only adds
crash-DETECTION for when the process itself died, which land()'s existing
in-process error handling cannot cover by definition.

Also extended scope for sequential-single-worktree-dispatch SCOPE001 noise
from T-0507's already-committed files (src/frob/app/ack_runner.py,
src/frob/release/__init__.py, the two new test files, tickets-archive.md)
per the T-0431 precedent, and for T-0456's own REL001 bump (new public
frob.tickets._journal API): pyproject.toml 0.52.0 -> 0.53.0,
CHANGELOG.md, .frob-release.json (frob release stamp), uv.lock (uv lock).

Gates: uv run frob check --ticket T-0456 --json -> 0 new errors; remaining
DOC003 (docs/commands/sys.md) and REG003 x5 (docs/design/registry/
weaknesses.yaml) are the same pre-existing repo-wide debt observed and
disclosed in T-0519/T-0507's Done reports, unrelated to any file this
ticket touches. `frob release check` -> "since 0.53.0: none change -> need
>= 0.53.0 (current 0.53.0): OK". ruff check/format clean under BOTH the
PATH ruff and `uv run ruff` for every touched file.

### Changed
```
 .frob-release.json                   |   9 +-
 CHANGELOG.md                         |  21 ++
 docs/modules/tickets.md              |  57 ++++++
 pyproject.toml                       |   2 +-
 src/frob/app/ack_runner.py           |  14 +-
 src/frob/app/ticket_runner.py        |  20 +-
 src/frob/release/__init__.py         |  14 +-
 src/frob/tickets/_journal.py         | 157 +++++++++++++++
 src/frob/tickets/_land.py            |  88 +++++----
 src/frob/tickets/_reconcile.py       |  30 ++-
 src/frob/tickets/_store.py           |  15 +-
 tests/test_ack_worktree_lease.py     |  55 ++++++
 tests/test_release_worktree_lease.py |  52 +++++
 tests/test_ticket_journal.py         |  93 +++++++++
 tests/test_ticket_reconcile.py       |  35 ++++
 tests/unit/test_ticket_store.py      |  51 +++++
 tickets-archive.md                   |  17 +-
 tickets.md                           | 361 ++++++++++++++++++++++++++++++++++-
 uv.lock                              |   2 +-
 19 files changed, 1022 insertions(+), 71 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestAtomicWrite::test_fsyncs_file_before_replace` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestAtomicWrite::test_fsync_failure_is_write_failed_not_a_partial_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestWriteIntent::test_write_then_read_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestWriteIntent::test_write_failure_returns_err` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestClearIntent::test_clear_removes_the_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestClearIntent::test_clear_missing_file_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestReadAllIntents::test_reads_every_recorded_intent` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestReadAllIntents::test_no_journal_dir_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestReadAllIntents::test_malformed_record_is_skipped_not_fatal` (pytest node id, verified passing when recorded)
- `tests/test_ticket_journal.py::TestLandIntent::test_model_round_trips_via_json` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent::test_dry_run_reports_but_does_not_clear` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent::test_apply_clears_the_orphaned_intent` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent::test_no_intents_reports_empty` (pytest node id, verified passing when recorded)
