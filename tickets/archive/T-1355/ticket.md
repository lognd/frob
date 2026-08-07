---
id: T-1355
title: land merges the whole branch diff, leaking a sibling ticket's work onto main
state: done
kind: bug
origin: agent
created: '2026-07-31'
priority: high
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- docs/modules/tickets.md
- src/frob/tickets/_models.py
- tests/unit/test_land_cross_ticket_leakage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: add LandError.CrossTicketLeakage variant for the new preflight check
  actor: logan
  at: '2026-08-01'
- op: add
  glob: tests/unit/test_land_cross_ticket_leakage.py
  reason: regression tests for the T-1355 cross-ticket leakage preflight
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_ticket_already_done_on_main_does_not_block
designated_repro_test: null
acceptance:
- text: given a worktree hosting two tickets where one is deliberately open, when
    the other lands, then the open ticket's committed work does not silently reach
    main
  evidence:
  - tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open
  - tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal
  - tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly
  - tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_ticket_already_done_on_main_does_not_block
threat: null
component: tickets
---
Leaf of T-1344. Discovered 2026-07-31 during the batched parallel drive.

THE DEFECT: `frob ticket land` merges the ENTIRE BRANCH DIFF, not the landing ticket's declared scope. When one worktree hosts more than one ticket -- which is exactly what SERIES/BATCHED dispatch mandates -- landing ticket B carries ticket A's already-committed work onto main with it, even when A is deliberately still open.

OBSERVED: worktree t-1276 hosted T-1276 (paused, coverage-blocked) and T-1352 (an independent INV006 fix, split out precisely so it could land alone). Landing T-1352 at 5b02a25e carried T-1276's src/frob/app/doctor_runner.py frob:tests edges and its new 148-line tests/unit/test_doctor_runner_t1276.py onto main. T-1276's ledger state on main is still "in-progress".

WHY IT MATTERS: main now contains code whose ticket is unclosed. That is precisely the unaccounted-for work frob exists to make impossible -- the ledger says the work is in flight while the code says it shipped. Nothing FALSE landed here (the tests are real, verified, and passing), so this instance is benign, but the mechanism is not: it can land a sibling's half-finished or deliberately-withheld work, and it silently defeats any decision to hold a ticket back.

The hazard scales with batching. Series worktrees are now standing policy (they amortize agent cold-start), so every series is exposed on every land except the last.

DESIGN QUESTIONS -- answer, do not assume:
- Can land restrict its merge to paths within the landing ticket's declared scope? Cleanest in principle, but a real change to land semantics, and scope globs are often broader than the actual edit.
- Or should land REFUSE (or loudly warn) when the branch contains committed changes attributable to a DIFFERENT open ticket in the same worktree, naming them and forcing an explicit decision?
- Or should a paused ticket's work be parked (separate branch / explicit un-stage) rather than sitting committed on a shared branch?
- Whatever the answer, the LAND-PROOF contract and the existing splice/merge-driver behavior must survive intact.

Interim mitigation, already in effect: coordinator dispatch prompts say to pass --finish only on a series' last land, and paused tickets keep their worktrees. Neither prevents this leak.