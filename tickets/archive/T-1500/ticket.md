---
id: T-1500
title: 'arch: LARGE001 split of vet _capability TS/rust/C/kotlin families + tail (T-1420
  delivered portion 7)'
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: T-1420
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_typescript.py
- src/frob/vet/_capability_rust.py
- src/frob/vet/_capability_c.py
- src/frob/vet/_capability_kotlin.py
- src/frob/vet/_capability_scan.py
- tests/test_vet.py
- tests/test_vet_capability.py
- tests/test_capability_registry.py
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency
- tests/test_capability_registry.py::TestIsSelfPatternPath::test_frob_repo_root_with_matching_suffix_returns_true
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_resolve_expr_peels_through_chained_assignment
designated_repro_test: null
threat: null
component: null
---
Leaf carrier for T-1420's seventh delivered portion. Implements T-1459 design
steps 3-6 (the typescript/rust/c/kotlin per-language binding families) plus a
follow-up split of the aggregation/fingerprint/opaque tail, out of
src/frob/vet/_capability.py -- WAVE20-L session.

Starting state: src/frob/vet/_capability.py was 4670 lines (steps 1-2,
_capability_core.py and _capability_python.py, already landed by a prior
session per T-1459's design doc).

Four verbatim-relocation splits, one seam per commit, all gate-verified in
the t-1420 worktree:

1. TypeScript family (_ts_*/_bind_ts_*/_resolve_ts_*/_record_ts_* plus
   _ts_binding_capabilities/_ts_binding_operations/_extra_ts_binding_operations)
   -> new src/frob/vet/_capability_typescript.py. 4670 -> 3413 lines; new
   file 1276 lines.

2. Rust family (_rust_*/_bind_rust_*/_resolve_rust_*/_record_rust_* plus
   _rust_binding_capabilities/_rust_binding_operations/_extra_rust_binding_operations)
   -> new src/frob/vet/_capability_rust.py. Discovered a genuine cross-
   family dependency: the (not-yet-split) C family's _c_scope_bind_step
   calls _record_rust_binding directly -- carried forward via re-import
   until C's own split. 3413 -> 2639 lines; new file 794 lines.

3. C/C++ family (_c_*/_record_c_*/_resolve_c_* plus _c_binding_capabilities/
   _c_binding_operations/_extra_c_binding_operations, the last three moved
   from their original out-of-order position after the kotlin block per
   T-1459's design note) -> new src/frob/vet/_capability_c.py. Imports
   _record_rust_binding from _capability_rust.py, resolving the cross-
   family dependency the rust split disclosed. 2639 -> 1849 lines; new
   file 806 lines.

4. Kotlin family (_kt_*/_record_kt_* plus _kt_binding_capabilities/
   _kt_binding_operations/_extra_kt_binding_operations) -> new
   src/frob/vet/_capability_kotlin.py. _kt_resolved_candidates is NOT
   re-imported by the dispatcher (fingerprint dispatch deliberately
   excludes kotlin, no language="kotlin" CVE_FINGERPRINTS entry).
   1859 -> 1373 lines; new file 507 lines.

All four T-1459 per-language binding families are now split out of
_capability.py.

5. Aggregation/fingerprint/opaque tail (beyond T-1459's own six-family
   design scope, per this session's dispatch): the self-path-exclusion
   machinery (_SELF_PATH/_REGISTRY_PATH/_FINGERPRINT_CATALOG_PATH/
   _SELF_PATTERN_SUFFIXES/_is_frob_repo_root/is_self_pattern_path), the
   directory/fingerprint aggregation family (_binding_fingerprints through
   _aggregate_fingerprints), and the _OpaqueFinding structural-opaqueness
   family (_split_top_level_args through _needle_construct_findings) ->
   new src/frob/vet/_capability_scan.py. _capability.py re-imports every
   __all__-listed name the tail now owns so its public surface (including
   attribute access via `_capability._scan_directory_capabilities` et al.,
   used by vet/_scan.py and _closedworld.py) is unchanged.
   _capability_scan.py needs language_for/scan_file_capabilities/
   _resolved_candidates_for_language back from _capability.py -- resolved
   with local (function-body) imports, the same circular-import pattern
   this ticket's earlier _new_renumber.py/_renumber_v2.py split
   established as precedent. 1373 -> 467 lines (first time this file has
   been under the 800-line LARGE001 threshold since the ticket started);
   new file 972 lines (still over threshold, a candidate for a future
   split of its own -- disclosed, not force-split further in this
   session).

Doc/test edges repointed same-commit throughout: tests/test_vet.py,
tests/test_vet_capability.py, and tests/test_capability_registry.py's
direct imports and frob:tests directives repointed to whichever module now
defines each symbol; docs/modules/vet.md's four frob:describes anchors for
the four functions the tail split relocated; one test assertion
(test_self_pattern_exclusion_covers_every_needle_table_module) that
hardcoded _capability.py as the file whose prose trips a drift-lock's
needle-table marker regex, updated to name _capability_scan.py (the prose
moved with it) -- and added _capability_scan.py to _SELF_PATTERN_SUFFIXES
for the exact same self-match reason, mirroring the _capability_core.py
precedent from this ticket's earlier portion.

Verification per split: pytest on tests/test_vet.py (+ tests/
test_vet_capability.py, tests/test_capability_registry.py where touched),
foreground, all passing; `frob check --only archgate --only wire --only
dead_symbols --only doclink --only docanchor --only fmt` (plus --only
opaque --only pii_structural for the tail split, since it touches
is_self_pattern_path/_opaque_indirection_findings) 0 errors after each
commit. Final combined pytest run across tests/test_vet.py, tests/
test_vet_capability.py, tests/test_capability_registry.py, tests/
test_pii_structural_gate.py, tests/unit/strata/test_effects.py, tests/
unit/strata/test_selfconform.py, tests/unit/strata/test_mode_conformance.py,
tests/unit/strata/test_conform_eval_needle.py: all passing. `git diff main
--diff-filter=D --stat` empty (no unintended deletions).

Net: src/frob/vet/_capability.py 4670 -> 462 lines. Five new sibling
modules (_capability_typescript.py 1275, _capability_rust.py 794,
_capability_c.py 805, _capability_kotlin.py 507, _capability_scan.py 972
lines).