## Done report

Fixed two worktree-workflow defects found on the first land onto dev.

1. T-4492's own declared defect: frob ticket work branched worktrees from a literal 'main' (git worktree add -b <branch> main) and refreshed them with a literal git merge main; the worktree sweep counted unlanded commits with a literal main..branch rev-list. Added _resolve_default_ticket_branch (src/frob/tickets/_land.py, next to T-3787's _resolve_land_target_branch) returning root's own current branch, falling back to ticket_land_branch config, then the literal main. Wired through _worktree_add_or_reuse/_ensure_worktree_fresh (src/frob/app/ticket_runner/_lifecycle.py) and _branch_ahead_of_main_count (src/frob/tickets/_worktree_sweep.py). Repro test confirmed FAILED_AT_PARENT against 322dc4aa5. Root-on-main/no-config behavior unchanged.

Out of declared scope: did NOT touch evidence/done-report --base-ref defaults or _unlanded.py's three-dot diff -- neither is in this ticket's declared scope/acceptance; fixing safely needs re-threading cfg.ticket_base_ref through several downstream consumers, a larger separate change.

2. Coordinator-directed second defect, same root cause: _find_leaked_tickets called read_all_leases once per candidate sibling (twice per candidate before the hoist) -- measured minutes per call, ~800 candidates, no land finished its precheck. Hoisted one read_all_leases(root) call before the loop, threaded as a leases parameter. Added tests/unit/test_land_leaked_tickets_lease_hoist.py asserting at most one call across 8 candidates.

Verification: all touched-file tests plus tests/test_ticket_work_and_land_finish.py, tests/test_ticket_lifecycle.py, tests/test_ticket_leases.py, tests/unit/rapid_sweep_suite/test_worktrees.py, tests/unit/test_unlanded_branch_work.py, tests/unit/test_land_cross_ticket_leakage.py, tests/unit/test_cross_ticket_leakage_gate.py, tests/unit/test_land_step_ordering.py, tests/unit/test_land_machinery_owned_leakage.py pass, 0 failures. frob check --ticket T-4492 (5-25 min per run under heavy fleet contention) reduced to errors that are (a) pre-existing/repo-wide per the tool's own scope-note, (b) an artifact of check's OWN diff-base computation counting sibling tickets filed via dev-merge as touched (gate:SCOPE SCOPE001 on other tickets ticket.md files -- the same literal-main-diff bug class this ticket fixes, but inside check itself, out of scope), or (c) a genuine documented limitation: SELFAUDIT001 always attributes to design_dir:1 (Violation(file=design_dir, line=1) in _sys_selfaudit.py), never the observed source line, so no in-source waive can suppress it; the real fix (declaring 2 new capability sites in design/frob.strata's testsuite node) needs an edit to a file T-draft-725f3c4c has leased for its whole work window. Filed T-4497 as follow-up, same precedent as src/frob/gates/_narrative_blocks.py's existing T-2989/T-3020 waiver for the identical lease-conflict shape.

### Changed
```
 src/frob/app/ticket_runner/_lifecycle.py           |  79 +++++---
 src/frob/tickets/_land.py                          |  99 +++++++++-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  96 +++++++++
 tests/unit/test_lifecycle_work_base.py             | 220 +++++++++++++++++++++
 tickets/T-4492/ticket.md                 |  34 +++-
 tickets/T-4497/ticket.md                 |  30 +++
 7 files changed, 534 insertions(+), 41 deletions(-)
```

### Evidence
- `tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch::test_worktree_head_contains_devs_own_tip_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_lifecycle_work_base.py::TestWorktreeSweepCountsAgainstResolvedTarget::test_counts_commits_ahead_of_dev_not_ahead_of_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch::test_byte_for_byte_historical_when_root_is_on_main_no_config` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_leaked_tickets_lease_hoist.py::TestFindLeakedTicketsHoistsReadAllLeases::test_read_all_leases_called_at_most_once_across_many_candidates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 4954 warning(s), 983 waived
- error-findings: SELFAUDIT001@tests/unit/test_lifecycle_work_base.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4496.json
