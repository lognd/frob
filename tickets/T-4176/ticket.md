---
id: T-4176
title: Generalize TEST002's absent-vs-measured-zero fix (T-4138) to TEST001/003/004/009
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4138 (audit item 4: every consumer of the shared
CollectedTests/_valid_edges/_case_count path for the same conflation).

T-4138 fixed TEST002: a frob:tests edge whose evidence depends entirely
on a native test collector (rust/ts/cpp) that failed this run now reports
UNMEASURED (Severity.UNRESOLVED) via _load_tests's new third return
value, failed_test_languages, instead of a false measured-zero WARN.

The IDENTICAL conflation exists, unfixed, in:
- TEST001's naming-convention (no explicit frob:tests edge) path,
  _inferred_unit_cases -- effective==0 there also fires when the
  record's OWN file's language collector failed, not just when there is
  genuinely no convention-matching test.
- TEST003 (_test003_check_package, integration edges) -- package-level,
  so which language's failure should suppress a given package's finding
  needs more thought than TEST002's per-edge check.
- TEST004 (_test004, e2e edges) -- Severity.ERROR, the most
  consequential instance: a failed collector here BLOCKS frob check,
  not just warns.
- TEST009 (_test009, design-file e2e edges) -- same shape as TEST004,
  scoped to .strata files instead of [[system]] entries.

Extend failed_test_languages threading (already plumbed through
_GateInputs/test_gate) to all four, following T-4138's
_test002_unmeasured precedent (Severity.UNRESOLVED, distinct message,
never a silent pass). TEST004's ERROR severity makes it the highest-value
of the four to land first.

See docs/modules/gates.md#test002-unmeasured-vs-measured-zero-t-4138 for
the full audit writeup.