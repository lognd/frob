## Done report

T-1522: `land_plan`'s (`src/frob/tickets/_land.py`) failure-unwind path no
longer resets `root` all the way back to its pre-merge tip once the merge
commit exists. The merge commit is the queue-drain checkpoint on a shared
design-phase worktree branch -- it already durably carries every other
ticket's content the branch accumulated -- so a LATER, unrelated failure
in the SAME invocation (a finalize error, a dirty `check_ticks()` result)
now unwinds only what was committed AFTER the merge (new helper
`_land_plan_unwind_after_merge`), never the merge itself. This is the
2026-08-04 T-1199/T-1200 incident shape (tickets-archive.md) directly:
those tickets' already-merged content was discarded by two retried
`land_plan` attempts because the unwind reset past the merge commit on an
unrelated later failure. `dry_run`'s own always-revert behavior is
unchanged -- a dry run is deliberately "run then always revert", not a
failure path.

Updated two pre-existing tests whose assertions encoded the OLD (buggy)
full-unwind behavior (`test_tick_gate_dirty_unwinds_everything` ->
`test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge`,
`test_no_foreign_commit_unwinds_cleanly_as_before` ->
`test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge`), and
added a new `TestLandPlanQueueDrainCommitsDurable` test class that
reproduces the T-1199/T-1200 shape directly: a finalize failure injected
via monkeypatch AFTER a real merge commit, asserting the merge content
(a doc file) survives and a follow-up retry is a clean no-op.

### Changed
```
 src/frob/tickets/_land.py         | 30 ++++++++-----
 src/frob/tickets/_land_git_ops.py | 49 +++++++++++++++-------
 tests/test_ticket_land.py         | 65 +++++++++++++++++++++++++++++
 tickets.md                        | 88 +++++++++++++++++++++++++++++++++++++--
 4 files changed, 205 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandPlanQueueDrainCommitsDurable::test_finalize_failure_after_merge_keeps_the_merge_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlan::test_dry_run_unwinds_the_merge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 362 warning(s), 790 waived
- error-findings: none (measured, zero errors)
