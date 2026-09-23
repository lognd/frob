---
id: T-draft-36f5e957
title: Gate registry derived views are not consumed by the check job runner; @gate
  registration does not run a detector
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
T-4661 shipped frob.gates._registry (register_gate/@gate, derive_job_names and three other derived views) so a new detector is a one-file change, but src/frob/gates/__init__.py never reads _REGISTRY.by_job: _ALL_GATES/_CANONICAL_GATE_ORDER/_GATE_STAGE_GROUPS remain hand-maintained, so a registered job is catalogued and never run. Observed 2026-09-23: four WEBSEC leaves (T-5306/T-5308/T-5309/T-5311) could not wire without editing _taint_gate.py or gates/__init__.py, both leased; the workaround is per-family module discovery in the taint gate (T-5311). Fix: make the runner derive its job list and stage groups from the registry (legacy seed first, registered jobs appended in registration order), import registered modules through a documented discovery path (frob.gates plus frob.webapp/frob.sql packages), and add a positive control: a test that registers a fake job with a planted finding and asserts that frob check --only <group> reports it. Then retire the per-family discovery hooks or keep them as thin adapters.
