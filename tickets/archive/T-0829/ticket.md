---
id: T-0829
title: 'vet capability scan: _python_binding_capabilities'' per-candidate needle sweep
  is the real CPU cost once parsing is cached (T-0414); investigate trie/short-circuit'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_import_as_alias_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_from_import_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_from_import_as_detected_with_correct_kind
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_import_as_alias_operation_names_registry_entry
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_method_shadowing_import_not_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_param_shadowing_import_not_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_local_variable_shadowing_import_not_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_bare_name_call_with_no_import_not_detected
designated_repro_test: null
threat: null
component: null
---
T-0582 (perf audit re-measurement) profiled `scan_file_capabilities`
(src/frob/vet/_capability.py:2232) directly over every tracked .py file in
this repo (592 files) after confirming parsing itself is now cheap (T-0414's
`_parse` memo -- 592 misses / 1776 hits, exactly one parse per unique file
content, zero re-parse waste). The remaining 31.8s wall for 592 files is
real Python work, not caching: `_python_binding_capabilities` (line 1084)
alone accounted for ~23s of it (cProfile, `tottime` breakdown), inside
`_collect_py_candidates`/`_resolve_py_expr`/`_shadowing_scope`/`walk`.

What's algorithmically expensive: for every resolved call/attribute
candidate in a file (`_python_resolved_candidates`), `_python_binding_
capabilities` loops every not-yet-found capability kind in `table.items()`
and, for each, checks `any(_needle_matches_resolved(needle, resolved) for
needle in needles)` -- a substring containment test (`needle in resolved`,
`_capability.py:1072`). This is O(candidates * remaining_capability_kinds *
needles_per_kind) per file; measured 2.0M+ calls into the needle-match
genexpr (`_capability.py:1101`) and 1.3M+ into `_collect_py_candidates`
itself for 592 files.

This is inherent recall-oriented analysis work (T-0328's binding-aware
resolution), not an obvious redundancy bug like H5 or the refs O(n^2) scan
-- no single clear fix direction was confident enough to apply blind in a
measurement ticket. Possible directions worth investigating (NOT vetted
here): (a) precompute a single flat needle-trie (Aho-Corasick style) per
language ONCE at module load instead of re-iterating `table.items()` per
candidate, turning the per-candidate cost from O(capability_kinds *
needles) into O(len(resolved)) trie lookups; (b) short-circuit the whole
per-candidate loop once `len(found) == len(table)` (all capability kinds
already observed in this file) -- cheap to add but only helps files that
trigger every kind, likely low win in practice, worth measuring before
committing to it as the fix.

Filed rather than fixed: correctness risk of a nontrivial resolver rewrite
under a measurement ticket's scope discipline. A dedicated ticket should
prototype option (a) or (b) with its own before/after profile against this
same 592-file corpus before landing either.