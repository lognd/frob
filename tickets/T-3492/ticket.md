---
id: T-3492
title: Wire java into vet/dup/docblock capability facets
state: done
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/**
- src/frob/dup/_exhaustiveness.py
- src/frob/gates/_docblocks.py
- src/frob/lang/_support.py
- src/frob/vet/_capability_core.py
- src/frob/vet/_capability_scan.py
- src/frob/gates/_docblocks_refs.py
- docs/modules/vet.md
- docs/modules/dup.md
- docs/modules/gates.md
- docs/modules/lang.md
- docs/guides/extending/capability-registry.md
- tests/test_capability_registry.py
- tests/test_dup.py
- tests/test_dup_exhaustiveness.py
- tests/test_gates.py
- tests/test_vet.py
- tests/test_lang_support.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_core.py
  reason: 'T-2906''s own precedent (the exact same bash/csharp facet-wiring pattern
    this ticket mirrors) needed both files: _capability_core.py''s _EXT_LANGUAGE dict
    (extension->language dispatch, without a .java entry the new java DANGEROUS_OPERATIONS
    table is never reached by a real scan) and _capability_scan.py''s _SELF_PATTERN_SUFFIXES
    (self-match exemption list for the new _dangerous_ops_java.py file''s own needle
    literals). Both are minimal, mechanical additions mirroring T-2906''s identical
    diff shape, not a scope expansion into unrelated work.'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: 'T-2906''s own precedent (the exact same bash/csharp facet-wiring pattern
    this ticket mirrors) needed both files: _capability_core.py''s _EXT_LANGUAGE dict
    (extension->language dispatch, without a .java entry the new java DANGEROUS_OPERATIONS
    table is never reached by a real scan) and _capability_scan.py''s _SELF_PATTERN_SUFFIXES
    (self-match exemption list for the new _dangerous_ops_java.py file''s own needle
    literals). Both are minimal, mechanical additions mirroring T-2906''s identical
    diff shape, not a scope expansion into unrelated work.'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_docblocks_refs.py
  reason: DOC004's fenced-block checker for java needs its own import-statement violation
    function (mirrors _csharp_using_violations exactly, T-2906's own precedent) --
    that function and its _CSHARP_USING_RE-sibling regex live in _docblocks_refs.py,
    not _docblocks.py (which only re-exports/dispatches). Same minimal, mechanical
    mirroring as the _capability_core.py/_capability_scan.py additions.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/vet.md
  reason: T-2906's own precedent touched exactly these 5 doc files to update the facet-wiring
    narrative for the new language; mirroring that for java's own wiring.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/dup.md
  reason: T-2906's own precedent touched exactly these 5 doc files to update the facet-wiring
    narrative for the new language; mirroring that for java's own wiring.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/gates.md
  reason: T-2906's own precedent touched exactly these 5 doc files to update the facet-wiring
    narrative for the new language; mirroring that for java's own wiring.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/lang.md
  reason: T-2906's own precedent touched exactly these 5 doc files to update the facet-wiring
    narrative for the new language; mirroring that for java's own wiring.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/guides/extending/capability-registry.md
  reason: T-2906's own precedent touched exactly these 5 doc files to update the facet-wiring
    narrative for the new language; mirroring that for java's own wiring.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_capability_registry.py
  reason: T-2906's own precedent updated exactly these 6 test files with per-language
    fixture entries for the new adapter language; mirroring for java's own wiring
    tests.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_dup.py
  reason: T-2906's own precedent updated exactly these 6 test files with per-language
    fixture entries for the new adapter language; mirroring for java's own wiring
    tests.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_dup_exhaustiveness.py
  reason: T-2906's own precedent updated exactly these 6 test files with per-language
    fixture entries for the new adapter language; mirroring for java's own wiring
    tests.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_gates.py
  reason: T-2906's own precedent updated exactly these 6 test files with per-language
    fixture entries for the new adapter language; mirroring for java's own wiring
    tests.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_vet.py
  reason: T-2906's own precedent updated exactly these 6 test files with per-language
    fixture entries for the new adapter language; mirroring for java's own wiring
    tests.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_lang_support.py
  reason: T-2906's own precedent updated exactly these 6 test files with per-language
    fixture entries for the new adapter language; mirroring for java's own wiring
    tests.
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'BUG002 waiver: facet-wiring ticket adds new matrix entries, no pre-existing
    failing state to repro'
  actor: logan
  at: '2026-08-30'
  old_length: 374
  new_length: 1137
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_lang_support.py::TestDeriveLanguageRegistry::test_java_capability_dup_docblock_are_implemented
- tests/test_vet.py::TestCapabilityScan::test_java_process_builder_exec_detected
- tests/test_vet.py::TestCapabilityScan::test_java_object_input_stream_deserialize_detected
- tests/test_vet.py::TestCapabilityScan::test_java_benign_file_has_no_capabilities
- tests/gates_suite/test_doc.py::TestDoc004JavaImportDrift::test_import_of_tracked_package_unanchored_warns
- tests/gates_suite/test_doc.py::TestDoc004JavaImportDrift::test_import_of_tracked_package_anchored_passes
- tests/gates_suite/test_doc.py::TestDoc004JavaImportDrift::test_import_of_jdk_package_is_not_project_internal
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6e25300ac982a9a7ebb7451459b365bca925b763
---
found while working T-1601: java gets a real frob.lang grammar/walker but the capability dangerous-op registry, dup clone-detection exhaustiveness table, and DOC004 fenced-code-block bucket have no java entry yet -- mirrors T-2906's bash/csharp facet-wiring follow-up exactly. frob.lang._support marks these three facets KNOWN_GAP for java citing this ticket in the interim.

<!-- frob:waive BUG002 reason="this is a facet-wiring/feature ticket (mirrors T-2906's identical bash/csharp precedent, itself a bug-kind ticket with the same shape), not a defect with a pre-existing failing behavior -- at the parent commit java simply had zero cells in the capability/dup/docblock matrices (no LANGUAGES entry existed yet), so test_no_unexcused_empty_cells trivially holds at parent (there is nothing to be unexcused when the language does not exist in the matrix at all) and again at the fix (every new cell is now patterned or excused); there is no failing-at-parent state to reproduce because the gap being closed is an absence of entries, not a wrong existing entry. Same posture T-2906 itself would have hit had BUG002 existed then." -->
