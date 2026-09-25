---
id: T-draft-c439e5c2
title: 'GRAMMAR: node operational axis (`drain`, `cert_expiry`, `health` closed vocabulary,
  `owner`, typed `slo`/`error_budget`, `scale_on`)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-ffda706b
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- strata-core/src/parse/grammar_node.rs
- docs/strata/surface.md#node
- src/frob/strata/_models.py
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
OWNER-OWNED: strata surface change; owner reviews before dispatch


title: GRAMMAR: node operational axis (drain, cert_expiry, health vocabulary, owner,
       typed slo/error_budget, scale_on)
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 5
scope: strata-core/src/parse/grammar_node.rs, docs/strata/surface.md#node,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/node-ops/**
blocked_by: [T-SYS-A-NODE-LIFECYCLE, T-STORE-301-ATTR]

Findings (STRATA-EXPRESSIVENESS.md, sections D/F/G):

graceful shutdown/drain -- "NOT EXPRESSIBLE. Confirmed zero hits. Proposal (GRAMMAR): node_prop
`drain QUANTITY` (max time to stop accepting new work and finish inflight before SIGKILL)...
typed Quantity field... Enables RULE: a node with `capacity`+`deploy.rollback` but no `drain`
bound risks dropped inflight requests during every rollout -- authority: Kubernetes
terminationGracePeriodSeconds / SIGTERM handling best practice."

TLS termination/cert -- "General cert lifecycle (expiry/rotation) NOT EXPRESSIBLE anywhere...
for expiry specifically add node_prop `cert_expiry QUANTITY` (typed field, arithmetic:
days-until-expiry comparable to a rotation SLA)... authority: CA/Browser Forum baseline
requirements (398-day max cert lifetime)."

health probes -- "`health` attr (REL210/211) proves a node declares SOME health surface, but
it is a single bare attr, not distinct readiness/liveness/startup probe types... Proposal
(GRAMMAR): node_prop `health` IDENT closed vocabulary (readiness|liveness|startup|combined)...
flagged as a VERIFY-BEFORE-FILING item, not confirmed bare-marker vs. already-valued." This
leaf's implementer must read the exact current grammar_node.rs `health` at_keyword branch
before writing the closed-vocabulary change, per that flag.

bounded contexts/ownership-teams -- "there's no explicit 'team X owns module Y' declaration...
Proposal (GRAMMAR, minor): top-level or node_prop `owner STRING` clause... authority: this
repo's own existing Waiver.owner precedent generalized." (Node-level half only; module-level
half is T-SYS-A-MODULE-OWNER.)

SLO/error budget -- "rides generic `attr slo=... error_budget=...`... Proposal (GRAMMAR,
minor): promote `slo`/`error_budget` from attr strings to a typed node_prop clause `slo
PERCENT error_budget QUANTITY`... enabling direct arithmetic against REL380/381's utilization
numbers rather than string-parsing an attr."

autoscaling signal -- "the SIGNAL (CPU/RPS/custom metric that drives the scale decision) does
not exist at all... Proposal (GRAMMAR): capacity_prop addition `scale_on IDENT (above|below)
NUMBER UNIT`... Desugars to a typed field on Capacity... Enables: a new REL-family rule
'declared scale_on threshold is above one-replica service_rate, so autoscaling can never fire
before REL380 saturation' -- authority: Kubernetes HPA / AWS Auto Scaling target-tracking
policy."

Acceptance criteria: all six clauses land in one change; `drain`/`cert_expiry`/`scale_on`/
`slo`/`error_budget` become typed fields (arithmetic-consuming per charter law 1), `health`
becomes closed-vocabulary IDENT, `owner` (node-level) desugars to attr and registers in
T-STORE-301-ATTR's table. Positive-control fixture: tests/fixtures/sysdesign/node-ops/
rollout-no-drain-bound/design.strata.
