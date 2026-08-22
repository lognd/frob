---
id: T-2729
title: 'LARGE001: split strata/_selfconform.py (2290 lines) by SYS1xx rule family'
state: done
kind: feature
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_selfconform.py
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires
- tests/unit/strata/test_selfconform.py::TestBindingTotality::test_laundered_capable_file_fires
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_outside_profile_fires
- tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_real_symbol_outside_declared_set_fires
- tests/unit/strata/test_selfconform.py::TestNonPythonLanguageWiring::test_sorted_capability_files_includes_typescript
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0485b1f4667d6824b63cdb83270e31f55fe732b8
---
## Description

Continuation of T-2695 (LARGE001 remainder batch 2). `src/frob/strata/
_selfconform.py` is 2290 lines (LARGE001 threshold 800). T-2695's own
body names the real seam: "SYS100-SYS107 numbered-rule seam" -- and
after direct inspection this batch confirms it: each SYS1xx rule's
violation-computation function is a distinguishable unit (e.g.
`_extended_kind_violations` (SYS100 extended), `_stale_design_violations`
(SYS101), `_coverage_totality_violations` (SYS103), `_duplicate_
interface_violations`, `_undeclared_intended_surface_violations`,
`_purpose_contract_violations`, `_binding_totality_violations`,
`_via_less_large_node_violations`, `_unmodeled_violations`/foreign-file
family), with orchestration (`check_self_conformance`, waiver
application/dedup) at the bottom of the file.

NOT attempted in T-2695 itself: several of the per-rule violation
functions share low-level helper plumbing across MULTIPLE rules (e.g.
`_observed_raw_kinds_by_node`/`_observed_kinds_for_files` feed both
SYS100's extended-kind scan and SYS101's stale-design scan), so a safe
split needs a real three-layer architecture, not a single file-move:

1. A shared "observed capability kinds" computation layer (pure
   functions over `KernelModel`/`CodeBinding`, no violation semantics of
   their own) -- used by 2+ rule functions.
2. Per-rule violation classification, one function-group per SYS1xx rule
   (or a small number of closely related rules), each importing layer 1.
3. Orchestration + waiver application/dedup (`check_self_conformance`
   and its own helpers) staying in `_selfconform.py` itself, importing
   from whichever of layers 1/2 end up in new modules.

This is real, multi-file surgery in this repo's OWN security self-
conformance checker (govern's `design/frob.strata` vs. `src/frob/`
compliance) -- doing it correctly needs its own dedicated ticket with
budget for careful helper-dependency mapping, not a rushed pass inside a
larger batch. Do NOT force a line-count-only split (T-2695's own standing
guidance); if the three-layer shape above turns out not to hold cleanly
once someone maps every helper's actual callers, waive with a specific
per-function reason instead, same discipline T-1651/T-1656 used.

Filed while working T-2695 (LARGE001 remainder batch 2) -- narrowing
that ticket's own scope rather than absorbing this file into it.