---
id: T-draft-226a5f7f
title: 'Quarantine residue from earlier lands never stalls the queue: prepare auto-files
  one residue ticket and disposes the findings against it'
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
parent: T-5106
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/verify/_quarantine.py
- src/frob/app/verify_runner.py
- tests/unit/verify/**
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
Leaf C3 of T-5106 (~2 pts). Quarantine residue never stalls the queue.
- When a land starts and `.frob/quarantine.json` is RAISED by post-land sweep findings (attributable to earlier lands, not to this branch), prepare files ONE residue ticket for the undisposed findings (kind bug, scope = the finding files, body lists RULE:FILE identities) and disposes them against it via the existing `--file-ticket` path, then proceeds on the deferred path. A quarantine raised by findings attributable to THIS branch still forces synchronous verification (T-1693 unchanged).
- Idempotent: an existing open residue ticket covering the same identities is reused, not duplicated.
- Replaces the coordinator's dispose-noise.sh; cheap ledger writes only, so it belongs in prepare and does not contradict T-4414's detached post-land sweep.
- Positive control: a raised quarantine with two undisposed sweep findings yields one residue ticket, a clear quarantine, and a deferred (not synchronous) land.
