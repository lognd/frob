---
id: T-1223
title: 'rust(interim): tree-sitter Query captures for comment/docstring spans shared
  by sys+opaque+vet'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_core.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_core.py
  reason: T-1420 split moved the actual _comment_byte_spans_from_tree/_docstring_byte_spans_from_tree
    functions this ticket edits into _capability_core.py after the ticket's scope
    was written against the old single-file location -- same scope-drift precedent
    as T-1210's own Done report; tests/test_vet.py added for new-evidence node ids
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_vet.py
  reason: T-1420 split moved the actual _comment_byte_spans_from_tree/_docstring_byte_spans_from_tree
    functions this ticket edits into _capability_core.py after the ticket's scope
    was written against the old single-file location -- same scope-drift precedent
    as T-1210's own Done report; tests/test_vet.py added for new-evidence node ids
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_vet.py::TestCapabilityScan::test_docstring_query_does_not_treat_enum_value_as_docstring
- tests/test_vet.py::TestCapabilityScan::test_docstring_query_still_finds_real_docstrings
- tests/test_vet.py::TestFingerprintScan::test_whitespace_tolerant_match_still_respects_comment_spans
- tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire
- tests/test_vet.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
- tests/test_vet.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
designated_repro_test: null
acceptance:
- text: GIVEN _comment_byte_spans (vet/_capability.py:212) and _docstring_byte_spans
    (:286) are per-node Python recursions independently re-run by sys and opaque (12
    pct of sys + 92 pct of opaque combined) WHEN they are replaced with tree-sitter
    Query captures ('(comment) @c' and the docstring-node equivalent), which run in
    C via the existing py-tree-sitter binding rather than a Python recursion, THEN
    sys+opaque's span-extraction share drops without requiring a new frob_core crate
    export
  evidence:
  - tests/test_vet.py::TestCapabilityScan::test_docstring_query_does_not_treat_enum_value_as_docstring
  - tests/test_vet.py::TestCapabilityScan::test_docstring_query_still_finds_real_docstrings
  - tests/test_vet.py::TestFingerprintScan::test_whitespace_tolerant_match_still_respects_comment_spans
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire
  - tests/test_vet.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
  - tests/test_vet.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
threat: null
component: null
---
Root cause and target: this is the interim zero-Rust step noted under Rust-migration candidate #1 ('use tree-sitter Query captures (C speed) for comment/docstring/identifier extraction from Python'), and it is the mechanism half of PERF-epic child T-1210 (report candidate #5). Split of ownership: this ticket owns the span-EXTRACTION mechanism (Query captures replacing Python recursion) since it is the natural home for a tree-sitter-API-level change; T-1210 owns the sort+bisect containment fix and the per-run cache for the resulting spans, and its acceptance criteria explicitly defer the mechanism to this ticket to avoid two owners writing to the same function. Do not duplicate the containment/caching acceptance criteria here -- see T-1210.