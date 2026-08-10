---
id: T-2065
title: _LAND_LOCK_TIMEOUT_S (600s) exceeds the playbook's mandated 540-580s shell
  wrapper
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Surfaced while measuring T-2055 (_land_gate_claims_fn's spawn cost).

_LAND_LOCK_TIMEOUT_S = 600.0 (src/frob/tickets/_land.py:148) exceeds the
agent-playbook's own mandated foreground shell wrapper (timeout 540-580s,
docs/guides/agent-playbook.md section 0 item 3 / section 3b). A land
whose own work runs long enough to queue behind the lock for 540-600s
gets SIGTERM'd by the outer shell wrapper before frob's own internal
LandLockTimeout can ever fire and print a clean refusal -- confirmed as
the mechanism behind the T-2032/T-2033 silent land deaths (see
docs/guides/agent-playbook.md section 13).

Fix by ALIGNING the numbers downward (shrink _LAND_LOCK_TIMEOUT_S below
the playbook's shell-wrapper floor, e.g. ~500s) or by making a typical
land fast enough that queueing past 540s becomes rare -- NOT by raising
either number, which only makes a genuinely stuck land take longer to
surface (T-1344's explicit finding). Needs a decision on which number
moves and by how much; not fixed as a side effect of T-2055.
