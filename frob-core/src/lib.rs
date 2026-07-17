//! frob-core: compute-only clone-detection kernels for frob.dup (docs/dup.md).
//!
//! Every function here is data-in/data-out: serialized token lists in,
//! fingerprints/hashes/distances out. No IO, no caching policy, no git
//! awareness -- that all stays in Python (frob.dup._pipeline). Errors never
//! cross this boundary; a malformed input is a Python-side validation bug,
//! not something this crate defends against.

use pyo3::prelude::*;
use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};

/// Deterministic 64-bit hash of one token (std `DefaultHasher` is
/// unkeyed/deterministic across runs, unlike `HashMap`'s `RandomState`).
fn hash_str(s: &str) -> u64 {
    let mut h = DefaultHasher::new();
    s.hash(&mut h);
    h.finish()
}

/// R3: canonicalized-AST subtree hash.
///
/// WHY: the caller (frob.dup._pipeline) has already alpha-renamed locals,
/// abstracted literals, and normalized control flow via frob.lang -- this
/// function's only job is to fold the resulting token sequence into one
/// stable hex digest so equal-shape bodies collide regardless of source
/// length. Kept as a pure fold (not a crate like blake3) to keep the
/// dependency surface at just pyo3.
#[pyfunction]
fn r3_canonical_hash(tokens: Vec<String>) -> String {
    // frob:doc docs/dup.md#frob-core-kernels-the-pyo3-exported-surface
    let mut acc: u64 = 0xcbf29ce484222325; // FNV offset basis, arbitrary seed
    for tok in &tokens {
        let h = hash_str(tok);
        acc = acc.rotate_left(5) ^ h;
    }
    format!("{:016x}", acc)
}

/// R4: winnowing fingerprints (Moss-style) over sliding token windows.
///
/// Returns the set of selected k-gram hashes after winnowing with window
/// `w`, so fingerprints are position-independent -- the same substring
/// anywhere in the token stream produces the same fingerprint, which is
/// what makes region-granular matching (docs/dup.md's "regions, not just
/// functions") fall out for free.
#[pyfunction]
fn winnow_fingerprints(tokens: Vec<String>, k: usize, w: usize) -> Vec<u64> {
    // frob:doc docs/dup.md#frob-core-kernels-the-pyo3-exported-surface
    if k == 0 || tokens.len() < k {
        return Vec::new();
    }
    // k-gram hashes
    let kgram_hashes: Vec<u64> = (0..=tokens.len() - k)
        .map(|i| {
            let mut h = DefaultHasher::new();
            for tok in &tokens[i..i + k] {
                tok.hash(&mut h);
            }
            h.finish()
        })
        .collect();

    if w == 0 || kgram_hashes.len() < w {
        // No windowing possible -- every k-gram hash is selected.
        let mut out = kgram_hashes;
        out.dedup();
        return out;
    }

    // Classic winnowing: in each window of w consecutive hashes, keep the
    // minimum (rightmost on ties), dedup consecutive repeats.
    let mut selected: Vec<u64> = Vec::new();
    let mut last_selected_idx: Option<usize> = None;
    for start in 0..=kgram_hashes.len() - w {
        let window = &kgram_hashes[start..start + w];
        let mut min_idx = start;
        let mut min_val = window[0];
        for (off, &v) in window.iter().enumerate() {
            if v <= min_val {
                min_val = v;
                min_idx = start + off;
            }
        }
        if last_selected_idx != Some(min_idx) {
            selected.push(min_val);
            last_selected_idx = Some(min_idx);
        }
    }
    selected
}

