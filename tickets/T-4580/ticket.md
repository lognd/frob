---
id: T-4580
title: wire COV009 entrypoint_coverage_violations into the gate pipeline (_ProcessJob
  registry in gates/__init__.py, _KNOWN_GATE_RULES in _waive.py) and the land pre-sweep
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4540
- T-4214
- T-4230
parent: T-4230
tier: ticket
sprint: v0.540.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4230
  reason: 'follow-up: wire entrypoint_coverage_violations built under T-4230 into
    the gate pipeline'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: resolve COV009/COV010 rule-id clash with T-4254
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 472
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
RENAME: rule id COV009 clashed with T-4254's already-landed COV009 (symbols sharing one frob:doc anchor). This ticket's underlying finding is now COV010: wire src/frob/gates/_coverage.py::entrypoint_coverage_violations (COV010) into the gate pipeline (_ProcessJob registry in gates/__init__.py, _KNOWN_GATE_RULES in _waive.py) and the land pre-sweep. Title text still says COV009 only because no CLI verb renames a ticket title after filing; treat COV010 as authoritative.