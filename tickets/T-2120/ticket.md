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