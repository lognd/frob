---
id: T-4087
title: 'WIRE001 follow-up anchor: profile_boundary_subject_count''s lazy dict-registry
  wiring is invisible to the callgraph'
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: true
anchor_reason: 'WIRE001 follow_up anchor (T-1856 pattern, T-1831/T-1856 precedent):
  profile_boundary_subject_count is genuinely wired (called from frob.check._python._subject_count_probes)
  but only via a function-local deferred import required to avoid a real frob.gates<->frob.check
  circular import -- the callgraph''s best-effort tracer cannot see through that,
  a permanent structural fact, not deferred work; stays queued forever so WIRE002''s
  follow_up-must-be-open check keeps passing'
land_commit: null
---
