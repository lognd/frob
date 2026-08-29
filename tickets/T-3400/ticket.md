---
id: T-3400
title: 'Scaffold: remove Makefile/frob contradiction from templates'
state: queued
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
- src/frob/scaffold/**
- docs/commands/scaffold.md
scope_breadth_ack: true
scope_breadth_ack_reason: 'genuine cross-manifest epic: directive requires consistency
  across all 7 scaffold types (Makefile presence, docs, per-type frob.toml.j2 shadowing)
  not a single-file change'
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 1: frob scaffold ships a Makefile of one-line frob aliases and docs/commands/scaffold.md tells new users to run make check, contradicting the resolved global-instructions rule that frob <verb> is the interface in a frob-enabled repo (exceptions: bootstrap, real-logic Makefiles). Filed per T-3284 (frob-suggest make-target hook block). Audit all 7 scaffold manifest types (>=4 carry their own frob.toml.j2 shadowing the shared one per DZ's T-3277 trap) and make Makefile presence/absence and docs consistent across all of them. Do not touch this repo's own root Makefile (T-1382 out of scope).