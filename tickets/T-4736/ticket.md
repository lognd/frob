---
id: T-4736
title: 'Gate cut-over: delete the hand-written job list and the _KNOWN_GATE_RULES
  literal; the registry is the sole source'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-4661
- T-3962
parent: T-4655
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- tests/unit/test_gate_registry_cutover.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given this leaf closes, when src/frob/gates/__init__.py and src/frob/gates/_waive.py
    are searched, then no hand-written check job list and no `_KNOWN_GATE_RULES` frozenset
    literal remain; both are derived from the registry.
  evidence: []
- text: 'POSITIVE CONTROL: a test asserts that removing a detector''s registry entry
    makes its rule id disappear from the live job list and from GATERULE001''s known
    set, with no edit to __init__.py or _waive.py. It FAILS on dev today (the frozenset
    literal still carries the id) and passes after this leaf.'
  evidence: []
- text: Given a live rule id absent from the registry, when `frob check` runs, then
    GATERULE001 reports it against the registry, and the job reports a nonzero number
    of rule ids CHECKED -- never a bare zero.
  evidence: []
- text: Given the deletion, when the existing gate suite runs, then every rule id,
    severity and frob:waive behaviour is unchanged -- frozen contract.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
GATE cut-over leaf (story T-4655), owner-approved amendment 2026-09-19. ~3 points.

T-4661 builds the registry and proves it derives today's job list and rule-id set
byte-identically. This leaf DELETES the originals: the hand-written check job list in
src/frob/gates/__init__.py and the `_KNOWN_GATE_RULES` frozenset literal in
src/frob/gates/_waive.py both go, and the registry becomes the SOLE source. GATERULE001
checks live rule ids against the registry instead of against a hand-maintained frozenset.

This is the leaf that actually makes adding a detector a one-file change, and that removes
three of the four shared-registry lease hotspots that serialize every gate ticket today.

Blocked on T-3962 for the lease on gates/__init__.py as well as on T-4661 for the registry
itself: this leaf cannot hold that file until T-3962 releases it.