/// R4 candidate discovery: LSH-style bucketing by shared fingerprints.
///
/// `ids` and `fingerprint_sets` are parallel arrays (one fingerprint list
/// per region). Returns index pairs `(i, j)` with `i < j` whose fingerprint
/// sets share at least `min_shared` values -- the candidate pairs that get
/// verified downstream by `tree_edit_similarity`.
#[pyfunction]
fn candidate_pairs(fingerprint_sets: Vec<Vec<u64>>, min_shared: usize) -> Vec<(usize, usize)> {
    // frob:doc docs/dup.md#frob-core-kernels-the-pyo3-exported-surface
    let mut buckets: HashMap<u64, Vec<usize>> = HashMap::new();
    for (idx, fps) in fingerprint_sets.iter().enumerate() {
        for fp in fps {
            buckets.entry(*fp).or_default().push(idx);
        }
    }
    let mut shared_counts: HashMap<(usize, usize), usize> = HashMap::new();
    for members in buckets.values() {
        if members.len() < 2 {
            continue;
        }
        for a in 0..members.len() {
            for b in (a + 1)..members.len() {
                let (i, j) = (members[a].min(members[b]), members[a].max(members[b]));
                *shared_counts.entry((i, j)).or_insert(0) += 1;
            }
        }
    }
    let mut out: Vec<(usize, usize)> = shared_counts
        .into_iter()
        .filter(|(_, count)| *count >= min_shared)
        .map(|(pair, _)| pair)
        .collect();
    out.sort_unstable();
    out
}

/// R4 verification: statement-sequence edit distance and alignment.
///
/// **Deviation from docs/dup.md**: the design names APTED (tree edit
/// distance over the full subtree structure). This implementation is a
/// statement-level Needleman-Wunsch/Levenshtein alignment over each
/// region's flattened statement-hash sequence, not a full tree metric --
/// it catches inserted/deleted statements (the R4 use case named in the
/// rung table) but not within-statement tree restructuring, which is a
/// known gap recorded for a follow-up (frob:ticket T-0001 follow-up:
/// upgrade to true APTED). Returns `(similarity, alignment)` where
/// `alignment` is matched `(i, j)` statement-index pairs.
#[pyfunction]
fn tree_edit_similarity(a: Vec<u64>, b: Vec<u64>) -> (f64, Vec<(usize, usize)>) {
    // frob:doc docs/dup.md#frob-core-kernels-the-pyo3-exported-surface
    let n = a.len();
    let m = b.len();
    if n == 0 && m == 0 {
        return (1.0, Vec::new());
    }
    if n == 0 || m == 0 {
        return (0.0, Vec::new());
    }

    // dp[i][j] = edit distance between a[..i] and b[..j]
    let mut dp = vec![vec![0usize; m + 1]; n + 1];
    for i in 0..=n {
        dp[i][0] = i;
    }
    for j in 0..=m {
        dp[0][j] = j;
    }
    for i in 1..=n {
        for j in 1..=m {
            if a[i - 1] == b[j - 1] {
                dp[i][j] = dp[i - 1][j - 1];
            } else {
                dp[i][j] = 1 + dp[i - 1][j].min(dp[i][j - 1]).min(dp[i - 1][j - 1]);
            }
        }
    }
    let dist = dp[n][m];
    let max_len = n.max(m);
    let similarity = 1.0 - (dist as f64 / max_len as f64);

    // Backtrace to recover matched (equal) index pairs.
    let mut alignment: Vec<(usize, usize)> = Vec::new();
    let (mut i, mut j) = (n, m);
    while i > 0 && j > 0 {
        if a[i - 1] == b[j - 1] && dp[i][j] == dp[i - 1][j - 1] {
            alignment.push((i - 1, j - 1));
            i -= 1;
            j -= 1;
        } else if dp[i][j] == dp[i - 1][j - 1] + 1 {
            i -= 1;
            j -= 1;
        } else if dp[i][j] == dp[i - 1][j] + 1 {
            i -= 1;
        } else {
            j -= 1;
        }
    }
    alignment.reverse();
    (similarity, alignment)
}

