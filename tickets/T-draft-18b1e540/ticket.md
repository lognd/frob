---
id: T-draft-18b1e540
title: land spends 10+ minutes AFTER publishing the commit in _record_verify_intent_for_landed_commit
  -> _load_snapshot_for_intent (full snapshot load in the land's critical path); the
  serial land queue idles for every minute of it -- defer the verify-intent snapshot
  to the async sweep or reuse the pre-land snapshot
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
