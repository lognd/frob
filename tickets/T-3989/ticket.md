---
id: T-3989
title: 'INV000: frob:invariant naming an unregistered invariant'
state: queued
kind: invariant
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3984
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_inv.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a frob:invariant directive naming an id with no matching registered
    invariant, when frob check runs, then INV000 fires
  evidence: []
- text: given a frob:invariant directive naming a real registered invariant, when
    frob check runs, then the rule stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-201 (T-3984 item 6). VERIFIED: git grep for INV000 across src/frob found nothing -- no existing rule checks that a frob:invariant directive names a REGISTERED invariant id. WAIVE004 (referenced in src/frob/gates/_waive.py and elsewhere) is the analogous stale-waiver rule -- a frob:waive naming a rule id that does not exist / is no longer a live rule. This item is that same shape applied to frob:invariant instead of frob:waive.

FINDING THIS WOULD HAVE CAUGHT: a frob:invariant directive in code naming an invariant id that was never registered anywhere (a typo, a since-deleted invariant, a copy-paste from another repo's id scheme) -- it silently does nothing rather than being flagged, mirroring the exact stale-reference risk WAIVE004 already catches for waivers. Proposed rule INV000: mirror WAIVE004's structure -- a frob:invariant directive whose named id does not resolve to any invariant declared in invariants/ (or wherever this repo's invariant registry lives) is flagged.
