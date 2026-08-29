---
id: T-3348
title: add DOC011 catalog row for docstatus_gate to docs/modules/gates.md#public-api
state: in-progress
kind: docs
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
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
T-1486/T-2843: docstatus_gate (src/frob/gates/_docstatus.py) needs a DOC011 catalog row in docs/modules/gates.md#public-api, matching the DOC009/DOC010 precedent immediately above it in that table. Was waived (frob:waive AFFECT001) at T-1486 land time because docs/modules/gates.md was leased by T-1205 (now done); T-2843 later split docstatus_gate into its own module but did not add the catalog row either. Add the row and the frob:doc anchor on docstatus_gate. Found while converting a frob:waive-vs-frob:debt misclassification for T-3295 -- the doc still does not mention docstatus_gate at all (grep confirmed).