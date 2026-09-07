---
id: T-4202
title: 'close: a strata/json/docs-only ticket scope should accept bound test or cmd
  evidence without a touched Python symbol'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets
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
Consumer F-336 (T-4135). A ticket whose scope is entirely non-code (a .strata file, a ratchet lock json) cannot close: EvidenceScopeUnbound fires because no touched/scope Python symbol exists, even with a genuinely bound test as evidence. Adjacent to T-4170's family (evidence rules assuming a code-symbol shape) but a distinct trigger -- non-code scope, not out-of-scope test file. Fixture-testable: YES.