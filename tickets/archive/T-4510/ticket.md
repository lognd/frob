---
id: T-4510
title: C# dup/docblock facet fixture (verify _CSHARP_LANGS bucket end to end)
state: done
kind: feature
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
- tests/fixtures/csharp_dup_docblock/**
- tests/unit/test_support_csharp.py
- src/frob/dup/_legacy.py
- src/frob/dup/_legacy_cs.py
- docs/modules/dup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/dup/_legacy.py
  reason: 'T-4510 finding: frob.dup._legacy._scan_tree never dispatched .cs at all
    (only _PY_EXTS/_CPP_EXTS), so csharp''s dup facet had zero real fixture coverage;
    wire a minimal _legacy_cs.py scanner mirroring _legacy_py.py/_legacy_cpp.py rather
    than weaken the ticket''s own fixture assertion'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/dup/_legacy_cs.py
  reason: 'T-4510 finding: frob.dup._legacy._scan_tree never dispatched .cs at all
    (only _PY_EXTS/_CPP_EXTS), so csharp''s dup facet had zero real fixture coverage;
    wire a minimal _legacy_cs.py scanner mirroring _legacy_py.py/_legacy_cpp.py rather
    than weaken the ticket''s own fixture assertion'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/dup.md
  reason: document the new csharp _scan_cs_file/_CS_EXTS coverage (T-4510) alongside
    the existing python/cpp scanner docs
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_support_csharp.py::TestCsharpDupFacetFires::test_find_duplicates_reports_near_duplicate_methods
- tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_unanchored_project_using_fires_unbound
- tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_bcl_using_is_zero_false_positives
- tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_anchored_project_using_has_zero_violations
designated_repro_test: null
acceptance:
- text: GIVEN two near-duplicate C# methods in a fixture file, WHEN the dup detector
    runs, THEN it reports the duplicate pair using the _CSHARP_LANGS facet path.
  evidence:
  - tests/unit/test_support_csharp.py::TestCsharpDupFacetFires::test_find_duplicates_reports_near_duplicate_methods
- text: GIVEN a public C# method missing an XML doc comment (///), WHEN the docblock
    checker runs, THEN it flags the missing docblock the same way it flags a missing
    Python docstring.
  evidence:
  - tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_unanchored_project_using_fires_unbound
- text: GIVEN a C# 'using' statement that _csharp_using_violations (T-2906) is meant
    to police, WHEN the checker runs on the fixture, THEN the expected violation fires
    with zero false positives on clean code.
  evidence:
  - tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_bcl_using_is_zero_false_positives
  - tests/unit/test_support_csharp.py::TestCsharpDocblockFacetFires::test_anchored_project_using_has_zero_violations
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
src/frob/lang/_support.py already routes csharp through the _CSHARP_LANGS facet bucket (T-2906 _csharp_using_violations, T-3492) for capability/dup/docblock faceting, but there is no C# fixture proving dup-detection and docblock-checking actually fire correctly for csharp. Add a small fixture and test module.

GIVEN two near-duplicate C# methods in a fixture file, WHEN the dup detector runs, THEN it reports the duplicate pair using the _CSHARP_LANGS facet path.
GIVEN a public C# method missing an XML doc comment (///), WHEN the docblock checker runs, THEN it flags the missing docblock the same way it flags a missing Python docstring.
GIVEN a C# 'using' statement that _csharp_using_violations (T-2906) is meant to police, WHEN the checker runs on the fixture, THEN the expected violation fires with zero false positives on clean code.