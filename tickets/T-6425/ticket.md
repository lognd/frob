---
id: T-6425
title: 'SYSDESIGN107: internal listener accepting plaintext when design declares zero-trust'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6503
- T-6482
parent: T-6424
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
- src/frob/sysdesign/_lb.py
- tests/fixtures/sysdesign/sysdesign107/**
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
title: SYSDESIGN107: internal listener accepting plaintext when design declares zero-trust
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_lb.py, docs/modules/gates.md (SYSDESIGN107 row),
       tests/fixtures/sysdesign/sysdesign107/**
blocked_by: [T-SYS-B-PROXY, T-SYS-H-RESEARCH-GAPS]
tag: Static: config

Research row 4.5 (not independently quoted this pass; cites sec. 2 Envoy docs as establishing
the mesh as the enforcement point, mTLS-specific quote not captured): "Internal (cluster-
internal) listener/route accepting plaintext (no mTLS/PeerAuthentication STRICT mode) when
design declares 'zero-trust' flags."

Cross-reference (STRATA-EXPRESSIVENESS.md section D): "mTLS: `transport` atom (free string,
e.g. `mtls`) could encode it today as an opaque tag but nothing validates or requires it;
PARTIAL, RULE-ONLY fix: a rule reading `transport` for a closed `mtls` atom on cross-trust
flows... Authority: NIST SP 800-207 (Zero Trust Architecture)." This rule reads BOTH the
config-layer signal (T-SYS-B-PROXY's `transport_socket`/PeerAuthentication) and the
design-model `transport` attr for consistency, rather than filing two separate rules for one
concern.

Acceptance criteria: flags an internal listener in T-SYS-B-PROXY's parsed config with no mTLS
transport_socket when the corresponding strata node/flow declares `attr transport mtls` (or the
design declares zero-trust more broadly) but the deployed config disagrees. Positive-control
fixture: tests/fixtures/sysdesign/sysdesign107/declared-mtls-plaintext-listener/**.
