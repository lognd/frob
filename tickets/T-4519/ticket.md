---
id: T-4519
title: docs/xref/perf coverage for csharp (post T-3232/T-3234 generic fix)
state: in-progress
kind: bug
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4506
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/docs/__init__.py
- src/frob/xref/__init__.py
- src/frob/perf/_collectors.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: 'xref: property_declaration (SymbolKind.CONST) is a resolvable xref definition,
    not just methods/classes'
  evidence: []
- text: 'xref: property_declaration (SymbolKind.CONST) is a resolvable xref definition,
    not just methods/classes'
  evidence: []
- text: 'xref: property_declaration (SymbolKind.CONST) is a resolvable xref definition,
    not just methods/classes'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
After T-3232 (frob.docs/frob.xref language filters) and T-3234 (frob.perf hot-graph collector) land their generic fixes, add csharp-specific test fixtures proving the three packages now cover csharp end to end. This ticket adds proof coverage, it does not re-implement T-3232/T-3234's generic fix. blocked_by both.

GIVEN a .cs file with an XML doc comment (///), WHEN frob.docs extracts docstrings, THEN the csharp docstring is extracted (not silently skipped as non-python).
GIVEN a .cs file, WHEN frob xref --lang csharp is run, THEN it is accepted as a valid --lang filter value and returns csharp symbols.
GIVEN a .cs file with a hot call path, WHEN frob.perf's hot-graph collector runs, THEN csharp appears in its adapter-extension coverage alongside python/typescript/rust/kotlin.

## Unblock log
- 2026-09-16: unblocked by T-3234 -- frob.perf hot-graph coverage for csharp is deferred to v1.1.0 with T-3234; T-4519 delivers docs/xref only
- 2026-09-17: unblocked by T-3232 -- T-3232 landed 7eacfd2a7 / perf coverage deferred to v1.1.0 with T-3234
