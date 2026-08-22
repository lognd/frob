## Done report

T-2292: `reconcile --apply` demoted T-2276 from in-progress to queued
while its worktree and agent were both live and its land was about to
run/in flight (real incident, 9246d4b5a/2d854269c). Root cause:
`_stale_in_progress_ticket_ids` judged a hold stale purely from lease
ABSENCE (`ticket_id not in leased_ticket_ids`), with no independent
corroboration -- a momentarily-absent or -reclaimed lease read the same
as a genuinely dead one.

Fix (src/frob/tickets/_reconcile.py): a ticket is only requeued if
BOTH of two additional, independent signals also agree the hold is dead:

1. `_live_worktree_ticket_ids(root)` (new): parses `git worktree list
   --porcelain` and matches each live worktree's own branch name against
   `_DEFAULT_WORKTREE_BRANCH_RE` (`t-####` or `t-draft-xxxxxxxx`) -- the
   exact convention `frob ticket work`/`start` always cuts a worktree
   under (`_default_work_worktree`, `frob.app.ticket_runner._lifecycle`).
   A ticket whose default-convention worktree is still on disk is never
   requeued, independent of what the lease file reads.
2. `_land_in_progress_for_ticket(root, ticket_id)` (reused from
   src/frob/tickets/_leases.py, the same T-1619 land-process/flock scan
   `refuse_if_land_in_progress` already runs) -- a ticket currently being
   landed is never requeued either, per-ticket, as belt-and-braces
   alongside T-2291's own whole-`apply` guard.

Both checks are best-effort, narrowing false positives only (a ticket
resumed under a non-default branch name, or with no matching signal,
falls back to the pre-existing lease-only behaviour unchanged) -- per
the ticket's own "false positive is the dangerous direction" framing, a
ticket is now requeued only when NONE of the three signals (lease,
worktree-branch, land-process) shows it alive.

`_stale_in_progress_ticket_ids` gained two new parameters (`root`,
`live_worktree_ticket_ids`); split `_live_worktree_ticket_ids` into its
own top-level helper to keep both functions under ARCH001's line
threshold.

Positive controls (tests/test_ticket_reconcile.py,
TestReconcileLiveWorktreeShield):
- test_live_default_worktree_with_no_lease_is_never_requeued: cuts a
  REAL `git worktree` on the exact `t-####` branch convention, transitions
  it IN_PROGRESS, then calls `release_lease` directly to simulate the
  lease reading momentarily absent WITHOUT removing the worktree.
  Confirmed genuinely fails at parent (64b2fcc6c, before the fix):
  AssertionError -- T-0001 WAS requeued. Passes after the fix: report.
  requeued_tickets is empty, ledger state stays IN_PROGRESS.
- test_still_requeues_a_genuinely_gone_worktree: must-still-pass control
  -- once the worktree is ACTUALLY `git worktree remove --force`d (the
  ordinary crashed-agent shape), the same ticket IS requeued exactly as
  before, proving the new shield does not widen into "never requeue a
  default-branch-named ticket".

--designate-repro validated FAILED_AT_PARENT against 64b2fcc6c.
Full tests/test_ticket_reconcile.py (16/16) and tests/test_ticket_leases.py
(134/134) both pass with the fix.

### Changed
```
 src/frob/tickets/_reconcile.py | 80 ++++++++++++++++++++++++++++++++++++++++--
 tests/test_ticket_reconcile.py | 77 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-2292/ticket.md       | 13 ++++---
 3 files changed, 163 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_ticket_reconcile.py::TestReconcileLiveWorktreeShield::test_live_default_worktree_with_no_lease_is_never_requeued` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileLiveWorktreeShield::test_still_requeues_a_genuinely_gone_worktree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2291/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2291/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2291/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2291/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2291/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2292, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
