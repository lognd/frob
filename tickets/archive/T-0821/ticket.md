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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-0821: a ticket landed with full evidence and a Done report but never

    actually run through frob ticket start (or reverted to PLANNED by a

    section-10b ledger restore, T-0752) cannot legally jump

    PLANNED -> DONE (_TRANSITIONS only allows PLANNED -> IN_PROGRESS/

    DROPPED) -- every prior incident (T-0799, T-0752, T-0815) hit this

    AFTER the merge already landed in the worktree, forcing a manual

    start-then-retry recipe with main untouched but the coordinator now

    needing a second pass.'
  actor: logan
  at: '2026-09-19'
  old_length: 437
  new_length: 953
evidence:
- tests/ticket_land_suite/test_land_core.py::TestPlannedStateAutoAdvanceOnLand::test_planned_ticket_with_full_evidence_lands_to_done
designated_repro_test: null
acceptance:
- text: GIVEN a worktree ticket in planned state with evidence bound and a Done report
    WHEN land runs THEN it either advances planned->in-progress->done transparently
    during finalize or the PRE-MERGE preflight refuses naming the state and the frob
    ticket start remedy -- never a post-merge InvalidTransition; a regression test
    covers the planned-state land
  evidence:
  - tests/ticket_land_suite/test_land_core.py::TestPlannedStateAutoAdvanceOnLand::test_planned_ticket_with_full_evidence_lands_to_done
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Hit 3x this drive (T-0799, T-0752 post-10b-restore, T-0815): implementers leave tickets planned (never ran start, or a ledger restore reverted the state), evidence+report are complete, land merges+finalizes then dies InvalidTransition at close, forcing the coordinator start-then-retry recipe. Either fold the start transition into finalize when preconditions are met, or extend the T-0763 preflight to check state transitions pre-merge.

<!-- narrative-moved:src/frob/tickets/_land_finalize.py:869:T-0821 -->
T-0821: a ticket landed with full evidence and a Done report but
never actually run through `frob ticket start` (or reverted to
PLANNED by a section-10b ledger restore, T-0752) cannot legally
jump PLANNED -> DONE (`_TRANSITIONS` only allows PLANNED ->
IN_PROGRESS/DROPPED) -- every prior incident (T-0799, T-0752,
T-0815) hit this AFTER the merge already landed in the worktree,
forcing a manual start-then-retry recipe with main untouched but