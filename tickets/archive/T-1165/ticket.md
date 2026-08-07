---
id: T-1165
title: 'gates: wire git merge-driver''s %O merge-base into splice_ledger''s base_text
  (T-1154 follow-up)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land.py
- tests/test_ticket_merge_driver.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_merge_driver.py
  reason: T-1165's regression test for the merge-driver base_text fix lives in the
    merge-driver's dedicated test file, not test_ticket_land.py
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1165 changes _merge_driver's documented base(%O)-argument behavior; docs/modules/tickets.md#git-merge-driver
    describes it and AFFECT001 requires the doc touched in the same diff
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_disjoint_ids_both_survive_the_splice
- tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_same_id_newer_state_wins_and_is_written_back
- tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_malformed_theirs_exits_nonzero_and_leaves_ours_untouched
- tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_missing_args_exits_nonzero
- tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_base_o_arg_prevents_wrong_side_merge_via_live_driver
- tests/test_ticket_merge_driver.py::TestMergeDriverHandler::test_missing_base_file_degrades_to_newer_only_tiebreak
- tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit::test_real_git_merge_auto_splices_both_sides_append
designated_repro_test: null
threat: null
component: null
---
T-1154 fixed the wrong-side-merge tie-break in _merge_ledger_tickets/splice_ledger by threading a base_text (true 3-way merge-base) param through, and wired it into frob ticket land's own tickets-archive.md splice via _true_merge_base. The frob ticket merge-driver CLI entry point (_land_cmd.py::_merge_driver) already receives git's own %O merge-base argument (cfg.ticket_merge_base) but discards it -- splice_ledger is called with only ours/theirs text. Thread ticket_merge_base's file content through as splice_ledger's new base_text param so a live git merge (not just frob ticket land's own internal merge step) gets the same wrong-side-merge protection. Concretely observed live during T-1154's own worktree warm-up: a bare (stale, non-uv-run) frob ticket merge-driver invocation reverted T-1111 from done to queued via exactly this unfixed tie-break.