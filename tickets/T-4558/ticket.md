---
id: T-4558
title: iter_identifiers._IDENTIFIER_TYPES missing java/cuda/kotlin/bash/zig/typescript
  entries
state: queued
kind: bug
origin: human
created: '2026-09-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_extract.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3232: frob.xref's parsed-usage lookup (iter_identifiers) returns () for any language not in _extract.py's _IDENTIFIER_TYPES table. T-3232 added a 'csharp' entry (measured against tests/fixtures/lang/sample.cs) as the proven case; python/c/cpp/rust/csharp are covered, java/cuda/kotlin/bash/zig/typescript are not -- xref definitions still resolve for those (RawSymbol-based) but usages silently come back empty. Each grammar's own leaf-node type name for identifiers needs measuring against a fixture (see T-3232's _IDENTIFIER_TYPES edit for the pattern) before adding an entry; do not guess node type names.