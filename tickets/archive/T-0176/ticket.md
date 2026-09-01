---
id: T-0176
title: 'frob ticket land: one-command landing (merge-check-splice-close-commit)'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0162
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
- docs/modules/tickets.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/ticket_land_suite/test_ledger_splice.py::TestSpliceLedger::test_disjoint_ids_both_kept
- tests/ticket_land_suite/test_ledger_splice.py::TestSpliceLedger::test_same_id_newer_state_wins
- tests/ticket_land_suite/test_land_core.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace
- tests/ticket_land_suite/test_land_core.py::TestLand::test_real_land_lands
- tests/ticket_land_suite/test_land_core.py::TestLand::test_refuses_on_dirty_main
- tests/ticket_land_suite/test_land_core.py::TestLand::test_refuses_without_evidence_or_done_report
- tests/ticket_land_suite/test_land_core.py::TestStaleBaseDeletion::test_unowned_deletion_aborts_loudly
- tests/ticket_land_suite/test_land_core.py::TestStaleBaseDeletion::test_scoped_deletion_is_allowed
- tests/ticket_land_suite/test_ledger_splice.py::TestLedgerBothSidesAppend::test_both_sides_append_merges_cleanly
- tests/ticket_land_suite/test_draft.py::TestDraftIdFinalization::test_draft_id_finalized_on_land
- tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
- tests/ticket_land_suite/test_draft.py::TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean::test_code_directive_rewritten_and_worktree_clean_after_land
- tests/ticket_land_suite/test_archive.py::TestArchiveResurrection::test_archived_id_never_resurrected
designated_repro_test: null
threat: null
component: null
---
The landing procedure is manual coordinator surgery repeated per ticket: wip-commit in the worktree, merge main, deletion-filter check (git diff main --diff-filter=D must be empty of unowned files), squash-apply, ledger splice on conflict, close with evidence validation, conventional commit. Implement frob ticket land <id> --worktree <path> doing the whole chain atomically with a dry-run mode: refuses on a dirty main, runs the deletion check and ABORTS loudly listing unowned deletions (the stale-base guard), auto-splices tickets.md keeping newest state per ticket section, finalizes provisional ids via the T-0162 mechanism (hence blocked_by), closes the ticket (evidence+done-report validation as today), and commits with a message template. Every abort path must name the exact manual remedy. Tests: fixture repo with a worktree simulating the real incident classes from this session (stale base deleting landed features, ledger both-sides-append conflict, id finalize).
