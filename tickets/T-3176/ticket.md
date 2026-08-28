---
id: T-3176
title: Document T-3135 warm sweep stage and split _squash_apply_on_disposable_stage
state: done
kind: docs
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-landing.md
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:grep -n 'the-t-3135-warm-sweep-stage' docs/modules/tickets-landing.md src/frob/tickets/_land.py
  exit=0 sha256=e94dc9f32445
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7480934c69ddeeb977b85c26665340fde2ebe2e0
---
T-3135 added the persistent warm-stage carve-out to _squash_apply_on_disposable_stage (waived ARCH001/AFFECT001 there) because docs/modules/tickets-landing.md was under another agent's live scope lease for the whole of T-3135's work and the function was already long before this change. Two follow-ups: (1) document the warm stage in docs/modules/tickets-landing.md#the-disposable-stage-flip-t-3121 alongside the existing T-3121 section; (2) split _squash_apply_on_disposable_stage's new ensure/compose/fallback branch into its own helper now that a lease is free.