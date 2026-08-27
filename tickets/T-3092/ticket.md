---
id: T-3092
title: Warn when a FEATURE/BUG ticket closes with an empty code diff
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a BUG-kind ticket with no scope exemption closes with a diff touching
    only tickets/, when the check runs, then it WARNs
  evidence: []
- text: Given a docs-kind, epic-tier, or no_scope_declared ticket closes with an empty
    code diff, when the check runs, then it stays quiet (fixture per exemption)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3087 follow-up (deferred, optional per its own brief). A done-report that says work was NOT implemented, on a land whose diff touches nothing outside tickets/, is mechanically detectable: a FEATURE- or BUG-kind ticket closing with an empty code diff should be at minimum a WARN. Needs a frob.gates-level diff scan at close/land time (frob.tickets deliberately stays free of frob.gates, per _done_transition_guard's own docstring on why covers_scope/mutation_evidence/etc are injected booleans, never computed in-package). Exemptions required: docs-kind, epic-tier, no_scope_declared tickets legitimately close without code -- each needs its own must-stay-quiet fixture. T-3064 (closed done with a done-report literally saying "T-3064 is BLOCKED, not implemented" and a land touching only tickets/) is the motivating measured incident.