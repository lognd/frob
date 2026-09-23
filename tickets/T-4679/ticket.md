---
id: T-4679
title: csharp event_declaration has no RawSymbol (_walk_csharp.py)
state: queued
kind: bug
origin: human
created: '2026-09-17'
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
- src/frob/lang/_walk_csharp.py
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
found while working T-4519: _cs_dispatch has no case for event_declaration, so a C# event member (e.g. 'public event EventHandler Changed;') never becomes a RawSymbol at all -- frob.xref/frob.docs cannot resolve it regardless of any change in those modules, since there is no symbol to find. Add an event_declaration case to _walk_csharp.py (likely SymbolKind.CONST, mirroring the property-declaration decision documented in that module's docstring) and a matching RawSymbol test. T-4519 pinned the current (missing) behavior in tests/unit/test_xref.py::test_csharp_event_declaration_is_not_yet_a_symbol using tests/fixtures/lang/csharp/nested_property_event.cs -- update/remove that pin once this lands.