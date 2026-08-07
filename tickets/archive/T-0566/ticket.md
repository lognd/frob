---
id: T-0566
title: docblocks DOC004 gate has no C/C++ fenced-code-block bucket
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_docblocks.py
- src/frob/lang/_support.py
- tests/test_docblocks_gate.py
- tests/test_lang_support.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/_support.py
  reason: the c/cpp DOC004 known_gap declaration + T-draft-78a0f919 citation lives
    here; adding a real bucket in _docblocks.py must update this claim to _implemented,
    not leave a stale known_gap pointing at a bogus ticket id
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_docblocks_gate.py
  reason: 'regression tests for the new c/cpp #include DOC004 bucket and its LANG003
    known_gap->implemented transition'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_lang_support.py
  reason: 'regression tests for the new c/cpp #include DOC004 bucket and its LANG003
    known_gap->implemented transition'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_docblocks_gate.py::TestCCppNamespace::test_include_of_tracked_header_unanchored_warns
- tests/test_docblocks_gate.py::TestCCppNamespace::test_include_of_tracked_header_anchored_passes
- tests/test_docblocks_gate.py::TestCCppNamespace::test_include_resolving_to_no_tracked_file_not_flagged
- tests/test_docblocks_gate.py::TestCCppNamespace::test_angle_bracket_system_include_never_flagged
- tests/test_docblocks_gate.py::TestCCppNamespace::test_waive_suppresses_unbound_c_include
- tests/test_lang_support.py::TestDeriveLanguageRegistry::test_c_and_cpp_docblock_facet_is_implemented
designated_repro_test: null
threat: null
component: null
---
found while working T-0405 (language extension contract survey): DOC004's fenced-code-block doc-drift check (frob.gates._docblocks) has _PYTHON_LANGS/_RUST_LANGS/_TS_LANGS buckets but no C/C++ bucket -- a fenced c or cpp code block in docs gets no drift checking at all, unlike python/rust/typescript. Add a _C_LANGS/_CPP_LANGS bucket (or a combined c-cpp one, matching frob.vet's capability-matrix convention) with the matching source-extraction branch in doc004_gate.