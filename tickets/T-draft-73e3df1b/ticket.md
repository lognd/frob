---
id: T-draft-73e3df1b
title: 'GRAMMAR: node compute-shape axis (`lifecycle`, `schedule`, `image`, `sidecar_of`)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-62e2a780
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


title: GRAMMAR: node compute-shape axis (`lifecycle`, `schedule`, `image`, `sidecar_of`)
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 5
scope: strata-core/src/parse/grammar_node.rs, docs/strata/surface.md#node,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/node-lifecycle/**
blocked_by: [T-STORE-301-ATTR]

Findings (STRATA-EXPRESSIVENESS.md, section A "COMPUTE"):

serverless function -- "NOT EXPRESSIBLE as a distinct shape... nothing in node_prop lets a node
opt out of the daemon-shaped obligations because it is invocation-scoped. Proposal (GRAMMAR):
add `lifecycle` clause to node_prop: `node_prop := ... | 'lifecycle' ('daemon' | 'invoked' |
'batch' | 'cron')`... Desugars to attr `lifecycle=<kind>`... authority: AWS Lambda /
well-architected serverless lens, CNCF serverless whitepaper."

batch/cron -- "No `schedule`/`cron`/`interval` clause anywhere in node_prop or flow_prop...
Proposal (GRAMMAR): node_prop clause `schedule "<cron-expr>"` or `schedule every QUANTITY`,
desugars to attr `schedule=<expr>`... authority: Kubernetes CronJob concurrencyPolicy / Quartz
misfire semantics."

container/pod -- "no first-class 'this node is a container image running under an
orchestrator' shape... Proposal (GRAMMAR): node_prop `image STRING` (opaque provenance tag,
desugars to attr `image=<ref>`)... authority: CIS Docker Benchmark / NIST SP 800-190."

sidecar -- "A sidecar... has no keyword; it would be an ordinary `node` with an ordinary
`flow` to its parent, indistinguishable from any other two-service relationship (no 'shares
failure domain with' semantics, so REL250 SPOF and REL392 cgroup_bounds would treat it as
fully independent). Proposal (GRAMMAR): node_prop clause `sidecar_of ID`... authority:
Kubernetes pod multi-container pattern / istio-proxy sidecar model."

Acceptance criteria:
- node_prop gains all four clauses in one grammar_node.rs change (scope-disjoint from the
  T-SYS-A-NODE-OPS leaf below, which touches the same file next).
- Each clause registers its new attr key (`lifecycle=`, `schedule=`, `image=`, `sidecar_of=`)
  in the shared AttrKey table from T-STORE-301-ATTR rather than emitting an unregistered attr
  (ATTR001 would otherwise fire on frob's own new attrs).
- REL210/REL211 (health-check obligation) and REL392/REL393 (cgroup_bounds) gain a RULE-ONLY
  exemption for `lifecycle=invoked` nodes, the same shape as the existing `deep_chain_ok`/
  `shared_state_ok` exemptions on REL340/REL360.
- Positive-control fixture: tests/fixtures/sysdesign/node-lifecycle/faas-no-health-exempt/
  design.strata with a `lifecycle invoked` node that would otherwise fail REL210.
