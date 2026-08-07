---
id: T-1370
title: CrossTicketLeakage mutually deadlocks tickets sharing one series worktree
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_cross_ticket_leakage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_does_not_block
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_ticket_already_done_on_main_does_not_block
designated_repro_test: null
acceptance:
- text: GIVEN two complete tickets on one series branch whose scopes overlap WHEN
    either is landed THEN the guard does not refuse solely because the other sibling
    on the same branch is still open
  evidence:
  - tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_does_not_block
threat: null
component: null
---
Hit live 2026-08-01 landing the w1-land series. T-1355's new CrossTicketLeakage guard refused T-1355 because T-1356 was open, and refused T-1356 because T-1355 was open -- a hard mutual deadlock with no CLI escape hatch (T-1369 wires the flag; this ticket is the guard logic itself). The guard has no notion of a series worktree, where several tickets legitimately share one branch and are landed back to back. It should treat siblings whose lease is held by the SAME worktree the way T-1356 taught frob ticket scope to -- as not-a-conflict -- and only refuse for tickets leased elsewhere or unleased. Recovery used this time: T-1358's land merged the whole branch, so the code reached main, and T-1355/T-1356 were closed directly on main after verifying all 19 tests pass there.