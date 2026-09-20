---
id: T-4530
title: 'strata: secret_prop reads-flows cannot carry a waive or timeout so REL200
  is unfixable'
state: queued
kind: bug
origin: agent
created: '2026-09-16'
priority: medium
parent: null
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/parse/grammar_node.rs
- src/frob/strata/_secrets.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: given a secret block with a non-empty audience whose issuer code has no timeout
    token, when frob check runs, then the resulting REL200 finding on the auto-generated
    reads flow can be discharged with a waive clause, the same way a node-originated
    flow's REL200 can be
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`docs/strata/surface.md`'s `secret_prop` grammar
(`issued_by`/`audience`/`lifetime`/`revoke`) has no `waive` clause, unlike
`node`/`store` (T-0174). std.secrets auto-generates one "reads" flow per
`audience` member with `src` set to the synthetic secret-clearance node
itself (`elaborate_secret`, docs/strata/surface.md#std-secrets). REL200
(missing timeout obligation) fires on every such flow whenever the
secret's real code has not landed yet (design-first modeling, or any
node whose issuer code genuinely never carries a timeout), and there is
no legal `.strata` syntax to discharge it: not on the secret block
itself (no `waive` slot), and not on the synthetic node (never declared
in source, so there is no `node { ... }` block to add a `waive` line
to).

Found while modeling project-hullbreach-platform's sprint-1 design
(design/hullbreach.strata) against secrets with a real `audience` list
during a design-only pass with no implementing code yet. Worked around
there by dropping `audience` and hand-declaring the equivalent flows
from a real node instead -- an acceptable but lossy substitute (it loses
std.secrets' auto-generated `readers(secret) == audience` SetEquality
claim) that should not be the only fix available.

Suggested remedy: extend `secret_prop`'s grammar with an optional
`waive` clause (same shape as `node`'s: `RULE_ID STRING "reason" STRING
("ticket" STRING)?`), and have `elaborate_secret` attach it to the
synthetic secret node it creates so `check_reliability_timeouts`'s
existing waiver lookup (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`)
finds it the same way a real node's waive already works.
