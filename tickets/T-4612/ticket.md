---
id: T-4612
title: 'implement T-3961 provenance/trust-as-identity: derived_from and trust_identity
  node attrs with SYS10x consumer'
state: in-progress
kind: security
origin: human
created: '2026-09-19'
priority: high
parent: T-3961
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
- tests/test_pii_provenance_trust_identity.py
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
- op: add
  glob: tests/test_pii_provenance_trust_identity.py
  reason: new tests for derived_from/trust_identity attrs (avoids _pii structural
    gate test file leased by T-4073)
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3961
  reason: implementation of accepted T-3961 design
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
