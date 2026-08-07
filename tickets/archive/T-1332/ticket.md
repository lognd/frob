---
id: T-1332
title: 'land waive-guard: test branch-merged-main deletion attribution and rename-aware
  paths'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_ticket_land.py
- src/frob/tickets/_land_merge.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_branch_merges_main_after_main_deletes_a_waiver_still_allowed
- tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_committed_waiver_deleted_inside_a_rename_attributes_to_old_path
- tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_committed_waiver_deleted_inside_a_rename_out_of_scope_still_refuses
- tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_uncommitted_waiver_deleted_inside_a_rename_attributes_to_old_path
designated_repro_test: null
acceptance:
- text: GIVEN a branch that merged main after main legitimately deleted a waiver WHEN
    land runs THEN no refusal occurs (locked by test)
  evidence:
  - tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_branch_merges_main_after_main_deletes_a_waiver_still_allowed
  - tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_committed_waiver_deleted_inside_a_rename_attributes_to_old_path
  - tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_committed_waiver_deleted_inside_a_rename_out_of_scope_still_refuses
  - tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_uncommitted_waiver_deleted_inside_a_rename_attributes_to_old_path
- text: GIVEN a waiver deleted inside a file renamed in the same branch THEN the guard
    attributes the deletion to a path that scope-ownership evaluates correctly (test
    proves which)
  evidence:
  - tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_branch_merges_main_after_main_deletes_a_waiver_still_allowed
  - tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_committed_waiver_deleted_inside_a_rename_attributes_to_old_path
  - tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_committed_waiver_deleted_inside_a_rename_out_of_scope_still_refuses
  - tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_uncommitted_waiver_deleted_inside_a_rename_attributes_to_old_path
threat: null
component: null
---
Two verification gaps flagged at T-1326 review (both inherited/analysis-only today): (1) no test exercises a branch that runs git merge main AFTER main legitimately deleted a waiver, then lands -- the committed-history guard is safe by git merge-base construction (the merge advances the base past main's deletion) but nothing locks that in; every agent worktree merges main mid-flight, so a regression here would break all lands. (2) rename-aware attribution: _waive_deletions_in_diff takes the pre-image path from the hunk header; a waiver deleted inside a renamed file has untested scope-ownership attribution (pre- vs post-rename path) on BOTH the uncommitted (T-1323) and committed (T-1326) checks. Add tests for both; fix attribution if the rename test exposes a wrong-path bug.