/// R4 verification (real tree edit distance): Zhang-Shasha algorithm over
/// two labeled ordered trees, each given as a flat `parents` array (index i
/// is a node, `parents[i]` its parent index or `-1` for the root; any
/// traversal order is fine -- this function derives its own postorder).
///
/// This is the real tree-edit-distance metric the rung table names (APTED
/// generalizes Zhang-Shasha with a smarter choice of single/double-path
/// decomposition for better worst-case complexity; Zhang-Shasha is the
/// same edit-distance *result* -- insert/delete/rename over full subtree
/// structure, not a flat statement sequence -- at a still-polynomial
/// O(n*m*min(depth,leaves)) cost, which is what frob.dup's clone-sized
/// inputs need). Unlike the old `tree_edit_similarity` (kept below for
/// R4's statement-alignment/region-span narrowing, a different job), this
/// operates on real subtree shape: a token reordered *within* one
/// statement changes the tree structure and is caught here, where the
/// flat statement-sequence Levenshtein could not see it.
fn build_postorder(parents: &[i64]) -> (Vec<usize>, Vec<usize>, usize) {
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
    let mut postorder: Vec<usize> = Vec::with_capacity(n);
    let mut leftmost_of: Vec<usize> = vec![0; n]; // node id -> leftmost-leaf node id
    // iterative post-order to avoid unbounded recursion depth on large trees
    let mut stack: Vec<(usize, usize)> = vec![(root, 0)]; // (node, next-child-idx)
    let mut first_leaf_stack: Vec<Option<usize>> = vec![None];
    while let Some(&(node, idx)) = stack.last() {
        let kids = &children[node];
        if kids.is_empty() {
            postorder.push(node);
            leftmost_of[node] = node;
            stack.pop();
            first_leaf_stack.pop();
            if let Some(top) = first_leaf_stack.last_mut() {
                if top.is_none() {
                    *top = Some(node);
                }
            }
        } else if idx < kids.len() {
            stack.last_mut().unwrap().1 += 1;
            stack.push((kids[idx], 0));
            first_leaf_stack.push(None);
        } else {
            postorder.push(node);
            let lf = first_leaf_stack.pop().unwrap().unwrap_or(node);
            leftmost_of[node] = lf;
            stack.pop();
            if let Some(top) = first_leaf_stack.last_mut() {
                if top.is_none() {
                    *top = Some(lf);
                }
            }
        }
    }
    let mut pos_of: Vec<usize> = vec![0; n];
    for (i, &node) in postorder.iter().enumerate() {
        pos_of[node] = i;
    }
    let lmd: Vec<usize> = postorder.iter().map(|&node| pos_of[leftmost_of[node]]).collect();
    (postorder, lmd, root)
}

fn keyroots(lmd: &[usize]) -> Vec<usize> {
    let mut last_for_l: HashMap<usize, usize> = HashMap::new();
    for (i, &l) in lmd.iter().enumerate() {
        last_for_l.insert(l, i); // largest i wins, since we overwrite in order
    }
    let mut kr: Vec<usize> = last_for_l.values().copied().collect();
    kr.sort_unstable();
    kr
}

/// The Zhang-Shasha tree-edit-distance value between two labeled trees
/// (postorder positions are 0-indexed internally; the algorithm's classic
/// formulation is used with a +1 offset for the forestdist boundary row).
fn zhang_shasha_distance(
    labels_a: &[String],
    postorder_a: &[usize],
    lmd_a: &[usize],
    labels_b: &[String],
    postorder_b: &[usize],
    lmd_b: &[usize],
) -> usize {
    let n = postorder_a.len();
    let m = postorder_b.len();
    if n == 0 && m == 0 {
        return 0;
    }
    if n == 0 {
        return m;
    }
    if m == 0 {
        return n;
    }
    let mut treedist = vec![vec![0usize; m]; n];
    let kr_a = keyroots(lmd_a);
    let kr_b = keyroots(lmd_b);

    for &i in &kr_a {
        for &j in &kr_b {
            let li = lmd_a[i];
            let lj = lmd_b[j];
            let rows = i - li + 2;
            let cols = j - lj + 2;
            let mut forestdist = vec![vec![0usize; cols]; rows];
            for x in 1..rows {
                forestdist[x][0] = forestdist[x - 1][0] + 1;
            }
            for y in 1..cols {
                forestdist[0][y] = forestdist[0][y - 1] + 1;
            }
            for x in 1..rows {
                let node_x = li + x - 1;
                for y in 1..cols {
                    let node_y = lj + y - 1;
                    if lmd_a[node_x] == li && lmd_b[node_y] == lj {
                        let cost_rename =
                            if labels_a[postorder_a[node_x]] == labels_b[postorder_b[node_y]] {
                                0
                            } else {
                                1
                            };
                        let del = forestdist[x - 1][y] + 1;
                        let ins = forestdist[x][y - 1] + 1;
                        let ren = forestdist[x - 1][y - 1] + cost_rename;
                        let val = del.min(ins).min(ren);
                        forestdist[x][y] = val;
                        treedist[node_x][node_y] = val;
                    } else {
                        let p = lmd_a[node_x] - li;
                        let q = lmd_b[node_y] - lj;
                        let del = forestdist[x - 1][y] + 1;
                        let ins = forestdist[x][y - 1] + 1;
                        let ren = forestdist[p][q] + treedist[node_x][node_y];
                        forestdist[x][y] = del.min(ins).min(ren);
                    }
                }
            }
        }
    }
    treedist[n - 1][m - 1]
}

