---
id: T-1997
title: stale WIRE001 waiver on capability_ratchet_violations claims 'not wired' after
  T-1977 wired it
state: dropped
kind: bug
origin: human
created: '2026-08-10'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1628's frob:waive WIRE001 comment on capability_ratchet_violations (src/frob/strata/_effects.py) says wiring into frob sys audit is out of scope and names follow_up=T-1977. T-1977 landed the wiring (SYS111, src/frob/gates/_sys_selfaudit.py). The waiver comment is now stale prose (not currently failing any gate, since WAIVE gate reports 0 errors) but should be removed for accuracy -- out of T-1977's declared scope, filed separately rather than touched silently.

## Drop reason
- 2026-08-10: fixed directly in T-1977's own land instead of deferring -- the stale WIRE001 waiver was removed (not just re-pointed) since the wiring it disclosed as missing now exists
