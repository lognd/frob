---
id: T-draft-86b2a859
title: 'Post-land sweep residue from T-5126 and T-4612: DOC006 provenance doc, DRIFT001
  _docptr.py, DUP001/DUP002/WIRE001 docptr and land_squash tests, FLAGCOV001 frob.toml'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
- tests/gates/test_docptr.py
- tests/tickets/test_land_squash.py
- docs/strata/provenance-trust-identity.md
- frob.toml
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
Findings raised by the post-land sweeps of T-5126 (docptr/land_squash tests) and T-4612 (provenance doc). The quarantine dispositions were recorded against T-4710 by a coordinator scripting slip on 2026-09-21; this ticket is the real owner. Fix each finding in scope.