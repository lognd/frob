---
id: T-3232
title: frob.docs/frob.xref narrower per-language coverage than frob.lang
state: done
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
- docs/modules/app.md
- docs/commands/xref.md
- tests/unit/test_docs_module.py
- tests/unit/test_xref.py
- tests/fixtures/lang/sample.cs
- src/frob/lang/_extract.py
- docs/modules/lang.md
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
- op: remove
  glob: tests/fixtures/lang/csharp/no_dangerous_apis.cs
  reason: use existing namespaced csharp fixture (class+doc comment+method call) for
    docs/xref parity tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/sample.cs
  reason: use existing namespaced csharp fixture (class+doc comment+method call) for
    docs/xref parity tests
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/lang/_extract.py
  reason: iter_identifiers' _IDENTIFIER_TYPES table is the direct blocker for xref
    csharp usage lookups (T-3232's proven case); needs a csharp entry to reach the
    deliverable
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/lang.md
  reason: iter_identifiers doc anchor; document the csharp _IDENTIFIER_TYPES addition
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_xref.py::test_csharp_finds_definition_and_usage_with_explicit_lang
- tests/unit/test_xref.py::test_csharp_finds_definition_and_usage
- tests/unit/test_docs_module.py::test_extract_docstrings_csharp_class_and_method
designated_repro_test: null
acceptance:
- text: frob.docs.extract_docstrings and frob.xref's --lang/parsed-search dispatch
    on frob.lang's supported language set via a single shared table (frob.lang.supported_extensions/language_for_extension/tree_sitter_extensions),
    no second hand-maintained language list
  evidence:
  - tests/unit/test_xref.py::test_csharp_finds_definition_and_usage_with_explicit_lang
- text: frob explore xref <symbol> finds the definition and every reference for a
    public C# method across a static csharp fixture (tests/fixtures/lang/sample.cs)
  evidence:
  - tests/unit/test_xref.py::test_csharp_finds_definition_and_usage
- text: a public C# class's XML doc comment resolves through frob.docs.extract_docstrings
    (the docs facet), not just python docstrings
  evidence:
  - tests/unit/test_docs_module.py::test_extract_docstrings_csharp_class_and_method
acceptance_amendments:
- op: remove
  index: 4
  old_text: frob.docs.extract_docstrings and frob.xref's --lang/parsed-search dispatch
    on frob.lang's supported language set via a single shared table (frob.lang.supported_extensions/language_for_extension/tree_sitter_extensions),
    no second hand-maintained language list
  new_text: null
  reason: duplicate created by a redundant accept retry while a stale land pid caused
    a false LandInProgress refusal
  actor: logan
  at: '2026-09-16'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2996's unfaceted_packages AST detection cross-check found frob.docs.__init__ filters docstring extraction to language=='python' only (skips every other language's docstrings), and frob.xref.__init__._LANG_EXTS only maps python/c/cpp/strata (missing typescript/rust/kotlin/csharp/bash) for its --lang filter, both narrower than frob.lang.supported_languages(). Measured, not fixed, in T-2996's scope (frob.lang's facet registry, not these packages' implementations).