---
id: T-5095
title: DOC006 also needs tickets/** skip for non-CLI pointer kinds (file/path, config,
  file::symbol) in open ticket bodies
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-5126 (DOC006 cli-pointer tickets/** skip). tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo currently fails (pre-existing, unrelated to T-5126's CLI-only fix) with 11 live DOC006 findings of FILE/PATH, CONFIG, and FILE::SYMBOL kinds inside OPEN (queued/in-progress) ticket bodies: tickets/T-3822, T-3823, T-4668, T-4670, T-4691, T-4693, T-4742, T-4808. These are the same narrative-prose-in-ticket-body false-positive class T-5126 fixes for CLI pointers, but for the other DOC006 pointer kinds. Needs its own scoping decision (skip entirely for tickets/**, or per-kind narrowing) since an open ticket's real file/symbol pointer can still be a genuine live finding worth keeping for some kinds.