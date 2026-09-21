---
id: T-5180
title: 'INV003: seven new gate/strata docs make ''only'' claims with no frob:invariant
  marker'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gate-inv011-forbidden-constant-reachability.md
- docs/modules/gate-race001.md
- docs/modules/gate-registration.md
- docs/modules/gate-sys111-ratchet-auto-accept.md
- docs/modules/gate-testmock001.md
- docs/modules/gate-time-stable-invariant.md
- docs/strata/dataset-construct.md
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
MEASURED 2026-09-21 05:05 (frob check --base dev after the overnight drain): 7 INV003 errors. Each listed doc (all landed in the last two days: T-3962, T-3953, T-4661, T-3997 and siblings) makes an exclusivity/normative claim (regex \bonly\b) and carries no <!-- frob:invariant INV-### --> marker naming a real invariant. Fix per file: bind an existing invariant that covers the claim, add one in invariants/ if none does, or reword to drop the normative claim. Verify: INV003 count 7 -> 0.