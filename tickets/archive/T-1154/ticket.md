---
id: T-1154
title: 'land: take main''s side for ledger/archive files the ticket did not deliberately
  edit (wrong-side-merge corruption, 3rd occurrence)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish
- tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected
- tests/test_ticket_land.py::TestSpliceLedger::test_malformed_ours_propagates_as_err
- tests/test_ticket_land.py::TestSpliceLedger::test_malformed_theirs_propagates_as_err
- tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins
- tests/test_ticket_land.py::TestSpliceOnlyTicket::test_whole_ledger_splice_never_regresses_a_sibling_from_done
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
designated_repro_test: null
acceptance:
- text: GIVEN a worktree whose tickets-archive.md (or tickets.md blocks outside the
    landing ticket's own edits) is merely stale relative to main WHEN frob ticket
    land merges THEN main's newer content wins wholesale and the landed diff contains
    no reversion of main-side ledger/archive content the ticket never touched
  evidence:
  - tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
- text: GIVEN a ticket that DID deliberately edit tickets-archive.md (e.g. an evidence-path
    migration) THEN its edits land normally -- staleness detection distinguishes unchanged-since-branch
    from deliberately-edited
  evidence:
  - tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
threat: null
component: null
---
Third occurrence of the wrong-side-merge corruption class (standing rule: 3rd hit files the root-cause ticket on the merge path). Latest instance: T-1145's land bc834b95 reverted T-1143's tickets-archive.md evidence-path migration (40 parse.rs -> parse/mod.rs occurrences reintroduced) because the worktree's stale archive copy won the merge; T-1153 documents the damage. Two prior agent-observed instances noted in wave 9. T-0959's splice guard covers archive BLOCK LOSS; this is content regression. Detection: compare the worktree file to the merge-base version -- unchanged-in-worktree means the worktree has no claim, take main's side.