//! R5: anti-unification and Weisfeiler-Lehman hashing rung, split out of
//! lib.rs by T-2846.
//! frob:ticket T-2846

use crate::hash_str;
use pyo3::prelude::*;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

/// Children-index lists for a parent-index array, in source (array) order --
/// same construction `build_postorder` uses, factored out so `anti_unify`
/// can walk lockstep without paying for postorder/keyroots bookkeeping it
/// does not need.
fn children_lists(parents: &[i64]) -> (Vec<Vec<usize>>, usize) {
    let n = parents.len();
    let mut children: Vec<Vec<usize>> = vec![Vec::new(); n];
    let mut root = 0usize;
    for (i, &p) in parents.iter().enumerate() {
        if p < 0 {
            root = i;
        } else {
            children[p as usize].push(i);
        }
    }
    (children, root)
}

/// Failure modes for `anti_unify_core`: only the hole-ceiling sanity check
/// today (item 17/T-0194's ADOPT clause) -- a template that is mostly holes
/// carries no real generalization value, so the caller should fall back to
/// treating the pair as a plain (non-generalized) clone match.
// frob:doc docs/modules/dup.md#anti-unification-plotkin-lgg
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum AntiUnifyErr {
    /// Generalized template is >50% `$hole_N` placeholders by node count.
    HoleCeilingExceeded,
}

/// Plotkin lgg output: the generalized node array (shared labels plus
/// `$hole_N` placeholders at each divergence) and, per hole, the pair of
/// concrete subtree roots it generalizes -- one index into `parents_a`'s
/// node space, one into `parents_b`'s.
// frob:doc docs/modules/dup.md#anti-unification-plotkin-lgg
#[derive(Debug)]
pub(crate) struct Template {
    pub(crate) labels: Vec<String>,
    pub(crate) parents: Vec<i64>,
    /// `(hole_id, node_index_in_a)`, one entry per hole, in hole order.
    pub(crate) bindings_a: Vec<(usize, usize)>,
    /// `(hole_id, node_index_in_b)`, one entry per hole, in hole order.
    pub(crate) bindings_b: Vec<(usize, usize)>,
}

/// Recursive lockstep walk: at `(a, b)`, emit a shared node and recurse into
/// children pairwise when labels AND arity agree; otherwise emit a fresh
/// `$hole_N` at this position, bind it to `(a, b)`, and do not recurse --
/// everything under a hole is exactly what differs per-instance, so it
/// belongs to the binding, not the template.
// frob:invariant terminates reason="each recursive call descends strictly into a child of a and b \
// in the input parse trees, which are finite; recursion stops at leaves (empty child lists) or on \
// any label/arity mismatch" measure="min(remaining-depth-in-a, remaining-depth-in-b) from the \
// current (a, b) pair to a leaf"
#[allow(clippy::too_many_arguments)]
fn anti_unify_walk(
    a: usize,
    b: usize,
    parent_out: i64,
    children_a: &[Vec<usize>],
    children_b: &[Vec<usize>],
    labels_a: &[String],
    labels_b: &[String],
    out_labels: &mut Vec<String>,
    out_parents: &mut Vec<i64>,
    bindings_a: &mut Vec<(usize, usize)>,
    bindings_b: &mut Vec<(usize, usize)>,
    hole_counter: &mut usize,
) {
    let kids_a = &children_a[a];
    let kids_b = &children_b[b];
    if labels_a[a] == labels_b[b] && kids_a.len() == kids_b.len() {
        let idx = out_labels.len() as i64;
        out_labels.push(labels_a[a].clone());
        out_parents.push(parent_out);
        for k in 0..kids_a.len() {
            anti_unify_walk(
                kids_a[k],
                kids_b[k],
                idx,
                children_a,
                children_b,
                labels_a,
                labels_b,
                out_labels,
                out_parents,
                bindings_a,
                bindings_b,
                hole_counter,
            );
        }
    } else {
        let hole_id = *hole_counter;
        *hole_counter += 1;
        out_labels.push(format!("$hole_{hole_id}"));
        out_parents.push(parent_out);
        bindings_a.push((hole_id, a));
        bindings_b.push((hole_id, b));
    }
}

