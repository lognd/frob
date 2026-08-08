---
id: T-1856
title: First-class anchor marker for permanent-waiver-target tickets
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1853 fixed the land-time refusal so a non-terminal land of a live-tracker-cited ticket is no longer blocked. Item 2 of T-1853's required list is still open: a first-class 'anchor' marker (explicit field or dedicated kind) so intent is declared rather than inferred from prose in the body -- today nothing stops a well-meaning agent from closing an anchor ticket in the name of draining the queue (T-1820 near-miss cited in T-1853's body). Design the marker, wire it into close/land guidance and doable output.