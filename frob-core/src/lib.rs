//! frob-core: compute-only clone-detection kernels for frob.dup (docs/modules/dup.md).
//!
//! Every function here is data-in/data-out: serialized token lists in,
//! fingerprints/hashes/distances out. No IO, no caching policy, no git
//! awareness -- that all stays in Python (frob.dup._pipeline). Errors never
//! cross this boundary; a malformed input is a Python-side validation bug,
//! not something this crate defends against.

// T-2846: the R1.5/R3/R4/R5/callgraph rungs previously lived here directly.
// The earlier LARGE001 waiver on this file claimed pyo3's #[pymodule]
// registration needed every #[pyfunction] visible in crate-root scope --
// false: this crate already registers extract_tree_*/scan_python_capabilities/
// py_function_metrics from sibling modules (extract.rs/capability_python.rs/
// arch_python.rs) via plain `use` imports below, and wrap_pyfunction! only
// needs the name in scope, not defined in this file. Measured zero cross-
// calls between the five rungs (only `hash_str` is shared, kept here as
// `pub(crate)`), so each rung moved to its own sibling module below,
// mirroring arch_python.rs/capability_python.rs's own extraction pattern.
// This shrank the file from 2297 to 932 lines but did not clear LARGE001's
// 500-line threshold on its own, so a fresh waiver replaces the old one:

// frob:waive LARGE001 reason="post-T-2846 shape: 834 of this file's 932 lines (line 66 on) are \
// its own #[cfg(test)] mod tests block, the idiomatic Rust convention of colocating unit tests \
// with the code they test rather than a separate tests/ directory -- not production-code bulk. \
// The remaining ~98 lines are the module doc, the mod/use declarations wiring in this crate's six \
// sibling kernel/binding modules (arch_python, callgraph, capability_python, exact_regions, \
// extract, r3, r4, r5), the shared hash_str helper genuinely used by two of those rungs, and the \
// pymodule registration function -- there is no further rung left to extract; this is the \
// crate-root wiring itself, mirroring strata-core/src/lib.rs's own identical post-split LARGE001 \
// waiver shape."

use pyo3::prelude::*;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

mod arch_python;
mod callgraph;
mod capability_python;
mod exact_regions;
mod extract;
mod r3;
mod r4;
mod r5;
use arch_python::py_function_metrics;
use callgraph::{
    called_names, near_duplicate_indices, ordered_called_names, referenced_names,
    resolve_call_edges, unresolved_exempt_names,
};
use capability_python::scan_python_capabilities;
use exact_regions::exact_regions as run_exact_regions;
use extract::{extract_tree_cpp, extract_tree_python, extract_tree_rust, extract_tree_typescript};
use r3::r3_canonical_hash;
use r4::{apted_similarity, candidate_pairs, tree_edit_similarity, winnow_fingerprints};
use r5::{anti_unify, wl_hash};
#[cfg(test)]
use callgraph::arch_sim_ratio;
#[cfg(test)]
use exact_regions::{build_suffix_array, kasai_lcp};
#[cfg(test)]
use r3::{is_numeric_literal, is_string_literal};
#[cfg(test)]
use r4::{build_postorder, zhang_shasha_distance};
#[cfg(test)]
use r5::anti_unify_core;
#[cfg(test)]
use r5::AntiUnifyErr;
#[cfg(test)]
use std::collections::HashMap;

