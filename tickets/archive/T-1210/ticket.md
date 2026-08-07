---
id: T-1210
title: 'perf: vet capability comment/docstring spans recomputed per file per gate
  -- tree-sitter Query + sorted-span bisect'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
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
  reason: root-cause span/containment functions (_comment_byte_spans, _docstring_byte_spans,
    _fully_in_any_span, _non_executable_byte_spans) actually live in _capability_core.py,
    not _capability.py; ticket description cites their behavior but the declared scope
    missed the file they are defined in
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_vet.py
  reason: evidence for sort+bisect containment fix and per-run span cache in _capability_core.py
    lives here (TestCapabilityScan et al.)
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_vet.py::TestFingerprintScan::test_whitespace_tolerant_match_still_respects_comment_spans
- tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire
- tests/test_vet.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
- tests/test_vet.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
designated_repro_test: null
acceptance:
- text: 'GIVEN _comment_byte_spans/_docstring_byte_spans (per-node Python recursion)
    are recomputed independently by sys and opaque, and _fully_in_any_span does an
    O(candidates x spans) linear any() over an unsorted span tuple (7.8M genexpr steps
    in sys alone) WHEN spans are sorted once and containment uses bisect, and spans
    are cached per (path, content-hash) for the run so sys and opaque share them THEN
    sys+opaque drop ~4-5s native combined (report candidate #5). NOTE: computing spans
    via a tree-sitter Query in C rather than Python recursion is covered by the sibling
    EPIC B child ''tree-sitter Query captures for comment/docstring spans (interim,
    zero-Rust)'' -- this ticket covers only the sort+bisect containment fix and the
    per-run cache, not the extraction mechanism itself'
  evidence:
  - tests/test_vet.py::TestFingerprintScan::test_whitespace_tolerant_match_still_respects_comment_spans
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire
  - tests/test_vet.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
  - tests/test_vet.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
threat: null
component: null
---
Root cause: vet/_capability.py:212/:286 recompute comment/docstring byte spans per file per gate via Python recursion (12 pct of sys + 92 pct of opaque), and :244 _fully_in_any_span is a linear any() over an unsorted span tuple per candidate. Fix here: sort spans once, bisect for containment, and cache spans per (path, content-hash) so sys and opaque share one computation. The extraction-mechanism half of this candidate (Query captures replacing the Python recursion) is EPIC B's job, not this ticket's -- see that child to avoid two owners for the same code.