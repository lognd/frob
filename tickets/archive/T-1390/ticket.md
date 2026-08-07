---
id: T-1390
title: CrossTicketLeakage compares declared scope, not actual sibling changes -- every
  land needs --allow-cross-ticket
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_cross_ticket_leakage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_declaring_broad_scope_but_untouched_does_not_block
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open
designated_repro_test: null
acceptance:
- text: GIVEN a branch whose committed changeset touches a file that a sibling open
    ticket merely DECLARES in scope, but to which that sibling has contributed no
    actual change on this branch, WHEN the branch is landed, THEN the land is permitted
    without --allow-cross-ticket
  evidence:
  - tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_declaring_broad_scope_but_untouched_does_not_block
- text: GIVEN a branch that genuinely carries a sibling open ticket's committed changes,
    WHEN the branch is landed, THEN CrossTicketLeakage still refuses the land
  evidence:
  - tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open
threat: null
component: null
---
Measured 2026-08-01: three independent agents landing seven tickets each hit CrossTicketLeakage on EVERY land and each resolved it with --allow-cross-ticket. One land reported leakage against 28 separate open tickets. In no case did the branch actually carry a sibling's work -- the siblings simply declare over-broad scopes (src/**, tests/**, docs/**, src/frob/gates/**), which is the same root cause as the 86 outstanding TICK009 scope-breadth nudges.

The guard asks 'does another open ticket DECLARE this file in scope?' when the question it must answer is 'does this branch actually CARRY another ticket's committed changes?'. Declared scope is an intention; it is not evidence that work exists.

Why this is critical rather than cosmetic: an override that must be passed on every single land is not a guard. It trains every agent to reach for --allow-cross-ticket reflexively, which is precisely how a genuine cross-ticket leak would reach main unnoticed. The T-1355 incident this guard was built to prevent is currently one habituated keystroke away from recurring.

T-1370 fixed only the narrow same-worktree case (sibling leased to the same worktree). The false-positive class above is broader and survives that fix -- all seven lands measured here were AFTER T-1370 landed.