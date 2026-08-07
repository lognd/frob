---
id: T-0682
title: 'ticket merge driver: splice_ledger still prefers main''s stale queued block
  over worktree''s in-progress+report'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: high
parent: T-0577
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference::test_report_side_still_wins_when_it_also_outranks_the_reportless_side
- tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference::test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side
- tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference::test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on
- tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference::test_neither_side_reporting_still_falls_back_to_state_rank
- tests/test_ticket_land.py::TestMergeMainIntoWorktreeRicherState::test_landing_tickets_in_progress_report_survives_the_merge_stage
designated_repro_test: null
acceptance:
- text: GIVEN a worktree ledger with the landing ticket in-progress plus Done report
    and main's copy queued WHEN the merge driver splices during land THEN the in-progress
    state and report both survive without manual repair
  evidence: []
threat: null
component: null
---
T-0577 fixed _splice_only_ticket (land path) to preserve the richer sibling state, but the GIT MERGE DRIVER path (splice_ledger, used when land merges main INTO the worktree, and by any git merge/pull touching tickets.md) still prefers main's stale block: observed twice landing T-0633/T-0637 -- each 'merge main into worktree for landing' regressed the LANDING ticket's own block to queued (report survived, state+start lost), forcing a manual start+commit repair before every land. Port the richer-state preference (Done-report presence, in-progress beats bare queued) into splice_ledger with the same direction tests as T-0577's, and add a land-path integration test that the landing ticket's own state survives the merge stage.