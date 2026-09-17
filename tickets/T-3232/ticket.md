---
id: T-3232
title: frob.docs/frob.xref narrower per-language coverage than frob.lang
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/docs/**
- src/frob/xref/**
- tests/fixtures/lang/csharp/no_dangerous_apis.cs
- docs/modules/app.md
- docs/commands/xref.md
- tests/unit/test_docs_module.py
- tests/unit/test_xref.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/fixtures/lang/csharp/no_dangerous_apis.cs
  reason: reuse static csharp fixture for docs/xref language-parity tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/app.md
  reason: update docs edges + add language-parity tests for T-3232
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/commands/xref.md
  reason: update docs edges + add language-parity tests for T-3232
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_docs_module.py
  reason: update docs edges + add language-parity tests for T-3232
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_xref.py
  reason: update docs edges + add language-parity tests for T-3232
  actor: logan
  at: '2026-09-16'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2996's unfaceted_packages AST detection cross-check found frob.docs.__init__ filters docstring extraction to language=='python' only (skips every other language's docstrings), and frob.xref.__init__._LANG_EXTS only maps python/c/cpp/strata (missing typescript/rust/kotlin/csharp/bash) for its --lang filter, both narrower than frob.lang.supported_languages(). Measured, not fixed, in T-2996's scope (frob.lang's facet registry, not these packages' implementations).