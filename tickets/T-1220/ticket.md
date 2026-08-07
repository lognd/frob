---
id: T-1220
title: 'rust: tree-extraction kernel -- source bytes to symbols/spans/tokens/identifiers/comment+docstring
  spans/import specs'
state: queued
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- frob-core/**
- docs/modules/lang.md
- docs/modules/dup.md
- tests/unit/test_extract_native.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/lang.md
  reason: 'portion delivered (T-1220''s coherent first slice): only frob-core/** (new
    Rust extraction kernel) plus the two doc anchors it affects touched this pass;
    src/frob/lang/** consumer rewiring and the cpp/rust/typescript walkers remain
    a later portion of this same ticket, not yet started'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/dup.md
  reason: 'portion delivered (T-1220''s coherent first slice): only frob-core/** (new
    Rust extraction kernel) plus the two doc anchors it affects touched this pass;
    src/frob/lang/** consumer rewiring and the cpp/rust/typescript walkers remain
    a later portion of this same ticket, not yet started'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_extract_native.py
  reason: new pytest golden-parity test file for this portion's extract_tree_python
    kernel
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: merge with main required updating the shared testsuite node capability declarations
    touched by this branch (T-1223 test wiring); consistent with T-1223s own scope
    having included this file
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_functions_structs_comments_and_field_access
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_unparseable_source_returns_empty_not_a_crash
- tests/unit/test_extract_native.py::TestExtractTreeRustParity::test_this_repos_own_extract_rs_matches_byte_for_byte
designated_repro_test: null
acceptance:
- text: 'GIVEN frob.lang._extract.extract and _walk_python do pure per-node Python
    recursion over py-tree-sitter Node objects (measured shares: perf 38 pct, clones
    69 pct, deprecated 76 pct, dead_symbols 88 pct, opaque 92 pct, sys ~50 pct) WHEN
    a frob_core kernel (e.g. extract_tree(source: bytes, lang: str) -> (symbols, spans,
    body_tokens, leaf_identifiers, comment_spans, docstring_spans, import_specs))
    is exported for python/cpp/rust/typescript via the tree-sitter Rust crates, with
    kotlin staying on the existing Python path, and the FFI boundary passes FFI001/FFI002
    THEN callers across perf/clones/deprecated/dead_symbols/opaque/sys switch to the
    native kernel and each site''s measured native-cost share for extraction drops
    correspondingly'
  evidence:
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_module_class_function_docstrings_and_comments
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_errorset_style_assignment_is_not_a_docstring
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_unparseable_source_returns_empty_not_a_crash
  - tests/unit/test_extract_native.py::TestExtractTreePythonParity::test_this_repos_own_lang_module_matches_byte_for_byte
- text: 'GIVEN the report''s Rust-migration-candidates #1 and #4 overlap (identifier/xref
    index kernel is subsumed by the tree-extraction kernel if it lands first) WHEN
    this ticket lands THEN the identifier/xref index kernel work is satisfied as a
    byproduct (leaf_identifiers output) rather than needing a separate crate export
    -- no duplicate kernel is built for identifier extraction'
  evidence: []
threat: null
component: null
---
Root cause and target: this is Rust-migration candidate #1 from the report, HIGH feasibility. tree-sitter has first-class Rust crates and tree-sitter-python/cpp/rust/typescript grammars exist as crates; kotlin (via tree-sitter-language-pack) stays Python-side for now. frob-core already has the pyo3/abi3 plumbing and .pyi convention; API shape mirrors existing kernels (plain lists/tuples over the FFI, consistent with dup/callgraph/arch kernels already shipped). This ticket SUBSUMES Rust-migration candidate #4 (identifier/xref index kernel): note explicitly in the design that leaf-identifier output from this kernel satisfies #4's need, so no second crate export is built purely for identifiers. Not blocked on anything -- this is the foundation the other EPIC B children (capability resolver, arch metrics walk) build on, but do not add a blocked_by edge for those; they are downstream consumers, this ticket's own scope does not require them to exist first.