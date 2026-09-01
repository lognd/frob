---
id: T-3493
title: Wire cuda into vet/dup/docblock capability facets
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
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_docblocks_refs.py
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/vet.md
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/dup.md
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/gates.md
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/lang.md
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/guides/extending/capability-registry.md
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_capability_registry.py
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_dup.py
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_dup_exhaustiveness.py
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_gates.py
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_vet.py
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_lang_support.py
  reason: T-3492's own precedent (identical facet-wiring shape, same 3-file scope
    gap discovered mid-work) needed exactly these files -- pre-widening here to avoid
    the same mid-flight scope-collision churn.
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'BUG002 waiver: same shape as T-3492, no pre-existing failing state to repro
    for a new-language wiring ticket'
  actor: logan
  at: '2026-08-31'
  old_length: 402
  new_length: 1057
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_lang_support.py::TestDeriveLanguageRegistry::test_cuda_capability_dup_docblock_are_implemented
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_cuda_host_system_call_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_cuda_dlopen_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_cuda_benign_kernel_has_no_capabilities
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 4b566117b4049574f15ca2a303ba26168413dbba
---
found while working T-1602: cuda gets a real frob.lang grammar/walker but the capability dangerous-op registry, dup clone-detection exhaustiveness table, and DOC004 fenced-code-block bucket have no cuda entry yet -- mirrors T-2906's bash/csharp and T-1601's java facet-wiring follow-ups exactly (T-3492). frob.lang._support marks these three facets KNOWN_GAP for cuda citing this ticket in the interim.

<!-- frob:waive BUG002 reason="facet-wiring/feature ticket (mirrors T-3492's identical java precedent and its own accepted BUG002 waiver), not a defect with a pre-existing failing behavior -- at the parent commit cuda simply had zero cells in the capability/dup/docblock matrices (no LANGUAGES entry existed yet), so test_no_unexcused_empty_cells trivially holds at parent (nothing to be unexcused when the language does not exist in the matrix at all) and again at the fix (every new cell is now patterned or excused). No failing-at-parent state exists to reproduce because the gap being closed is an absence of entries, not a wrong existing one." -->
