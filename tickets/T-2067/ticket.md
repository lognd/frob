---
id: T-2067
title: 'PERF004 false-positive: unnecessary sorted() in orphan-dir equality check
  (T-2046 follow-through)'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
  reason: same guard's own test file
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_extra_file_sorting_before_ticket_md_is_never_committed
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing
designated_repro_test: null
acceptance:
- text: PERF004 must be absent from frob check --only perf for src/frob/tickets/_land.py,
    measured before and after
  evidence:
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_extra_file_sorting_before_ticket_md_is_never_committed
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing
- text: 'T-2046''s own acceptance still holds: two valid dirs commit, mixed dirty
    tree declines fully, non-parsing dir yields no commits'
  evidence:
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_extra_file_sorting_before_ticket_md_is_never_committed
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing
- text: dispose the raised verify quarantine once fixed
  evidence:
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_extra_file_sorting_before_ticket_md_is_never_committed
threat: null
component: null
anchor: false
anchor_reason: null
---
Coordinator-directed fix: PERF004 flags src/frob/tickets/_land.py:1999's sorted() as a loop-invariant-hoist candidate; it is not loop-invariant (each iteration sorts a different directory), but the sort itself is unnecessary -- entries is only compared with != against a single-element list, so order never matters. Delete sorted(), keep a test that the guard still refuses a directory with more than ticket.md (order-irrelevant since it's a set-membership question in disguise). Raised the T-1693 verify quarantine on T-2046's land commit 38074dd92c2c; must be disposed once fixed.