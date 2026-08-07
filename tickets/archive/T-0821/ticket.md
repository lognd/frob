---
id: T-0821
title: 'land: close path refuses planned-state tickets with full evidence (recurring
  InvalidTransition; auto-advance or preflight-name the state gap)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestPlannedStateAutoAdvanceOnLand::test_planned_ticket_with_full_evidence_lands_to_done
designated_repro_test: null
acceptance:
- text: GIVEN a worktree ticket in planned state with evidence bound and a Done report
    WHEN land runs THEN it either advances planned->in-progress->done transparently
    during finalize or the PRE-MERGE preflight refuses naming the state and the frob
    ticket start remedy -- never a post-merge InvalidTransition; a regression test
    covers the planned-state land
  evidence:
  - tests/test_ticket_land.py::TestPlannedStateAutoAdvanceOnLand::test_planned_ticket_with_full_evidence_lands_to_done
threat: null
component: null
---
Hit 3x this drive (T-0799, T-0752 post-10b-restore, T-0815): implementers leave tickets planned (never ran start, or a ledger restore reverted the state), evidence+report are complete, land merges+finalizes then dies InvalidTransition at close, forcing the coordinator start-then-retry recipe. Either fold the start transition into finalize when preconditions are met, or extend the T-0763 preflight to check state transitions pre-merge.