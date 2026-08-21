---
id: T-2766
title: 'docs/modules/arch.md severity table stale: ARCH101/ARCH102 listed as warning,
  frob.toml overrides to error'
state: queued
kind: docs
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/arch.md
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
Found by the new DOC013 gate (T-2080): docs/modules/arch.md's severity
table (lines 57-58) lists ARCH101 and ARCH102 as `warning`, but
frob.toml's `[gates.severity]` table overrides both to `error` (T-0977
for ARCH101; ARCH102 presumably promoted alongside it). Update the table
cells to `error` (or drop the override if the promotion was reverted and
never reflected in frob.toml -- check T-0977's Done report first). Out of
scope for T-2080 itself (docs/modules/arch.md is not in its declared
scope).
