---
id: T-draft-769b07dc
title: post-land sweep raises quarantine on its own lease-file/doc noise (TICK010
  on .git/frob-leases, DOC012 docs/commands) and dirties the root ratchet lock, forcing
  every land synchronous
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
- tests/unit/rapid_sweep_suite/*
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: quarantine raise filtering, root-write fix
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: possible root ratchet-lock writer
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_land.py
  reason: land staging writer for ratchet lock
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/rapid_sweep_suite/*
  reason: positive-control tests for filtering
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/**
  reason: why-file / doc updates
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
