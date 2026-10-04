+++
id = "01M3AXSD8SS01FYJMKFFWRW85A"
title = "SYSDESIGN107: internal listener accepting plaintext when design declares zero-trust"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD8RPMPFSYCWPM0XQY5G"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:58:36Z"
aliases = ["T-6425"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_lb.py", "tests/fixtures/sysdesign/sysdesign107/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSDAJ8YB45QEY8G9Z8DWV"

[[links]]
kind = "blocked-by"
target = "01M3AXSDB73R2KVGH468Z79R41"
+++

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
