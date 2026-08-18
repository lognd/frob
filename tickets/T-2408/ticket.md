---
id: T-2408
title: frob.lang.extract_imports has no typescript/rust/kotlin walker (import_graph
  capability gap)
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/_extract.py
- tests/unit/test_lang_primitives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_lang_primitives.py
  reason: add import-walker unit tests for the three new typescript/rust/kotlin _IMPORT_WALKERS
    entries, TEST001 evidence
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_lang_primitives.py::test_extract_imports_typescript_rust_kotlin
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 52a5e2413c768639aed6d227b1d2bbba38d59a57
---
T-2365's adapter-capability conformance axis (frob.lang._support.derive_capability_registry) marks import_graph KNOWN_GAP for typescript/rust/kotlin: _IMPORT_WALKERS only has python/c/cpp entries. frob.graph.callgraph's cross-file import-verification path (verify_imports=True) and frob.xref both only work for languages with a real extract_imports walker. Add _imports_typescript/_imports_rust/_imports_kotlin walkers mirroring _imports_python/_imports_c_family's shape.