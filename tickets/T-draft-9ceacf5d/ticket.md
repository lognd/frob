---
id: T-draft-9ceacf5d
title: 'SYSDESIGN406: workload with a livenessProbe but no readinessProbe, or vice
  versa'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-0e74c702
parent: T-draft-3ed25d21
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
- src/frob/sysdesign/_horizontal.py
- tests/fixtures/sysdesign/sysdesign406/**
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
title: SYSDESIGN406: workload with a livenessProbe but no readinessProbe, or vice versa
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN406 row),
       tests/fixtures/sysdesign/sysdesign406/**
blocked_by: [T-SYS-B-K8S]
tag: Static: config

Research row 7.6: Kubernetes Pod Lifecycle docs, https://kubernetes.io/docs/concepts/
workloads/pods/pod-lifecycle/ (fetched, 942 lines; documents readinessProbe, livenessProbe,
startupProbe as distinct probe types with distinct effects -- readiness gates Service endpoint
membership, liveness triggers restart, startup gates the other two during slow boot). Lint
condition: "A workload with a `livenessProbe` but no `readinessProbe` (or vice versa) flags,
since conflating them can pull healthy-but-still-loading pods into the Service or fail to
restart a truly wedged pod."

Cross-reference row 9.4: "A `readinessProbe`/`livenessProbe` pointed at a business endpoint
(not a dedicated health endpoint) flags, since business-logic side effects or auth requirements
can make probes unreliable" -- filed as a second finding in the same module, not a separate id.

Acceptance criteria: SYSDESIGN406 fires on either of two conditions, folded into one id per
the coordinator's contiguous-numbering directive -- a container spec with exactly one of
readiness/liveness probe set flags; a probe pointed at a route the design model marks as a
business endpoint rather than a dedicated `/healthz`/`/readyz`-shaped path also flags.
Positive-control fixture: tests/fixtures/sysdesign/sysdesign406/liveness-only-no-readiness/**.
