---
id: T-3014
title: Wire NARR001 (T-2993's narrative-block detector) into gates/__init__.py
state: queued
kind: docs
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
T-2993 built NARR001 (frob.gates._narrative_blocks.narrative_blocks_gate) and
proved it via direct-call fixtures (must-fire + must-stay-quiet + the
_socketd.py T-2961 block), but could NOT wire it into src/frob/gates/__init__.py's
gate dict because that file was held by T-2986's live in-progress lease for the
whole of T-2993's work window.

Wire narrative_blocks_gate into gates/__init__.py's GATE_RUNNERS dict (mirroring
"excludehazard" immediately above it), add NARR001 to docs/modules/gates.md's
frob:enumerates member list and rule-catalog table, and ship it at WARN severity
per T-2993/T-2994's burn-then-promote doctrine.
