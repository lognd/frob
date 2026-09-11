---
id: T-4425
title: 'Fix DOC011: tickets-lifecycle.md cites nonexistent T-4313'
state: in-progress
kind: docs
origin: human
created: '2026-09-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-lifecycle.md
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
CI self-gate DOC011 fails (ubuntu/macOS/Windows, run 34556421981): docs/modules/tickets-lifecycle.md:419 cites T-4313, which was never a real ticket -- a ghost id printed by frob ticket new on 2026-09-09 (see T-4336, T-4342 for the incident and its fix). Replace the citation with the real tracking ticket (T-4342, which added orphaned-lock detection for exactly this shape) or reword to unbacktick prose with no ticket id. Verify uv run frob check --only doc is clean of DOC011.