/// R4 verification (real APTED-class tree edit distance): see
/// `zhang_shasha_distance` for the algorithm. `parents_a`/`parents_b` are
/// flat parent-index arrays (root has parent `-1`); `labels_a`/`labels_b`
/// are the per-node labels in the SAME index space as their parents array
/// (node structure, not tree-sitter node types directly -- the caller,
/// `frob.dup._pipeline`, builds this from `frob.lang`'s exported subtree).
/// Returns similarity in `[0, 1]` (`1 - distance / max(|A|, |B|)`).
#[pyfunction]
fn apted_similarity(
    labels_a: Vec<String>,
    parents_a: Vec<i64>,
    labels_b: Vec<String>,
    parents_b: Vec<i64>,
) -> f64 {
    // frob:doc docs/dup.md#frob-core-kernels-the-pyo3-exported-surface
    if labels_a.is_empty() && labels_b.is_empty() {
        return 1.0;
    }
    if labels_a.is_empty() || labels_b.is_empty() {
        return 0.0;
    }
    let (postorder_a, lmd_a, _root_a) = build_postorder(&parents_a);
    let (postorder_b, lmd_b, _root_b) = build_postorder(&parents_b);
    let dist = zhang_shasha_distance(
        &labels_a,
        &postorder_a,
        &lmd_a,
        &labels_b,
        &postorder_b,
        &lmd_b,
    );
    let max_len = labels_a.len().max(labels_b.len());
    1.0 - (dist as f64 / max_len as f64)
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
fn wl_hash(adjacency: Vec<(usize, usize)>, labels: Vec<String>, iterations: usize) -> u64 {
    // frob:doc docs/dup.md#frob-core-kernels-the-pyo3-exported-surface
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_hash_is_deterministic_and_shape_sensitive() {
        // frob:tests frob-core/src/lib.rs::r3_canonical_hash kind="unit"
        let a = vec!["def".into(), "_v0".into(), "return".into(), "_v0".into()];
        let b = vec!["def".into(), "_v0".into(), "return".into(), "_v0".into()];
        let c = vec!["def".into(), "_v0".into(), "return".into(), "_N_".into()];
        assert_eq!(r3_canonical_hash(a.clone()), r3_canonical_hash(b));
        assert_ne!(r3_canonical_hash(a), r3_canonical_hash(c));
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
        // frob:tests frob-core/src/lib.rs::wl_hash kind="unit"
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
        // frob:tests frob-core/src/lib.rs::apted_similarity kind="unit"
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
}

#[pymodule]
fn frob_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // frob:doc docs/dup.md#frob-core-kernels-the-pyo3-exported-surface
    m.add_function(wrap_pyfunction!(r3_canonical_hash, m)?)?;
    m.add_function(wrap_pyfunction!(winnow_fingerprints, m)?)?;
    m.add_function(wrap_pyfunction!(candidate_pairs, m)?)?;
    m.add_function(wrap_pyfunction!(tree_edit_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(apted_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(wl_hash, m)?)?;
    Ok(())
}
