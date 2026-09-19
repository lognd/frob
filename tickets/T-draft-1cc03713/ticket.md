---
id: T-draft-1cc03713
title: 'implement T-3961 provenance/trust-as-identity: derived_from and trust_identity
  node attrs with SYS10x consumer'
state: queued
kind: security
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_pii.py
- tests/**/test_sys*.py
- src/frob/gates/_sys_provenance.py
- docs/strata/provenance-trust-identity.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_pii.py
  reason: provenance/trust_identity attr parsing+validation lives in _pii.py per accepted
    T-3961 design
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/**/test_sys*.py
  reason: tests for SYS10x consumer rule
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/gates/_sys_provenance.py
  reason: new SYS10x consumer rule module for derived_from/trust_identity (avoids
    _sys.py lease held by T-4212)
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/strata/provenance-trust-identity.md
  reason: 'standalone doc row: docs/modules/gates.md is leased by T-4111'
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
