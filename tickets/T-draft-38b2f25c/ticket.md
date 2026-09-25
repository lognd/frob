---
id: T-draft-38b2f25c
title: 'SYSDESIGN407: no SIGTERM handler / no preStop hook covering LB deregistration
  lag'
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
- tests/fixtures/sysdesign/sysdesign407/**
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
title: SYSDESIGN407: no SIGTERM handler / no preStop hook covering LB deregistration lag
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN407 row),
       tests/fixtures/sysdesign/sysdesign407/**
blocked_by: [T-SYS-B-K8S, T-SYS-A-NODE-OPS]
tag: Static: code (app) / Static: config (k8s)

Research row 7.7: Kubernetes Pod Lifecycle docs -- "kubelet makes requests to the container
runtime to attempt to stop the containers in the pod by first sending a TERM (aka. SIGTERM)
signal, with a grace period timeout... The default terminationGracePeriodSeconds setting is 30
seconds. If the preStop hook needs longer to complete than the default grace period allows, you
must modify terminationGracePeriodSeconds." Also 12-Factor "IX. Disposability",
https://12factor.net/disposability -- "Processes shut down gracefully when they receive a
SIGTERM signal from the process manager. For a web process, graceful shutdown is achieved by
ceasing to listen on the service port... allowing any current requests to finish, and then
exiting." Lint condition: "Application entrypoint with no SIGTERM/signal handler... flags; a
Pod spec behind a LoadBalancer Service with no `preStop` sleep hook to cover LB deregistration
lag also flags."

Uses the `drain QUANTITY` node clause from T-SYS-A-NODE-OPS as the design-model declaration
this rule checks is actually backed by both a code-level signal handler and a k8s `preStop`
hook (declared-vs-observed, REL240/241-shaped).

Acceptance criteria: flags an entrypoint with no SIGTERM handler when the node declares `drain`;
flags a Service-fronted Pod spec with no `preStop` hook when `drain` implies LB deregistration
lag must be covered. Positive-control fixture: tests/fixtures/sysdesign/sysdesign407/
drain-declared-no-sigterm-handler/**.
