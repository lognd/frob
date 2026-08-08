---
id: T-1791
title: Wire frob.verify._quarantine.raise_quarantine into the batch-verification driver
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1693 built the durable quarantine primitive (frob.verify._quarantine: raise_quarantine/is_quarantined/clear_quarantine) and wired the land-path enforcement half (_land_cmd.py's _quarantine_override_ceilings, forcing synchronous verification while raised). It does NOT call raise_quarantine anywhere -- the batch-verification driver (T-1690's own declared scope, src/frob/app/ticket_runner/_rapid_sweep.py) needs to call raise_quarantine(root, batch_commit_shas=..., findings=...) when a batch verification comes back red with attributed/unattributed findings from frob.verify.attribute_batch. Out of T-1693's own declared scope (_rapid_sweep.py was leased by a concurrent in-progress ticket for that ticket's whole duration).