/// Deterministic 64-bit hash of one token (std `DefaultHasher` is
/// unkeyed/deterministic across runs, unlike `HashMap`'s `RandomState`).
pub(crate) fn hash_str(s: &str) -> u64 {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
    let mut h = DefaultHasher::new();
    s.hash(&mut h);
    h.finish()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_hash_is_deterministic_and_shape_sensitive() {
        // frob:tests frob-core/src/r3.rs::r3_canonical_hash kind="unit"
        // frob:tests frob-core/src/lib.rs::hash_str kind="unit"
        let a = vec!["def".into(), "_v0".into(), "return".into(), "_v0".into()];
        let b = vec!["def".into(), "_v0".into(), "return".into(), "_v0".into()];
        let c = vec!["def".into(), "_v0".into(), "return".into(), "_N_".into()];
        assert_eq!(r3_canonical_hash(a.clone()), r3_canonical_hash(b));
        assert_ne!(r3_canonical_hash(a), r3_canonical_hash(c));
    }

    #[test]
    fn r3_literal_abstraction_collapses_differing_constants() {
        // frob:tests frob-core/src/r3.rs::r3_canonical_hash kind="unit"
        let a = vec![
            "def".into(),
            "_v0".into(),
            "return".into(),
            "_v0".into(),
            "+".into(),
            "1".into(),
        ];
        let b = vec![
            "def".into(),
            "_v0".into(),
            "return".into(),
            "_v0".into(),
            "+".into(),
            "2".into(),
        ];
        assert_eq!(r3_canonical_hash(a), r3_canonical_hash(b));
    }

    #[test]
    fn r3_literal_abstraction_does_not_collapse_different_operators() {
        // frob:tests frob-core/src/r3.rs::r3_canonical_hash kind="unit"
        let plus = vec![
            "def".into(),
            "_v0".into(),
            "return".into(),
            "_v0".into(),
            "+".into(),
            "1".into(),
        ];
        let minus = vec![
            "def".into(),
            "_v0".into(),
            "return".into(),
            "_v0".into(),
            "-".into(),
            "1".into(),
        ];
        assert_ne!(r3_canonical_hash(plus), r3_canonical_hash(minus));
    }

    #[test]
    fn r3_elif_desugar_matches_manually_nested_if_else() {
        // frob:tests frob-core/src/r3.rs::r3_canonical_hash kind="unit"
        let with_elif = vec![
            "if".into(),
            "_v0".into(),
            ":".into(),
            "return".into(),
            "1".into(),
            "elif".into(),
            "_v0".into(),
            ":".into(),
            "return".into(),
            "2".into(),
            "else".into(),
            ":".into(),
            "return".into(),
            "3".into(),
        ];
        let nested = vec![
            "if".into(),
            "_v0".into(),
            ":".into(),
            "return".into(),
            "1".into(),
            "else".into(),
            ":".into(),
            "if".into(),
            "_v0".into(),
            ":".into(),
            "return".into(),
            "2".into(),
            "else".into(),
            ":".into(),
            "return".into(),
            "3".into(),
        ];
        assert_eq!(r3_canonical_hash(with_elif), r3_canonical_hash(nested));
    }

    #[test]
    fn r3_elif_desugar_does_not_collapse_different_conditions() {
        // frob:tests frob-core/src/r3.rs::r3_canonical_hash kind="unit"
        let a = vec![
            "if".into(),
            "_v0".into(),
            ":".into(),
            "return".into(),
            "1".into(),
            "elif".into(),
            "_v1".into(),
            ":".into(),
            "return".into(),
            "2".into(),
        ];
        let b = vec![
            "if".into(),
            "_v0".into(),
            ":".into(),
            "return".into(),
            "1".into(),
            "elif".into(),
            "_v2".into(),
            ":".into(),
            "return".into(),
            "2".into(),
        ];
        assert_ne!(r3_canonical_hash(a), r3_canonical_hash(b));
    }

    #[test]
    fn is_numeric_literal_rejects_identifiers_and_keywords() {
        // frob:tests frob-core/src/r3.rs::is_numeric_literal kind="unit"
        assert!(is_numeric_literal("1"));
        assert!(is_numeric_literal("-3"));
        assert!(is_numeric_literal("2.5"));
        assert!(!is_numeric_literal("_v0"));
        assert!(!is_numeric_literal("return"));
        assert!(!is_numeric_literal(""));
        assert!(!is_numeric_literal("1.2.3"));
    }

    #[test]
    fn is_string_literal_requires_matching_quotes() {
        // frob:tests frob-core/src/r3.rs::is_string_literal kind="unit"
        assert!(is_string_literal("\"hi\""));
        assert!(is_string_literal("'hi'"));
        assert!(!is_string_literal("hi"));
        assert!(!is_string_literal("\""));
    }

    #[test]
    fn winnow_fingerprints_nonempty_for_long_enough_token_stream() {
        let toks: Vec<String> = (0..20).map(|i| format!("t{}", i)).collect();
        let fps = winnow_fingerprints(toks, 4, 4);
        assert!(!fps.is_empty());
    }

    #[test]
    fn candidate_pairs_finds_shared_bucket() {
        let sets = vec![vec![1u64, 2, 3], vec![2u64, 3, 4], vec![99u64]];
        let pairs = candidate_pairs(sets, 2);
        assert_eq!(pairs, vec![(0, 1)]);
    }

    #[test]
    fn candidate_pairs_never_emits_a_self_pair() {
        // frob:tests frob-core/src/r4.rs::candidate_pairs kind="unit"
        // Regression for T-0268: a region whose own fingerprint set
        // contains a duplicate value indexes itself twice into the same
        // bucket, which previously produced a self-pair (i, i) once that
        // region's own duplicate-value collision count reached min_shared.
        let sets = vec![vec![7u64, 7, 7], vec![99u64]];
        let pairs = candidate_pairs(sets, 2);
        assert!(
            pairs.iter().all(|&(i, j)| i != j),
            "candidate_pairs returned a self-pair: {:?}",
            pairs
        );
        assert!(pairs.is_empty());
    }

    #[test]
    fn tree_edit_similarity_identical_sequences_is_one() {
        let a = vec![1u64, 2, 3];
        let (sim, alignment) = tree_edit_similarity(a.clone(), a);
        assert!((sim - 1.0).abs() < 1e-9);
        assert_eq!(alignment, vec![(0, 0), (1, 1), (2, 2)]);
    }

    #[test]
    fn tree_edit_similarity_disjoint_sequences_is_zero() {
        let a = vec![1u64, 2, 3];
        let b = vec![9u64, 8, 7];
        let (sim, _) = tree_edit_similarity(a, b);
        assert!(sim.abs() < 1e-9);
    }

    #[test]
    fn wl_hash_isomorphic_relabeled_graphs_collide() {
        // frob:tests frob-core/src/r5.rs::wl_hash kind="unit"
        // Triangle a-b-c with labels ["def", "use", "use"], vs the same
        // triangle with nodes renumbered -- 1-WL must be invariant to that.
        let labels_a = vec!["def".to_string(), "use".to_string(), "use".to_string()];
        let adj_a = vec![(0usize, 1usize), (1, 2), (2, 0)];
        let labels_b = vec!["use".to_string(), "def".to_string(), "use".to_string()];
        let adj_b = vec![(1usize, 0usize), (0, 2), (2, 1)];
        assert_eq!(wl_hash(adj_a, labels_a, 2), wl_hash(adj_b, labels_b, 2));
    }

    #[test]
    fn wl_hash_structurally_different_graphs_differ() {
        // A path of 3 nodes vs a triangle of 3 nodes, same labels.
        let labels = vec!["a".to_string(), "a".to_string(), "a".to_string()];
        let path = vec![(0usize, 1usize), (1, 2)];
        let triangle = vec![(0usize, 1usize), (1, 2), (2, 0)];
        assert_ne!(
            wl_hash(path, labels.clone(), 2),
            wl_hash(triangle, labels, 2)
        );
    }

    #[test]
    fn wl_hash_empty_graph_is_zero() {
        assert_eq!(wl_hash(Vec::new(), Vec::new(), 2), 0);
    }

    #[test]
    fn apted_identical_trees_is_similarity_one() {
        // frob:tests frob-core/src/r4.rs::apted_similarity kind="unit"
        // frob:tests frob-core/src/r4.rs::build_postorder kind="unit"
        // frob:tests frob-core/src/r4.rs::zhang_shasha_distance kind="unit"
        // def -> [return, name]  (a 3-node tree: root + 2 leaf children)
        let labels = vec!["def".into(), "return".into(), "name".into()];
        let parents = vec![-1i64, 0, 0];
        let sim = apted_similarity(labels.clone(), parents.clone(), labels, parents);
        assert!((sim - 1.0).abs() < 1e-9);
    }

    #[test]
    fn apted_disjoint_single_leaf_trees_is_zero_similarity() {
        let sim = apted_similarity(
            vec!["a".into()],
            vec![-1i64],
            vec!["b".into()],
            vec![-1i64],
        );
        assert!(sim.abs() < 1e-9);
    }

    #[test]
    fn apted_catches_within_statement_restructuring() {
        // Tree A: add(x, y) as add -> [x, y]
        // Tree B: add(y, x) as add -> [y, x] -- same flat token multiset,
        // different tree shape/order. A flat statement hash (the old
        // tree_edit_similarity's unit) cannot distinguish operand order
        // within one "statement"; a real tree metric can via rename cost
        // at matching positions.
        let labels_a = vec!["add".into(), "x".into(), "y".into()];
        let parents_a = vec![-1i64, 0, 0];
        let labels_b = vec!["add".into(), "y".into(), "x".into()];
        let parents_b = vec![-1i64, 0, 0];
        let sim = apted_similarity(labels_a, parents_a, labels_b, parents_b);
        // Not identical (rename cost at the two leaf positions), but still
        // highly similar (same root label, same arity/shape).
        assert!(sim < 1.0);
        assert!(sim > 0.0);
    }

    #[test]
    fn apted_inserted_node_costs_one() {
        // Tree A: root -> [a]
        // Tree B: root -> [a, b]  (one inserted leaf)
        let labels_a = vec!["root".into(), "a".into()];
        let parents_a = vec![-1i64, 0];
        let labels_b = vec!["root".into(), "a".into(), "b".into()];
        let parents_b = vec![-1i64, 0, 0];
        let dist = zhang_shasha_distance(
            &labels_a,
            &build_postorder(&parents_a).0,
            &build_postorder(&parents_a).1,
            &labels_b,
            &build_postorder(&parents_b).0,
            &build_postorder(&parents_b).1,
        );
        assert_eq!(dist, 1);
    }

    #[test]
    fn apted_empty_vs_empty_is_similarity_one() {
        let sim = apted_similarity(Vec::new(), Vec::new(), Vec::new(), Vec::new());
        assert!((sim - 1.0).abs() < 1e-9);
    }

    #[test]
    fn anti_unify_identical_trees_has_zero_holes() {
        // frob:tests frob-core/src/r5.rs::anti_unify_core kind="unit"
        let labels = vec!["def".into(), "return".into(), "name".into()];
        let parents = vec![-1i64, 0, 0];
        let tpl = anti_unify_core(&labels, &parents, &labels, &parents).unwrap();
        assert_eq!(tpl.labels, labels);
        assert_eq!(tpl.parents, parents);
        assert!(tpl.bindings_a.is_empty());
        assert!(tpl.bindings_b.is_empty());
    }

    #[test]
    fn anti_unify_single_leaf_divergence_binds_one_hole() {
        // frob:tests frob-core/src/r5.rs::anti_unify_core kind="unit"
        // Tree A: def -> [return, x]   Tree B: def -> [return, y]
        // Two near-identical trees differing in one leaf: the shared
        // "def"/"return" shape is kept, the leaf becomes $hole_0 bound
        // to (x's index, y's index).
        let labels_a = vec!["def".into(), "return".into(), "x".into()];
        let parents_a = vec![-1i64, 0, 0];
        let labels_b = vec!["def".into(), "return".into(), "y".into()];
        let parents_b = vec![-1i64, 0, 0];
        let tpl = anti_unify_core(&labels_a, &parents_a, &labels_b, &parents_b).unwrap();
        assert_eq!(tpl.labels, vec!["def", "return", "$hole_0"]);
        assert_eq!(tpl.parents, vec![-1i64, 0, 0]);
        assert_eq!(tpl.bindings_a, vec![(0usize, 2usize)]);
        assert_eq!(tpl.bindings_b, vec![(0usize, 2usize)]);
    }

    #[test]
    fn anti_unify_arity_mismatch_becomes_a_hole_not_a_crash() {
        // frob:tests frob-core/src/r5.rs::anti_unify_core kind="unit"
        // Tree A: root -> [shared, mid -> [a]]
        // Tree B: root -> [shared, mid -> [a, b]]
        // root and the leading "shared" child match; "mid"'s child count
        // differs (1 vs 2) so *that* subtree becomes a hole -- without
        // panicking/crashing -- while the surrounding shared shape stays.
        let labels_a = vec!["root".into(), "shared".into(), "mid".into(), "a".into()];
        let parents_a = vec![-1i64, 0, 0, 2];
        let labels_b = vec![
            "root".into(),
            "shared".into(),
            "mid".into(),
            "a".into(),
            "b".into(),
        ];
        let parents_b = vec![-1i64, 0, 0, 2, 2];
        let tpl = anti_unify_core(&labels_a, &parents_a, &labels_b, &parents_b).unwrap();
        assert_eq!(tpl.labels, vec!["root", "shared", "$hole_0"]);
        assert_eq!(tpl.bindings_a, vec![(0usize, 2usize)]);
        assert_eq!(tpl.bindings_b, vec![(0usize, 2usize)]);
    }

    #[test]
    fn anti_unify_wildly_different_trees_exceeds_hole_ceiling() {
        // frob:tests frob-core/src/r5.rs::anti_unify_core kind="unit"
        // HOLE-CEILING sanity: two trees sharing nothing generalize to a
        // single root-level hole, which is 100% holes -- Err, not a
        // useless one-hole "template".
        let labels_a = vec!["def".into(), "x".into(), "y".into()];
        let parents_a = vec![-1i64, 0, 0];
        let labels_b = vec!["class".into(), "p".into(), "q".into(), "r".into()];
        let parents_b = vec![-1i64, 0, 0, 0];
        let err = anti_unify_core(&labels_a, &parents_a, &labels_b, &parents_b).unwrap_err();
        assert_eq!(err, AntiUnifyErr::HoleCeilingExceeded);
    }

    #[test]
    fn anti_unify_empty_vs_empty_is_empty_template() {
        let tpl = anti_unify_core(&[], &[], &[], &[]).unwrap();
        assert!(tpl.labels.is_empty());
        assert!(tpl.bindings_a.is_empty());
    }

    #[test]
    fn anti_unify_deterministic_hole_numbering() {
        // frob:tests frob-core/src/r5.rs::anti_unify_core kind="unit"
        // Same input run twice must number holes identically -- left-to-
        // right, top-down (preorder emission order), so the template is
        // stable/testable across runs.
        // root -> [s1, dA1, s2, dA2] / root -> [s1, dB1, s2, dB2]:
        // two divergent leaves interleaved with two shared ones, keeping
        // the hole ratio at 40% (under the ceiling) while still exercising
        // multi-hole numbering order.
        let labels_a = vec![
            "root".into(),
            "s1".into(),
            "dA1".into(),
            "s2".into(),
            "dA2".into(),
        ];
        let parents_a = vec![-1i64, 0, 0, 0, 0];
        let labels_b = vec![
            "root".into(),
            "s1".into(),
            "dB1".into(),
            "s2".into(),
            "dB2".into(),
        ];
        let parents_b = vec![-1i64, 0, 0, 0, 0];
        let first = anti_unify_core(&labels_a, &parents_a, &labels_b, &parents_b).unwrap();
        let second = anti_unify_core(&labels_a, &parents_a, &labels_b, &parents_b).unwrap();
        assert_eq!(first.labels, second.labels);
        assert_eq!(first.bindings_a, second.bindings_a);
        assert_eq!(first.bindings_b, second.bindings_b);
        assert_eq!(first.labels, vec!["root", "s1", "$hole_0", "s2", "$hole_1"]);
        assert_eq!(first.bindings_a, vec![(0usize, 2usize), (1usize, 4usize)]);
        assert_eq!(first.bindings_b, vec![(0usize, 2usize), (1usize, 4usize)]);
    }

    #[test]
    fn anti_unify_pyfunction_wraps_hole_ceiling_as_false_sentinel() {
        // The #[pyfunction] boundary never raises for a hole-ceiling
        // failure -- confirms the (ok, ...) sentinel tuple shape.
        let labels_a = vec!["def".into(), "x".into(), "y".into()];
        let parents_a = vec![-1i64, 0, 0];
        let labels_b = vec!["class".into(), "p".into(), "q".into(), "r".into()];
        let parents_b = vec![-1i64, 0, 0, 0];
        let (ok, labels, parents, bindings_a, bindings_b) =
            anti_unify(labels_a, parents_a, labels_b, parents_b);
        assert!(!ok);
        assert!(labels.is_empty());
        assert!(parents.is_empty());
        assert!(bindings_a.is_empty());
        assert!(bindings_b.is_empty());
    }

    #[test]
    fn exact_regions_finds_shared_block_inside_different_functions() {
        // frob:tests frob-core/src/exact_regions.rs::exact_regions kind="unit"
        // frob:tests frob-core/src/exact_regions.rs::build_suffix_array kind="unit"
        // frob:tests frob-core/src/exact_regions.rs::kasai_lcp kind="unit"
        // Two otherwise-different token streams sharing one 6-token block
        // in the middle -- the exact shape R1/R2 (whole-body hashing)
        // cannot see, since neither whole body is identical or an alpha-
        // rename of the other.
        let shared = vec!["if", "x", ">", "0", "return", "x"];
        let doc_a: Vec<String> = ["def", "foo", "("]
            .iter()
            .chain(shared.iter())
            .chain(["else", "return", "0"].iter())
            .map(|s| s.to_string())
            .collect();
        let doc_b: Vec<String> = ["def", "bar", "(", "y", ")"]
            .iter()
            .chain(shared.iter())
            .chain(["print", "y"].iter())
            .map(|s| s.to_string())
            .collect();
        let (regions, truncated) = run_exact_regions(vec![doc_a.clone(), doc_b.clone()], shared.len(), 10_000);
        assert!(!truncated);
        assert_eq!(regions.len(), 1);
        let (da, oa, db, ob, l) = regions[0];
        assert_eq!(da, 0);
        assert_eq!(db, 1);
        assert_eq!(l, shared.len());
        assert_eq!(&doc_a[oa..oa + l], shared.as_slice());
        assert_eq!(&doc_b[ob..ob + l], shared.as_slice());
    }

    #[test]
    fn exact_regions_below_min_len_reports_nothing() {
        let shared = vec!["a", "b", "c"];
        let doc_a: Vec<String> = shared.iter().map(|s| s.to_string()).collect();
        let doc_b: Vec<String> = shared.iter().map(|s| s.to_string()).collect();
        let (regions, _) = run_exact_regions(vec![doc_a, doc_b], 10, 10_000);
        assert!(regions.is_empty());
    }

    #[test]
    fn exact_regions_no_match_across_wholly_different_documents() {
        let doc_a: Vec<String> = vec!["a".into(), "b".into(), "c".into(), "d".into()];
        let doc_b: Vec<String> = vec!["w".into(), "x".into(), "y".into(), "z".into()];
        let (regions, _) = run_exact_regions(vec![doc_a, doc_b], 2, 10_000);
        assert!(regions.is_empty());
    }

    #[test]
    fn exact_regions_does_not_match_across_document_boundary() {
        // The sentinel between documents must prevent a suffix straddling
        // the boundary from being reported as a match with anything.
        let doc_a: Vec<String> = vec!["p".into(), "q".into(), "r".into()];
        let doc_b: Vec<String> = vec!["r".into(), "s".into(), "t".into()];
        let (regions, _) = run_exact_regions(vec![doc_a, doc_b], 1, 10_000);
        // "r" alone (length 1) legitimately matches (doc0 offset 2, doc1
        // offset 0) -- but nothing longer, since "r","s" (from b) never
        // equals a real 2-token run present in doc_a.
        for (_, _, _, _, l) in &regions {
            assert!(*l <= 1);
        }
    }

    #[test]
    fn exact_regions_merges_overlapping_suffix_pairs_into_one_maximal_region() {
        // A longer shared block should be reported once, at full length --
        // not fragmented into many overlapping shorter sub-matches (one
        // per SA-adjacent suffix pair), which is what merge_diagonals
        // exists to collapse.
        let shared: Vec<String> = (0..12).map(|i| format!("t{i}")).collect();
        let doc_a = shared.clone();
        let doc_b = shared.clone();
        let (regions, _) = run_exact_regions(vec![doc_a, doc_b], 3, 10_000);
        assert_eq!(regions.len(), 1);
        assert_eq!(regions[0].4, shared.len());
    }

    #[test]
    fn exact_regions_empty_input_is_empty_output() {
        let (regions, truncated) = run_exact_regions(Vec::new(), 1, 10_000);
        assert!(regions.is_empty());
        assert!(!truncated);
        let (regions, _) = run_exact_regions(vec![vec!["a".into()]], 0, 10_000);
        assert!(regions.is_empty());
    }

    /// True if `regions` contains a pair naming exactly `(doc_x, doc_y)`
    /// (either order) with `length >= min_len` -- the shape a caller of
    /// `exact_regions` actually cares about, not exact offsets.
    fn has_pair(
        regions: &[(usize, usize, usize, usize, usize)],
        doc_x: usize,
        doc_y: usize,
        min_len: usize,
    ) -> bool {
        regions.iter().any(|&(da, _, db, _, l)| {
            l >= min_len && ((da == doc_x && db == doc_y) || (da == doc_y && db == doc_x))
        })
    }

    #[test]
    fn exact_regions_three_identical_documents_reports_all_three_pairs() {
        // frob:tests frob-core/src/exact_regions.rs::exact_regions kind="unit"
        // Regression for the reviewer-caught bug (T-0193 round 2): only
        // SA-adjacent suffix pairs were compared, so a block repeated in
        // 3+ documents silently dropped non-adjacent occurrence pairs --
        // e.g. (doc0, doc2) when doc1's matching suffix sorted between
        // them in the suffix array.
        let block: Vec<String> = ["a", "b", "c", "d"].iter().map(|s| s.to_string()).collect();
        let docs = vec![block.clone(), block.clone(), block.clone()];
        let (regions, _) = run_exact_regions(docs, 2, 10_000);
        assert!(has_pair(&regions, 0, 1, 4), "missing (doc0, doc1): {regions:?}");
        assert!(has_pair(&regions, 0, 2, 4), "missing (doc0, doc2): {regions:?}");
        assert!(has_pair(&regions, 1, 2, 4), "missing (doc1, doc2): {regions:?}");
    }

    #[test]
    fn exact_regions_four_way_shared_block_reports_every_pair() {
        // frob:tests frob-core/src/exact_regions.rs::exact_regions kind="unit"
        let block: Vec<String> = (0..6).map(|i| format!("w{i}")).collect();
        let docs = vec![block.clone(), block.clone(), block.clone(), block.clone()];
        let (regions, _) = run_exact_regions(docs, 3, 10_000);
        for x in 0..4 {
            for y in (x + 1)..4 {
                assert!(has_pair(&regions, x, y, 6), "missing ({x}, {y}): {regions:?}");
            }
        }
    }

    #[test]
    fn exact_regions_mixed_case_two_nested_shared_regions() {
        // frob:tests frob-core/src/exact_regions.rs::exact_regions kind="unit"
        // Three documents share region A ("p q r s"); only two of those
        // three (doc0, doc1) additionally share a second region B
        // ("m n o", immediately following A) that doc2 does not have at
        // all. Both groupings must come out correctly -- A across all
        // three pairs, and doc0/doc1's match must extend past A's length
        // (proving B was actually captured, not just A reported again).
        let region_a: Vec<&str> = vec!["p", "q", "r", "s"];
        let region_b: Vec<&str> = vec!["m", "n", "o"];
        let mk = |extra: &[&str]| -> Vec<String> {
            region_a
                .iter()
                .chain(extra.iter())
                .map(|s| s.to_string())
                .collect()
        };
        let doc0 = mk(&region_b);
        let doc1 = mk(&region_b);
        let doc2 = mk(&["x", "y", "z"]); // no region B
        let (regions, _) = run_exact_regions(vec![doc0, doc1, doc2], 3, 10_000);

        // Region A (length 4) ties all three documents together.
        assert!(has_pair(&regions, 0, 1, 4), "missing region-A (doc0,doc1): {regions:?}");
        assert!(has_pair(&regions, 0, 2, 4), "missing region-A (doc0,doc2): {regions:?}");
        assert!(has_pair(&regions, 1, 2, 4), "missing region-A (doc1,doc2): {regions:?}");

        // Region B (length 3) only ties doc0/doc1 -- and specifically at
        // length >= 3+4=7 they must share more than just region A alone,
        // proving region B was actually found (not merely region A
        // reported twice under a coincidentally-passing length check).
        assert!(
            regions
                .iter()
                .any(|&(da, _, db, _, l)| (da == 0 && db == 1) && l >= 7),
            "expected a doc0/doc1 match covering both region A and B: {regions:?}"
        );
    }

    #[test]
    fn exact_regions_run_size_guard_bounds_pair_emission_on_a_large_run() {
        // frob:tests frob-core/src/exact_regions.rs::exact_regions kind="unit"
        // T-0273: reviewer finding on T-0193 -- 2000 identical documents
        // sharing a block produced 1,999,000 unbounded pairs. With the
        // default cap (200) a 500-document run must emit at most
        // C(200, 2) = 19,900 pairs, never the unbounded C(500, 2) =
        // 124,750, and the truncation signal must be set so a caller
        // never mistakes the capped result for exhaustive.
        let block: Vec<String> = ["a", "b", "c", "d"].iter().map(|s| s.to_string()).collect();
        let docs: Vec<Vec<String>> = (0..500).map(|_| block.clone()).collect();
        let (regions, truncated) = run_exact_regions(docs, 2, 200);
        assert!(truncated, "500-document identical run must be flagged truncated");
        let max_uncapped_pairs = 500usize * 499 / 2;
        let cap_pairs = 200usize * 199 / 2;
        assert!(
            regions.len() <= cap_pairs,
            "expected <= {cap_pairs} pairs from the capped run, got {} (unbounded would be {max_uncapped_pairs})",
            regions.len()
        );
        assert!(!regions.is_empty(), "the capped run must still report something");
    }

    #[test]
    fn exact_regions_run_size_guard_does_not_trip_below_the_cap() {
        // frob:tests frob-core/src/exact_regions.rs::exact_regions kind="unit"
        // A run at or below max_run_size is unaffected: no truncation
        // signal, and every pair among the (small) run is still reported.
        let block: Vec<String> = ["a", "b", "c", "d"].iter().map(|s| s.to_string()).collect();
        let docs: Vec<Vec<String>> = (0..5).map(|_| block.clone()).collect();
        let (regions, truncated) = run_exact_regions(docs, 2, 200);
        assert!(!truncated);
        assert_eq!(regions.len(), 5 * 4 / 2);
    }

    #[test]
    fn suffix_array_and_kasai_lcp_agree_on_a_hand_checked_case() {
        // s = "banana" as token ids in alphabetical order (a=0,b=1,n=2), so
        // numeric comparison order matches the well-known string result.
        let s: Vec<i64> = vec![1, 0, 2, 0, 2, 0];
        let sa = build_suffix_array(&s);
        // Suffixes sorted lexicographically: a<a<a n<n na<na b -> standard
        // "banana" suffix array (0-indexed): [5,3,1,0,4,2]
        assert_eq!(sa, vec![5, 3, 1, 0, 4, 2]);
        let lcp = kasai_lcp(&s, &sa);
        assert_eq!(lcp, vec![0, 1, 3, 0, 0, 2]);
    }

    // frob:tests frob-core/src/callgraph.rs::resolve_call_edges kind="unit"
    #[test]
    fn resolve_call_edges_matches_private_callee_and_skips_self_and_public() {
        let by_name: HashMap<String, Vec<(String, String, bool)>> = HashMap::from([
            (
                "helper".to_string(),
                vec![("a.py::helper".to_string(), "a.py".to_string(), true)],
            ),
            (
                "public_fn".to_string(),
                vec![("a.py::public_fn".to_string(), "a.py".to_string(), false)],
            ),
        ]);
        let out = resolve_call_edges(
            vec!["a.py::caller".to_string()],
            vec![vec![
                "helper".to_string(),
                "public_fn".to_string(),
                "helper".to_string(), // self-call to a name equal to caller's own symref is a separate case below
            ]],
            vec![vec![]],
            by_name,
            false,
            "?unresolved".to_string(),
        );
        assert_eq!(
            out,
            vec![(
                "a.py::caller".to_string(),
                vec!["a.py::helper".to_string(), "a.py::helper".to_string()]
            )]
        );
    }

    #[test]
    fn resolve_call_edges_excludes_self_reference() {
        let by_name: HashMap<String, Vec<(String, String, bool)>> = HashMap::from([(
            "caller".to_string(),
            vec![("a.py::caller".to_string(), "a.py".to_string(), true)],
        )]);
        let out = resolve_call_edges(
            vec!["a.py::caller".to_string()],
            vec![vec!["caller".to_string()]],
            vec![vec![]],
            by_name,
            false,
            "?unresolved".to_string(),
        );
        assert!(out.is_empty());
    }

    #[test]
    fn resolve_call_edges_marks_unresolved_private_looking_miss_unless_exempt() {
        let by_name: HashMap<String, Vec<(String, String, bool)>> = HashMap::new();
        let unresolved = resolve_call_edges(
            vec!["a.py::caller".to_string()],
            vec![vec!["_missing".to_string()]],
            vec![vec![]],
            by_name.clone(),
            true,
            "?unresolved".to_string(),
        );
        assert_eq!(
            unresolved,
            vec![(
                "a.py::caller".to_string(),
                vec!["?unresolved".to_string()]
            )]
        );

        let exempted = resolve_call_edges(
            vec!["a.py::caller".to_string()],
            vec![vec!["_missing".to_string()]],
            vec![vec!["_missing".to_string()]],
            by_name,
            true,
            "?unresolved".to_string(),
        );
        assert!(exempted.is_empty());
    }

    // frob:tests frob-core/src/callgraph.rs::called_names kind="unit"
    #[test]
    fn called_names_rescues_wrapper_marker_argument() {
        let tokens: Vec<String> = ["memoize_per_run", "(", "_target", ")"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let mut names = called_names(tokens, vec!["memoize_per_run".to_string()]);
        names.sort();
        assert_eq!(
            names,
            vec!["_target".to_string(), "memoize_per_run".to_string()]
        );
    }

    #[test]
    fn ordered_called_names_preserves_order_and_duplicates() {
        let tokens: Vec<String> = ["_a", "(", ")", "_b", "(", ")", "_a", "(", ")"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let names = ordered_called_names(tokens, vec![]);
        assert_eq!(
            names,
            vec!["_a".to_string(), "_b".to_string(), "_a".to_string()]
        );
    }

    #[test]
    fn referenced_names_covers_signature_and_body_deduped() {
        let sig: Vec<String> = ["self", "arg"].iter().map(|s| s.to_string()).collect();
        let body: Vec<String> = ["arg", "+", "1"].iter().map(|s| s.to_string()).collect();
        let mut names = referenced_names(sig, body);
        names.sort();
        assert_eq!(
            names,
            vec!["arg".to_string(), "self".to_string()]
        );
    }

    #[test]
    fn unresolved_exempt_names_exempts_only_pure_foreign_attribute_calls() {
        // `self._foo()` (confident, never exempt) and `obj._bar()` (always
        // an attribute call on a non-self receiver, always exempt).
        let tokens: Vec<String> = [
            "self", ".", "_foo", "(", ")", "obj", ".", "_bar", "(", ")",
        ]
        .iter()
        .map(|s| s.to_string())
        .collect();
        let mut exempt = unresolved_exempt_names(tokens);
        exempt.sort();
        assert_eq!(exempt, vec!["_bar".to_string()]);
    }

    // frob:tests frob-core/src/callgraph.rs::arch_sim_ratio kind="unit"
    #[test]
    fn arch_sim_ratio_matches_difflib_golden_values() {
        // Expected values captured directly from
        // `difflib.SequenceMatcher(None, a, b).ratio()` (T-0953 parity bar
        // -- byte-identical, not approximate).
        let cases: [(&str, &str, f64); 4] = [
            ("abcde", "abcde", 1.0),
            ("abcde", "fghij", 0.0),
            (
                "the quick brown fox",
                "the quick brown dog",
                0.8947368421052632,
            ),
            ("aaaaaaaaaa", "aaaaaaaaab", 0.9),
        ];
        for (a, b, expected) in cases {
            let av: Vec<char> = a.chars().collect();
            let bv: Vec<char> = b.chars().collect();
            let ratio = arch_sim_ratio(&av, &bv);
            assert!(
                (ratio - expected).abs() < 1e-12,
                "a={a:?} b={b:?} got={ratio} want={expected}"
            );
        }
    }

    // frob:tests frob-core/src/callgraph.rs::arch_sim_ratio kind="unit"
    #[test]
    fn arch_sim_ratio_autojunk_matches_difflib() {
        // len(b) >= 200 triggers difflib's autojunk heuristic (chars
        // occurring in >1% of b are treated as junk and excluded from the
        // primary match search) -- this repo's real function bodies can
        // exceed 200 normalized-token characters, so this path is reachable
        // in practice, not just a synthetic corner case.
        let a: String = "x".repeat(250);
        let b: String = "x".repeat(200) + &"y".repeat(50);
        let av: Vec<char> = a.chars().collect();
        let bv: Vec<char> = b.chars().collect();
        let ratio = arch_sim_ratio(&av, &bv);
        assert!(
            (ratio - 0.8).abs() < 1e-12,
            "got={ratio} want=0.8 (difflib golden)"
        );
    }

    // frob:tests frob-core/src/callgraph.rs::near_duplicate_indices kind="unit"
    #[test]
    fn near_duplicate_indices_matches_python_reference_cluster() {
        // Same fixture, threshold, and expected cluster as
        // `_near_duplicate_cluster`'s Python reference computation (T-0953
        // parity harness) -- bodies 0/1 are near-duplicates of each other,
        // 2/3 are not near-duplicates of anything in the group.
        let bodies: Vec<String> = vec![
            "_S_ return _v0 . x".to_string(),
            "_S_ return _v0 . y".to_string(),
            "_S_ return _v1 + _v2".to_string(),
            "totally different body here with more tokens padding".to_string(),
        ];
        let idx = near_duplicate_indices(bodies, 0.9);
        assert_eq!(idx, vec![0usize, 1usize]);
    }
}

// frob:ticket T-1221
// frob:ticket T-1222
#[pymodule]
fn frob_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
    m.add_function(wrap_pyfunction!(r3_canonical_hash, m)?)?;
    m.add_function(wrap_pyfunction!(winnow_fingerprints, m)?)?;
    m.add_function(wrap_pyfunction!(candidate_pairs, m)?)?;
    m.add_function(wrap_pyfunction!(tree_edit_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(apted_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(anti_unify, m)?)?;
    m.add_function(wrap_pyfunction!(wl_hash, m)?)?;
    m.add_function(wrap_pyfunction!(run_exact_regions, m)?)?;
    m.add_function(wrap_pyfunction!(resolve_call_edges, m)?)?;
    m.add_function(wrap_pyfunction!(called_names, m)?)?;
    m.add_function(wrap_pyfunction!(ordered_called_names, m)?)?;
    m.add_function(wrap_pyfunction!(referenced_names, m)?)?;
    m.add_function(wrap_pyfunction!(unresolved_exempt_names, m)?)?;
    m.add_function(wrap_pyfunction!(near_duplicate_indices, m)?)?;
    // T-1220: tree-extraction kernels -- see docs/modules/lang.md#extraction-api.
    m.add_function(wrap_pyfunction!(extract_tree_python, m)?)?;
    m.add_function(wrap_pyfunction!(extract_tree_rust, m)?)?;
    m.add_function(wrap_pyfunction!(extract_tree_cpp, m)?)?;
    m.add_function(wrap_pyfunction!(extract_tree_typescript, m)?)?;
    // T-1221: capability-scan resolver -- see docs/modules/vet.md#public-api.
    m.add_function(wrap_pyfunction!(scan_python_capabilities, m)?)?;
    // T-1222: arch python metrics single-pass walk -- see
    // docs/modules/arch.md#normalized-code-model.
    m.add_function(wrap_pyfunction!(py_function_metrics, m)?)?;
    Ok(())
}

