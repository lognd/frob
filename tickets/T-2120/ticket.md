---
id: T-2120
title: 3 test fixtures hit 'nothing to commit' after new_ticket's T-1758 internal
  auto-commit
state: done
kind: bug
origin: agent
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_merge_driver.py
- tests/unit/test_land_cross_ticket_leakage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append
- tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_queued_sibling_scope_overlap_does_not_block
designated_repro_test: tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append
acceptance:
- text: Given new_ticket's T-1758 internal auto-commit, when the 3 named fixtures
    run, then they pass no_commit=True to new_ticket so their own _commit_all call
    has something to commit again
  evidence:
  - tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append
  - tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk
  - tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_queued_sibling_scope_overlap_does_not_block
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
GROUP 4: three fixtures call `new_ticket(...)` then their own
`_commit_all(root, message)` (`git add -A && git commit`), and now hit
"nothing to commit, working tree clean" (`git commit` exits nonzero,
`_run`'s `check=True` raises) because `frob.tickets._new_renumber.
new_ticket` (T-1758) auto-commits the ledger write internally by
default -- the fixture's own follow-up commit finds nothing left
staged.

  tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append
  tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk
  tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_queued_sibling_scope_overlap_does_not_block

Reproduced directly (not from the symptom): ran each test, confirmed
the exact `git commit` failure via `-o addopts="" -q` full log.

Fix: pass `no_commit=True` to each `new_ticket(...)` call in these
three fixtures (mechanical, not a design change) -- the fixture's own
`_commit_all` still does the real commit immediately after, same net
effect as before T-1758, just skipping the now-redundant internal
commit. Matches the established fix pattern already used elsewhere in
this exact test suite for this exact shape
(`tests/test_ticket_land.py`, `tests/test_serve_tools_daemon_bypass.py`
-- `new_ticket(..., no_commit=True)` followed by the fixture's own
commit).

## Done report

### Changed
tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit.test_real_git_merge_auto_splices_both_sides_append
tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit.test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk
tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage.test_queued_sibling_scope_overlap_does_not_block

### Evidence
tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append
tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk
tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_queued_sibling_scope_overlap_does_not_block

Full test_ticket_merge_driver.py re-verified: 9 passed. Full
test_land_cross_ticket_leakage.py re-verified: 17 passed.

### Root cause
`frob.tickets._new_renumber.new_ticket` (T-1758) auto-commits the
ledger write itself by default before returning. All three fixtures
called `new_ticket(...)` (default args) then their own `_commit_all`
(`git add -A && git commit`) immediately after -- with nothing left
staged, `git commit` exits nonzero ("nothing to commit, working tree
clean") and `_run`'s `subprocess.run(..., check=True)` raises.

### Fix
Passed `no_commit=True` to the 3 affected `new_ticket(...)` calls (2 in
`test_ticket_merge_driver.py`, 1 in
`test_land_cross_ticket_leakage.py` -- that file's OTHER `new_ticket`
calls followed by a real file write + `_commit_all` already had
something to commit and were unaffected, confirmed by running the
full file both before and after touching only the one call). Purely
mechanical: `_commit_all` still performs the real commit immediately
after, same net effect as before T-1758. Matches the fix pattern
already established elsewhere in this exact test suite for this exact
shape (`tests/test_ticket_land.py`, `tests/test_serve_tools_daemon_bypass.py`).

A `ruff format` pass on both touched files was needed after the edit
(the new `no_commit=True` kwarg pushed two call sites over the line-
length wrap point) -- applied directly, re-verified both files still
pass their full suite afterward.

### Gates
`frob ticket evidence --check-repro` on all 3 node ids, against the
pre-fix commit (`af4c8c9c65a6559ae68e7a57b41f8a4e04b686b6`): all 3
genuine FAILED_AT_PARENT. Designated the first as this ticket's repro.

Filed: none.

### Changed
```
 tests/test_ticket_merge_driver.py            | 16 ++++++++++++----
 tests/unit/test_land_cross_ticket_leakage.py | 15 ++++++++-------
 tickets/T-2120/ticket.md                     | 13 ++++++++++---
 3 files changed, 30 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_queued_sibling_scope_overlap_does_not_block` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-2120/src/frob/gates/_root_asset_dirs.py, PRE001@tickets/T-2120, TICK004@tickets.md
