---
id: T-draft-8bb6f1dd
title: COV006 rescue chain is O(edges x records) after T-5341 fix; full-repo self-scan
  exceeds 10 min
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
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
T-5341 restored COV006 by canonicalizing TESTS edges back to the legacy orientation, which made the rescue chain evaluate every frob:tests edge for the first time. A full-repo ad-hoc run of _cov006 did not finish within 10 minutes on the dev host (scoped land-time checks are fine). Profile _cov006_edge_violation and the three rescue helpers in src/frob/gates/__init__.py; index test records by qualname/file once per run instead of per-edge lookup. Per the perf directive, ship the root cause as a PERF00x detector if the pattern (per-item linear scan over a record set inside a per-edge loop) is general.