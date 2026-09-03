---
id: T-3711
title: re-stamp frob-ratchet.lock.json (WAIVE011 producer-abandoned)
state: queued
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-ratchet.lock.json
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
WAIVE011 flags frob-ratchet.lock.json's INV006 pool as ABANDONED: 1593+ commits touched src/frob/**/*.py since the lock was last stamped 2026-07-23, past ABANDONED_CODE_COMMIT_THRESHOLD. Re-run frob pool snapshot INV006 to re-stamp against current main and clear the self-gate error. Found during the AY self-gate drive (2026-09-02).