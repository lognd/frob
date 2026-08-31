---
id: T-3493
title: Wire cuda into vet/dup/docblock capability facets
state: in-progress
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-1602: cuda gets a real frob.lang grammar/walker but the capability dangerous-op registry, dup clone-detection exhaustiveness table, and DOC004 fenced-code-block bucket have no cuda entry yet -- mirrors T-2906's bash/csharp and T-1601's java facet-wiring follow-ups exactly (T-3492). frob.lang._support marks these three facets KNOWN_GAP for cuda citing this ticket in the interim.