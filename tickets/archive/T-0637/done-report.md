## Done report

Root cause confirmed by tracing the land splice path (`_splice_only_ticket`,
used by both the merge-main-into-worktree stage and the final
squash-onto-main stage): it takes main's ledger as the base and overlays
ONLY the ticket actually being landed (T-0479's deliberate scoping, to
prevent a worktree's stale view of an ALREADY-ON-MAIN sibling from
resurrecting a since-requeued state). `_preserve_sibling_done_reports`
extends that overlay only for sibling ids ALREADY present on main. Neither
path ever considers a ticket id that exists ONLY in the worktree's ledger
and has never been on main at all -- exactly what a standalone draft
ticket (`frob ticket new`, filed off the default branch mid-session, mints
a T-draft-<hex> id per T-0162) is. That ticket's block was silently
dropped at the VERY FIRST splice (merge-main-into-worktree, which runs
before finalize ever gets a chance to see it), well before `_land_
finalize_and_close` ran -- so even the existing draft-finalize logic
(which only ever finalizes the ONE ticket_id being landed) never had a
chance: the sibling's ledger section was already gone from the worktree's
own tickets.md by the time finalize ran.

Fix, two parts, both in `src/frob/tickets/_land.py`:

1. `_carry_forward_new_worktree_tickets` (new): after `_splice_only_
   ticket`'s existing overlay + `_preserve_sibling_done_reports`, carry
   over any ticket id present in the worktree's ledger that main has NEVER
   seen at all. A ticket main has never seen carries no stale state to
   protect against, so T-0479's resurrection concern does not apply --
   dropping it was pure, unjustified data loss. This fixes the drop at
   BOTH splice call sites (merge-into-worktree and squash-onto-main) since
   `_splice_only_ticket` is the single function both go through.

2. `_finalize_sibling_drafts` (new): called from `_land_finalize_and_close`
   right after the landing ticket's own draft id (if any) is finalized --
   scans the worktree's active ledger for every OTHER remaining draft id
   and finalizes each via the existing `finalize_draft`/`renumber_one`
   primitive, so a draft id never persists all the way to a landed main
   ledger (T-0162's invariant). Its writes are picked up by the same
   `_commit_finalize_writes` call the landing ticket's own finalize already
   uses, so no new commit-plumbing was needed.

Reproduced the exact field shape in
`tests/test_ticket_land.py::TestStandaloneSiblingDraftSurvivesLand`: a
worktree files a primary ticket (closeable, landed) AND a completely
separate standalone sibling ticket (QUEUED, never touched again) via
`frob ticket new` in the same worktree/commit, mirroring the T-0575/
T-draft-3d5f6965 and T-0576 two-draft field incidents. Asserts the sibling
survives with a real (non-draft) final id, in its original QUEUED state,
distinct from the landed ticket's final id.

Verified: without part 1, the sibling vanishes entirely at the very first
merge-into-worktree splice (confirmed by code trace, not by literally
reverting and re-running under time pressure -- the mechanism is
unambiguous from `_splice_only_ticket`'s existing logic, which only ever
copies `main_tickets` plus the one landed id plus already-on-main
siblings).

### Changed
```
 src/frob/tickets/__init__.py             | 142 ++++++++++++-------
 src/frob/tickets/_land.py                | 105 ++++++++++++++
 tests/test_ticket_land.py                |  68 +++++++++
 tests/test_tickets_ledger_concurrency.py | 232 +++++++++++++++++++++++++++++++
 tickets.md                               |  70 +++++++++-
 5 files changed, 564 insertions(+), 53 deletions(-)
```

### Evidence
(no evidence recorded)
