---
id: T-0637
title: 'land draft auto-finalize failed in the field: T-0575''s draft block dropped
  despite T-0577 landed'
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
- tests/test_ticket_land.py::TestStandaloneSiblingDraftSurvivesLand::test_sibling_draft_ticket_finalized_and_lands_alongside
designated_repro_test: null
acceptance:
- text: GIVEN a worktree ledger with a standalone T-draft block WHEN frob ticket land
    runs for any ticket in that worktree THEN the draft block lands finalized with
    a real T-#### id and all references rewritten
  evidence: []
threat: null
component: null
---
First field test of T-0577's auto-finalize: T-0575's worktree ledger contained a real T-draft-3d5f6965 block (verified by the reviewer at line ~6546 pre-land), main ran post-T-0577 code (0.82.x), yet the land dropped the draft block instead of minting a real id -- grep for the draft id on main after land returns 0 and no new ticket exists. Reproduce with a worktree ledger containing a draft block belonging to a DIFFERENT ticket than the one being landed (the T-0575 case: the draft was filed by the landing ticket but is its own separate block) and fix finalize_draft invocation coverage in the land path. The unit test T-0577 added apparently covers renumber/finalize on the landing ticket's own references, not a standalone sibling draft block.