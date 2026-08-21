---
id: T-2816
title: land-lock wait budget spends the caller's own work-time budget on queueing,
  not just measuring it
state: done
kind: bug
origin: human
created: '2026-08-21'
priority: high
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
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-2816 fix needs unit tests bound to test_ticket_land.py covering the near-zero
    in-land wait default and opt-in override
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: T-2816 documents the near-zero default in-land wait and FROB_LAND_INLINE_WAIT_S
    opt-in in tickets-landing.md
  actor: logan
  at: '2026-08-21'
evidence:
- tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_ample_deadline_defaults_to_the_near_zero_ceiling_not_the_flat_500s
- tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_opt_in_env_restores_a_longer_in_land_wait
- tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_opt_in_env_is_still_capped_by_the_remaining_budget
- tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_unparseable_inline_wait_env_falls_back_to_the_near_zero_default
- tests/test_ticket_land.py::TestLandLockInlineWaitDefaultsNearZero::test_held_lock_released_quickly_leaves_almost_the_whole_deadline_for_work
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Coordinator observation during T-2809/T-2807 landing tonight: a land sat at 177s elapsed with only 51s CPU (29%) -- WAITING on another agent's held land.lock, not computing. With --max-in-flight 1 (the old landing-recipe guidance) a land may START while another still holds the lock, and _resolve_land_lock_wait_budget_s then lets it spend up to (deadline - estimated_work_s) of ITS OWN declared FROB_LAND_DEADLINE_S waiting for that lock -- e.g. up to 240s of a 540s budget, leaving as little as ~300s for the actual work. A heavy land that needed more got SIGKILLed mid-work with no recorded failure log, which is the direct cause of at least two tickets tonight showing repeated failed lands with no reason recorded.\n\nStructural point: waiting OUTSIDE the land (the caller's own wait_for_land_slot.py poll loop) is cheap/free and does not compete with the deadline; waiting INSIDE the land (the lock-acquire wait _resolve_land_lock_wait_budget_s bounds) consumes the exact budget the actual work needs. A bounded-but-nonzero in-land lock wait is therefore strictly worse for the caller than not starting the land process at all, unless the wait is very short.\n\nWeigh: should the in-land lock-wait be reduced to near-zero by default (fail fast, let the caller's own wait_for_land_slot.py --max-in-flight 0 do 100% of the queueing), with the current bounded-wait behavior kept only for a caller that genuinely cannot poll externally? If so, name why that caller exists before keeping any nonzero default. Coordinator's own immediate mitigation: landing recipe now says --max-in-flight 0, not 1 -- this ticket is about whether frob's OWN default land-lock wait behavior should change, independent of the recipe.\n\nDoes NOT replace T-2809 (the estimated_work_s contention-feedback-loop fix, landed tonight) -- this is a separate, second defect in the same area: even with a perfectly uncontaminated estimate, spending queueing time out of the work budget is the wrong place to spend it.