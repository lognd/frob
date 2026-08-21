---
id: T-2816
title: land-lock wait budget spends the caller's own work-time budget on queueing,
  not just measuring it
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Coordinator observation during T-2809/T-2807 landing tonight: a land sat at 177s elapsed with only 51s CPU (29%) -- WAITING on another agent's held land.lock, not computing. With --max-in-flight 1 (the old landing-recipe guidance) a land may START while another still holds the lock, and _resolve_land_lock_wait_budget_s then lets it spend up to (deadline - estimated_work_s) of ITS OWN declared FROB_LAND_DEADLINE_S waiting for that lock -- e.g. up to 240s of a 540s budget, leaving as little as ~300s for the actual work. A heavy land that needed more got SIGKILLed mid-work with no recorded failure log, which is the direct cause of at least two tickets tonight showing repeated failed lands with no reason recorded.\n\nStructural point: waiting OUTSIDE the land (the caller's own wait_for_land_slot.py poll loop) is cheap/free and does not compete with the deadline; waiting INSIDE the land (the lock-acquire wait _resolve_land_lock_wait_budget_s bounds) consumes the exact budget the actual work needs. A bounded-but-nonzero in-land lock wait is therefore strictly worse for the caller than not starting the land process at all, unless the wait is very short.\n\nWeigh: should the in-land lock-wait be reduced to near-zero by default (fail fast, let the caller's own wait_for_land_slot.py --max-in-flight 0 do 100% of the queueing), with the current bounded-wait behavior kept only for a caller that genuinely cannot poll externally? If so, name why that caller exists before keeping any nonzero default. Coordinator's own immediate mitigation: landing recipe now says --max-in-flight 0, not 1 -- this ticket is about whether frob's OWN default land-lock wait behavior should change, independent of the recipe.\n\nDoes NOT replace T-2809 (the estimated_work_s contention-feedback-loop fix, landed tonight) -- this is a separate, second defect in the same area: even with a perfectly uncontaminated estimate, spending queueing time out of the work budget is the wrong place to spend it.