/// Anti-unification core (Plotkin 1970 least-general-generalization): the
/// pure algorithm, independent of the PyO3 boundary, so cargo tests can
/// assert on `Err` directly (docs/modules/dup-sota-survey.md section 4).
/// Both-empty inputs generalize to an empty template with zero holes;
/// exactly-one-empty is a maximal-divergence case (nothing shared) and
/// always exceeds the hole ceiling below.
// frob:doc docs/modules/dup.md#anti-unification-plotkin-lgg
pub(crate) fn anti_unify_core(
    labels_a: &[String],
    parents_a: &[i64],
    labels_b: &[String],
    parents_b: &[i64],
) -> Result<Template, AntiUnifyErr> {
    if labels_a.is_empty() && labels_b.is_empty() {
        return Ok(Template {
            labels: Vec::new(),
            parents: Vec::new(),
            bindings_a: Vec::new(),
            bindings_b: Vec::new(),
        });
    }
    if labels_a.is_empty() || labels_b.is_empty() {
        return Err(AntiUnifyErr::HoleCeilingExceeded);
    }

    let (children_a, root_a) = children_lists(parents_a);
    let (children_b, root_b) = children_lists(parents_b);

    let mut out_labels = Vec::new();
    let mut out_parents = Vec::new();
    let mut bindings_a = Vec::new();
    let mut bindings_b = Vec::new();
    let mut hole_counter = 0usize;

    anti_unify_walk(
        root_a,
        root_b,
        -1,
        &children_a,
        &children_b,
        labels_a,
        labels_b,
        &mut out_labels,
        &mut out_parents,
        &mut bindings_a,
        &mut bindings_b,
        &mut hole_counter,
    );

    let hole_count = out_labels
        .iter()
        .filter(|l| l.starts_with("$hole_"))
        .count();
    // HOLE-CEILING sanity: >50% holes means too little shared structure to
    // be a meaningful generalization -- fall back to a plain clone pair.
    if hole_count * 2 > out_labels.len() {
        return Err(AntiUnifyErr::HoleCeilingExceeded);
    }

    Ok(Template {
        labels: out_labels,
        parents: out_parents,
        bindings_a,
        bindings_b,
    })
}

/// Plotkin lgg over the `(labels, parents)` node-array representation
/// `apted_similarity` already consumes (docs/modules/dup-sota-survey.md
/// section 4, T-0194). Lockstep top-down walk: where labels and arity
/// agree, keep the shared node and recurse; on divergence, emit a fresh
/// `$hole_N` and bind it to the two diverging subtrees without recursing
/// into them. Returns `(ok, template_labels, template_parents, bindings_a,
/// bindings_b)` rather than raising -- this crate's data-in/data-out
/// contract (see module doc) never lets a Rust exception cross the PyO3
/// boundary, so a hole-ceiling failure (`ok == false`) is a plain sentinel
/// value, not a Python exception; all four arrays are empty in that case.
#[pyfunction]
pub fn anti_unify(
    labels_a: Vec<String>,
    parents_a: Vec<i64>,
    labels_b: Vec<String>,
    parents_b: Vec<i64>,
) -> (
    bool,
    Vec<String>,
    Vec<i64>,
    Vec<(usize, usize)>,
    Vec<(usize, usize)>,
) {
    // frob:doc docs/modules/dup.md#anti-unification-plotkin-lgg
    match anti_unify_core(&labels_a, &parents_a, &labels_b, &parents_b) {
        Ok(t) => (true, t.labels, t.parents, t.bindings_a, t.bindings_b),
        Err(AntiUnifyErr::HoleCeilingExceeded) => {
            (false, Vec::new(), Vec::new(), Vec::new(), Vec::new())
        }
    }
}

/// R5: Weisfeiler-Lehman graph-kernel hash over a def-use/control adjacency.
///
/// `adjacency` is an edge list `(u, v)` over node indices `0..labels.len()`
/// (undirected -- the caller symmetrizes if it wants directed semantics);
/// `labels[i]` is node `i`'s initial color (identifier role, e.g. "def" vs
/// "use", the caller's choice). Standard 1-WL refinement: each iteration,
/// every node's new label is the hash of its own label plus the *sorted*
/// multiset of its neighbors' labels (sorting makes it isomorphism-stable --
/// two graphs with relabeled-but-isomorphic structure hash identically).
/// After `iterations` rounds the per-node labels are folded (order-
/// independent, via XOR) into one graph hash, so reordered-but-equivalent
/// dataflow graphs collide regardless of node numbering.
#[pyfunction]
pub fn wl_hash(adjacency: Vec<(usize, usize)>, labels: Vec<String>, iterations: usize) -> u64 {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
    let n = labels.len();
    if n == 0 {
        return 0;
    }
    let mut neighbors: Vec<Vec<usize>> = vec![Vec::new(); n];
    for (u, v) in &adjacency {
        if *u < n && *v < n {
            neighbors[*u].push(*v);
            neighbors[*v].push(*u);
        }
    }

    let mut colors: Vec<u64> = labels.iter().map(|l| hash_str(l)).collect();
    for _ in 0..iterations {
        let mut next_colors: Vec<u64> = Vec::with_capacity(n);
        for i in 0..n {
            let mut neighbor_colors: Vec<u64> = neighbors[i].iter().map(|&j| colors[j]).collect();
            neighbor_colors.sort_unstable();
            let mut h = DefaultHasher::new();
            colors[i].hash(&mut h);
            neighbor_colors.hash(&mut h);
            next_colors.push(h.finish());
        }
        colors = next_colors;
    }

    // Order-independent fold: the graph hash must not depend on node
    // numbering, only on the (now-refined) multiset of node colors.
    let mut sorted_colors = colors;
    sorted_colors.sort_unstable();
    let mut acc: u64 = 0x9e3779b97f4a7c15; // golden-ratio seed, arbitrary
    for c in sorted_colors {
        acc = acc.wrapping_add(c.wrapping_mul(0xff51afd7ed558ccd));
        acc ^= acc >> 33;
    }
    acc
}

