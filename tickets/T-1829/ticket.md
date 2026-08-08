---
id: T-1829
title: '5 tests/test_ticket_land.py tests fail: new_ticket auto-commit (T-1758) leaves
  _commit_all with nothing to stage'
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_renumber.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Discovered while working T-1736 (unrelated scope). On a clean worktree at current main tip, these 5 tests fail with subprocess.CalledProcessError on 'git commit -q -m wip'/'file...' (exit 1, nothing to commit): TestLand::test_refuses_without_evidence_or_done_report, TestLedgerBothSidesAppend::test_both_sides_append_merges_cleanly, TestArchiveResurrection::test_archived_id_never_resurrected, TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive, TestMergeMainIntoWorktreeRicherState::test_landing_tickets_in_progress_report_survives_the_merge_stage. Each calls new_ticket(...) then _commit_all(wt, 'wip'/'file...') immediately after -- since T-1758 made new_ticket auto-commit internally by default, the ledger write is already committed by the time _commit_all's own 'git add -A && git commit' runs, so there is nothing left to stage and the commit fails. Reproduced in isolation (not a parallelism/xdist artifact), unrelated to _land.py content itself -- these tests fail in setup, before land() is ever called. Fix is either updating these 5 tests to pass no_commit=True to new_ticket (matching the T-1758-era pattern _file_regression_ticket itself already uses) or to drop their now-redundant _commit_all call.