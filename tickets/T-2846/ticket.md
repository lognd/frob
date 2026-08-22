---
id: T-2846
title: Split frob-core/src/lib.rs's clone-detection rungs into sibling modules
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-core/src/lib.rs
- frob-core/src/r3.rs
- frob-core/src/r4.rs
- frob-core/src/r5.rs
- frob-core/src/exact_regions.rs
- frob-core/src/callgraph.rs
evidence_scope:
- tests/test_arch_near_duplicate_native.py
- tests/test_dup_native_rungs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_over_this_repos_own_arch_tree
- tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r4_gapped_clone
- tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r5_dataflow_clone
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob-core/src/lib.rs (2297 lines) has a real seam beyond its own #[cfg(test)] test padding: the crate already extracts arch_python.rs and capability_python.rs as sibling modules (`mod arch_python; mod capability_python;`), but the crate root itself still hosts several independently-callable, already-#[pyfunction]-exposed algorithm families with no cross-calls between them -- R1.5 exact-region suffix-array matching (flatten_documents/build_suffix_array/kasai_lcp/merge_diagonals/exact_regions), R3 canonicalization/hashing (r3_canonicalize/r3_canonical_hash), R4 winnowing/candidate-pairing/tree-edit-distance (winnow_fingerprints/candidate_pairs/tree_edit_similarity/apted_similarity and their zhang-shasha/postorder/keyroots helpers), R5 anti-unification and Weisfeiler-Lehman hashing (anti_unify/anti_unify_core/anti_unify_walk/wl_hash), and a separate callgraph/arch-similarity family (called_names/referenced_names/resolve_call_edges/near_duplicate_indices/the arch_sim_* difflib-style ratio helpers).

Splitting these rungs into sibling modules (mirroring arch_python.rs/capability_python.rs's own extraction pattern already in this crate) is real, tracked work -- design/frob.strata's `frob-core/src/**` glob already covers any new file here with no additional capability grant needed, so this is lower-risk than a src/frob package-internal split. Rejected in T-2824 purely on scope grounds: new files are not covered by T-2824's enumerated file-list scope.