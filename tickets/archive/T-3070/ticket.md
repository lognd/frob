---
id: T-3070
title: Wire evidence-reach classifier (T-3046) into frob check as a real WARN gate
state: dropped
kind: feature
origin: human
created: '2026-08-26'
priority: medium
blocked_by:
- T-3009
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
Wire `frob.graph.reach.classify_evidence_reach` (T-3046) into `frob check`
as a real gate stage (`evidence_reach_gate`, suggested rule id REACH001),
at WARN severity per T-3046's own severity decision (measured 1.4%
DOES_NOT_REACH repo-wide after fixing the evidence_scope-laundering hole
-- too small a floor to justify ERROR on day one, but real enough to
surface).

Blocked on T-3009 landing: `src/frob/gates/__init__.py`'s job table (the
only place any gate's stage-registration lambda lives) and
`docs/modules/gates.md` are both in T-3009's declared scope; T-3046 could
not touch either file without a lease collision.

Plan:
- Register `evidence_reach_gate(snapshot, tickets)` in `_ALL_GATES` and
  the appropriate `_STAGE_GROUPS` member (see `affect_drift`'s own
  registration for the pattern: diff/ticket-scoped, not process-pool).
- For every ticket's non-cmd evidence id, call
  `classify_evidence_reach(root, snapshot, ticket.scope, evidence,
  evidence_scope=ticket.evidence_scope)`; emit one WARN Violation per
  DOES_NOT_REACH or UNKNOWN result (never per REACHES).
- Must-fire fixture: a ticket whose evidence id's test never calls
  anything in its own declared scope. Must-quiet fixture: a genuine
  covering test.
- Doc update: docs/modules/gates.md, once unleased.

## Drop reason
- 2026-08-27: Exact duplicate of T-3063: identical title and byte-identical body (10037 chars each), both queued, both unblocked now that T-3009 is done. T-3063 was filed first and is retained. Filed separately: frob ticket new does not detect duplicate titles/bodies.
