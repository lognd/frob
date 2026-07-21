//! frob-core: compute-only clone-detection kernels for frob.dup (docs/modules/dup.md).
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
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
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
/// what makes region-granular matching (docs/modules/dup.md's "regions, not just
/// functions") fall out for free.
#[pyfunction]
fn winnow_fingerprints(tokens: Vec<String>, k: usize, w: usize) -> Vec<u64> {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
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
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
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
                if members[a] == members[b] {
                    // Same region indexed twice in one bucket (duplicate
                    // fingerprint values within a single region's set) must
                    // never emit a self-pair (i, i) -- a region always
                    // "shares" with itself and that's not a candidate.
                    continue;
                }
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
/// **Deviation from docs/modules/dup.md**: the design names APTED (tree edit
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
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
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
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
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
#[derive(Debug, PartialEq, Eq)]
enum AntiUnifyErr {
    /// Generalized template is >50% `$hole_N` placeholders by node count.
    HoleCeilingExceeded,
}

/// Plotkin lgg output: the generalized node array (shared labels plus
/// `$hole_N` placeholders at each divergence) and, per hole, the pair of
/// concrete subtree roots it generalizes -- one index into `parents_a`'s
/// node space, one into `parents_b`'s.
#[derive(Debug)]
struct Template {
    labels: Vec<String>,
    parents: Vec<i64>,
    /// `(hole_id, node_index_in_a)`, one entry per hole, in hole order.
    bindings_a: Vec<(usize, usize)>,
    /// `(hole_id, node_index_in_b)`, one entry per hole, in hole order.
    bindings_b: Vec<(usize, usize)>,
}

/// Recursive lockstep walk: at `(a, b)`, emit a shared node and recurse into
/// children pairwise when labels AND arity agree; otherwise emit a fresh
/// `$hole_N` at this position, bind it to `(a, b)`, and do not recurse --
/// everything under a hole is exactly what differs per-instance, so it
/// belongs to the binding, not the template.
// frob:invariant terminates reason="each recursive call descends strictly into a child of a and b in the input parse trees, which are finite; recursion stops at leaves (empty child lists) or on any label/arity mismatch" measure="min(remaining-depth-in-a, remaining-depth-in-b) from the current (a, b) pair to a leaf"
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
fn anti_unify_core(
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
fn anti_unify(
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
fn wl_hash(adjacency: Vec<(usize, usize)>, labels: Vec<String>, iterations: usize) -> u64 {
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

/// Token-id/document-index bookkeeping for `exact_regions`: `global` is the
/// concatenation of every document's token ids with a unique per-document
/// sentinel appended after each one (so no suffix can match across a
/// document boundary); `doc_of[i]`/`offset_of[i]` recover which document and
/// local token offset global position `i` came from (`doc_of[i] == None` at
/// a sentinel position).
fn flatten_documents(documents: &[Vec<String>]) -> (Vec<i64>, Vec<Option<usize>>, Vec<usize>) {
    let mut token_ids: HashMap<&str, i64> = HashMap::new();
    let mut next_id: i64 = 0;
    let mut global: Vec<i64> = Vec::new();
    let mut doc_of: Vec<Option<usize>> = Vec::new();
    let mut offset_of: Vec<usize> = Vec::new();
    for (doc_idx, doc) in documents.iter().enumerate() {
        for (tok_idx, tok) in doc.iter().enumerate() {
            let id = *token_ids.entry(tok.as_str()).or_insert_with(|| {
                let v = next_id;
                next_id += 1;
                v
            });
            global.push(id);
            doc_of.push(Some(doc_idx));
            offset_of.push(tok_idx);
        }
        // Unique negative sentinel per document -- real token ids are >= 0,
        // so a sentinel can never equal (or be lexicographically confused
        // with) a real token id, and two different documents' sentinels
        // never collide with each other either.
        global.push(-1 - doc_idx as i64);
        doc_of.push(None);
        offset_of.push(0);
    }
    (global, doc_of, offset_of)
}

/// Suffix array of `s` via the classic O(n log^2 n) rank-doubling
/// algorithm (Manber-Myers). `s` may contain any `i64` values (not just
/// `0..alphabet_size`) -- ranks are recomputed from the current ordering
/// each round rather than assuming a bounded alphabet, so the negative
/// sentinel ids from `flatten_documents` work unmodified.
fn build_suffix_array(s: &[i64]) -> Vec<usize> {
    let n = s.len();
    if n == 0 {
        return Vec::new();
    }
    let mut sa: Vec<usize> = (0..n).collect();
    let mut rank: Vec<i64> = s.to_vec();
    let mut tmp: Vec<i64> = vec![0; n];
    let key = |i: usize, rank: &[i64], k: usize| -> (i64, i64) {
        let hi = rank[i];
        let lo = if i + k < n { rank[i + k] } else { i64::MIN };
        (hi, lo)
    };
    let mut k = 1usize;
    loop {
        sa.sort_unstable_by_key(|&i| key(i, &rank, k));
        tmp[sa[0]] = 0;
        for i in 1..n {
            let prev_key = key(sa[i - 1], &rank, k);
            let cur_key = key(sa[i], &rank, k);
            tmp[sa[i]] = tmp[sa[i - 1]] + if cur_key > prev_key { 1 } else { 0 };
        }
        rank.copy_from_slice(&tmp);
        if rank[sa[n - 1]] as usize == n - 1 || k >= n {
            break;
        }
        k <<= 1;
    }
    sa
}

/// Kasai's O(n) LCP-array construction: `lcp[i]` is the length of the
/// longest common prefix between the suffixes at `sa[i]` and `sa[i-1]`
/// (`lcp[0]` is unused/`0`, there is no predecessor).
fn kasai_lcp(s: &[i64], sa: &[usize]) -> Vec<usize> {
    let n = s.len();
    if n == 0 {
        return Vec::new();
    }
    let mut rank = vec![0usize; n];
    for (i, &p) in sa.iter().enumerate() {
        rank[p] = i;
    }
    let mut lcp = vec![0usize; n];
    let mut h = 0usize;
    for i in 0..n {
        if rank[i] > 0 {
            let j = sa[rank[i] - 1];
            while i + h < n && j + h < n && s[i + h] == s[j + h] {
                h += 1;
            }
            lcp[rank[i]] = h;
            if h > 0 {
                h -= 1;
            }
        } else {
            h = 0;
        }
    }
    lcp
}

/// Collapse raw adjacent-SA-pair matches into maximal repeated regions.
///
/// Two matches `(da, oa, db, ob, l)` lie on the same "diagonal" of the
/// `(doc_a offset, doc_b offset)` alignment grid when `oa - ob` is constant
/// -- exactly the condition for them to be different windows onto the same
/// underlying repeat. Grouping by `(da, db, diagonal)` and merging
/// overlapping/touching `[oa, oa+l)` intervals on that diagonal recovers
/// the single maximal region a generalized suffix automaton would report
/// directly, instead of one entry per SA-adjacent sub-window.
fn merge_diagonals(
    raw: Vec<(usize, usize, usize, usize, usize)>,
) -> Vec<(usize, usize, usize, usize, usize)> {
    let canon: Vec<(usize, usize, usize, usize, usize)> = raw
        .into_iter()
        .map(|(da, oa, db, ob, l)| {
            if (da, oa) <= (db, ob) {
                (da, oa, db, ob, l)
            } else {
                (db, ob, da, oa, l)
            }
        })
        .collect();

    let mut groups: HashMap<(usize, usize, i64), Vec<(usize, usize)>> = HashMap::new();
    for (da, oa, db, ob, l) in canon {
        let diag = oa as i64 - ob as i64;
        groups.entry((da, db, diag)).or_default().push((oa, l));
    }

    let mut out: Vec<(usize, usize, usize, usize, usize)> = Vec::new();
    for ((da, db, diag), mut intervals) in groups {
        intervals.sort_unstable();
        let (mut cur_start, first_len) = intervals[0];
        let mut cur_end = cur_start + first_len;
        for &(s, l) in intervals.iter().skip(1) {
            let e = s + l;
            if s <= cur_end {
                cur_end = cur_end.max(e);
            } else {
                out.push((
                    da,
                    cur_start,
                    db,
                    (cur_start as i64 - diag) as usize,
                    cur_end - cur_start,
                ));
                cur_start = s;
                cur_end = e;
            }
        }
        out.push((
            da,
            cur_start,
            db,
            (cur_start as i64 - diag) as usize,
            cur_end - cur_start,
        ));
    }
    out.sort_unstable();
    out
}

/// R1.5: exact repeated-region discovery via a generalized suffix array
/// over the whole corpus's (already-normalized, caller's choice of
/// abstraction) token stream.
///
/// WHY: R1/R2 (`_r1_hash`/`_r2_hash` in `frob.dup._pipeline`) hash whole
/// symbol bodies, so a copy-pasted block sitting inside two otherwise-
/// different functions is invisible to them -- neither whole-body hash
/// collides. A suffix array + LCP pass over the concatenated corpus finds
/// *every* maximal exact-token-match region of length `>= min_len`,
/// anywhere in any document, in one O(n log^2 n) pass (suffix-automaton-
/// equivalent recall, suffix-array-simple implementation -- see
/// docs/modules/dup-sota-survey.md section 16 for why either data
/// structure is acceptable here). `documents[i]` is one symbol's token
/// stream (index `i` is the caller's document id, threaded back through
/// the returned tuples); `min_len` is a token-count floor below which a
/// match is not reported (mirrors R4's `min_shared`/`min_tokens` floors --
/// keeps trivial single-token "matches" out of the result).
///
/// Returns `(regions, truncated)`. `regions` is a list of `(doc_a,
/// start_a, doc_b, start_b, length)` tuples: doc `doc_a` at token offset
/// `start_a` and doc `doc_b` at token offset `start_b` share an exact
/// `length`-token run. `doc_a <= doc_b` (and `start_a <= start_b` when
/// `doc_a == doc_b`) by construction -- callers get each region pair once,
/// not twice.
///
/// `max_run_size` (T-0273, reviewer finding on T-0193: `emit_run_pairs` is
/// O(k^2) in one equal-token run's size `k` -- 2000 near-identical docs
/// sharing a block produced 1,999,000 pairs in a demonstrated worst case)
/// bounds `k` per run: a run larger than `max_run_size` only pairs its
/// first `max_run_size` occurrences with each other, capping the per-run
/// cost at O(max_run_size^2) regardless of how many more times the block
/// repeats. `truncated` is `true` iff at least one run was capped -- an
/// honest signal, never a silent drop (the T-0193-recall-bug lesson):
/// callers are expected to surface it (e.g. a WARN log) rather than treat
/// the result as exhaustive when `truncated` is set.
#[pyfunction]
#[pyo3(signature = (documents, min_len, max_run_size=200))]
fn exact_regions(
    documents: Vec<Vec<String>>,
    min_len: usize,
    max_run_size: usize,
) -> (Vec<(usize, usize, usize, usize, usize)>, bool) {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
    if documents.is_empty() || min_len == 0 {
        return (Vec::new(), false);
    }
    let (global, doc_of, offset_of) = flatten_documents(&documents);
    if global.is_empty() {
        return (Vec::new(), false);
    }
    let sa = build_suffix_array(&global);
    let lcp = kasai_lcp(&global, &sa);

    let mut raw: Vec<(usize, usize, usize, usize, usize)> = Vec::new();
    let mut truncated = false;
    for (lo, hi) in lcp_runs(&lcp, min_len) {
        let run_truncated = emit_run_pairs(
            &sa,
            &doc_of,
            &offset_of,
            lo,
            hi,
            &lcp,
            min_len,
            max_run_size,
            &mut raw,
        );
        truncated = truncated || run_truncated;
    }
    (merge_diagonals(raw), truncated)
}

/// Maximal `[lo, hi]` (inclusive, both indices into `sa`/`lcp`) SA-index
/// ranges such that every consecutive pair inside the range has
/// `lcp >= min_len` -- i.e. every suffix in `sa[lo..=hi]` shares a common
/// prefix of at least `min_len` tokens with every other suffix in the same
/// range (LCP is a "staircase": for a sorted suffix array, the shared
/// prefix length between ANY two suffixes in a range is the MINIMUM
/// `lcp[k]` for `k` strictly between them, so bounding every adjacent gap
/// bounds every pairwise gap too). This is what lets `exact_regions` emit
/// every occurrence pair of a block repeated 3+ times, not just
/// SA-adjacent ones (the bug T-0193's reviewer caught: only comparing
/// `(sa[i-1], sa[i])` silently drops `(sa[i-2], sa[i])` and further-apart
/// pairs within the same run).
fn lcp_runs(lcp: &[usize], min_len: usize) -> Vec<(usize, usize)> {
    let n = lcp.len();
    let mut runs: Vec<(usize, usize)> = Vec::new();
    let mut run_start: Option<usize> = None;
    for i in 1..n {
        if lcp[i] >= min_len {
            if run_start.is_none() {
                run_start = Some(i - 1);
            }
        } else if let Some(start) = run_start.take() {
            runs.push((start, i - 1));
        }
    }
    if let Some(start) = run_start {
        runs.push((start, n - 1));
    }
    runs
}

/// Emit every occurrence pair `(sa[i], sa[j])`, `i < j`, within one
/// `lcp_runs` range `[lo, hi]` -- the shared length reported is the
/// minimum `lcp[k]` for `k` in `(lo, hi]`, which every pair in the range
/// is guaranteed to share (see `lcp_runs`'s doc comment). O(k^2) in the
/// run size `k`; runs are bounded by how many times one block repeats in
/// the corpus, not by corpus size, so this stays cheap in the common case
/// -- but a pathologically large equal-token run (many near-identical
/// generated/boilerplate symbols sharing a block) is NOT bounded by
/// anything else, so `max_run_size` (T-0273) caps `k` before the O(k^2)
/// double loop: only the run's first `max_run_size` occurrences (by SA
/// order) are paired with each other. Returns `true` iff the run exceeded
/// `max_run_size` and was capped, so the caller can propagate an honest
/// truncation signal instead of silently under-reporting.
fn emit_run_pairs(
    sa: &[usize],
    doc_of: &[Option<usize>],
    offset_of: &[usize],
    lo: usize,
    hi: usize,
    lcp: &[usize],
    min_len: usize,
    max_run_size: usize,
    out: &mut Vec<(usize, usize, usize, usize, usize)>,
) -> bool {
    let run_len = lcp[lo + 1..=hi].iter().copied().min().unwrap_or(min_len);
    let run_size = hi - lo + 1;
    let truncated = run_size > max_run_size.max(1);
    let capped_hi = if truncated {
        lo + max_run_size.max(1) - 1
    } else {
        hi
    };
    for i in lo..=capped_hi {
        let Some(da) = doc_of[sa[i]] else { continue };
        for j in (i + 1)..=capped_hi {
            let Some(db) = doc_of[sa[j]] else { continue };
            out.push((da, offset_of[sa[i]], db, offset_of[sa[j]], run_len));
        }
    }
    truncated
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
    fn candidate_pairs_never_emits_a_self_pair() {
        // frob:tests frob-core/src/lib.rs::candidate_pairs kind="unit"
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

    #[test]
    fn anti_unify_identical_trees_has_zero_holes() {
        // frob:tests frob-core/src/lib.rs::anti_unify_core kind="unit"
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
        // frob:tests frob-core/src/lib.rs::anti_unify_core kind="unit"
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
        // frob:tests frob-core/src/lib.rs::anti_unify_core kind="unit"
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
        // frob:tests frob-core/src/lib.rs::anti_unify_core kind="unit"
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
        // frob:tests frob-core/src/lib.rs::anti_unify_core kind="unit"
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
        // frob:tests frob-core/src/lib.rs::exact_regions kind="unit"
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
        let (regions, truncated) = exact_regions(vec![doc_a.clone(), doc_b.clone()], shared.len(), 10_000);
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
        let (regions, _) = exact_regions(vec![doc_a, doc_b], 10, 10_000);
        assert!(regions.is_empty());
    }

    #[test]
    fn exact_regions_no_match_across_wholly_different_documents() {
        let doc_a: Vec<String> = vec!["a".into(), "b".into(), "c".into(), "d".into()];
        let doc_b: Vec<String> = vec!["w".into(), "x".into(), "y".into(), "z".into()];
        let (regions, _) = exact_regions(vec![doc_a, doc_b], 2, 10_000);
        assert!(regions.is_empty());
    }

    #[test]
    fn exact_regions_does_not_match_across_document_boundary() {
        // The sentinel between documents must prevent a suffix straddling
        // the boundary from being reported as a match with anything.
        let doc_a: Vec<String> = vec!["p".into(), "q".into(), "r".into()];
        let doc_b: Vec<String> = vec!["r".into(), "s".into(), "t".into()];
        let (regions, _) = exact_regions(vec![doc_a, doc_b], 1, 10_000);
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
        let (regions, _) = exact_regions(vec![doc_a, doc_b], 3, 10_000);
        assert_eq!(regions.len(), 1);
        assert_eq!(regions[0].4, shared.len());
    }

    #[test]
    fn exact_regions_empty_input_is_empty_output() {
        let (regions, truncated) = exact_regions(Vec::new(), 1, 10_000);
        assert!(regions.is_empty());
        assert!(!truncated);
        let (regions, _) = exact_regions(vec![vec!["a".into()]], 0, 10_000);
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
        // frob:tests frob-core/src/lib.rs::exact_regions kind="unit"
        // Regression for the reviewer-caught bug (T-0193 round 2): only
        // SA-adjacent suffix pairs were compared, so a block repeated in
        // 3+ documents silently dropped non-adjacent occurrence pairs --
        // e.g. (doc0, doc2) when doc1's matching suffix sorted between
        // them in the suffix array.
        let block: Vec<String> = ["a", "b", "c", "d"].iter().map(|s| s.to_string()).collect();
        let docs = vec![block.clone(), block.clone(), block.clone()];
        let (regions, _) = exact_regions(docs, 2, 10_000);
        assert!(has_pair(&regions, 0, 1, 4), "missing (doc0, doc1): {regions:?}");
        assert!(has_pair(&regions, 0, 2, 4), "missing (doc0, doc2): {regions:?}");
        assert!(has_pair(&regions, 1, 2, 4), "missing (doc1, doc2): {regions:?}");
    }

    #[test]
    fn exact_regions_four_way_shared_block_reports_every_pair() {
        // frob:tests frob-core/src/lib.rs::exact_regions kind="unit"
        let block: Vec<String> = (0..6).map(|i| format!("w{i}")).collect();
        let docs = vec![block.clone(), block.clone(), block.clone(), block.clone()];
        let (regions, _) = exact_regions(docs, 3, 10_000);
        for x in 0..4 {
            for y in (x + 1)..4 {
                assert!(has_pair(&regions, x, y, 6), "missing ({x}, {y}): {regions:?}");
            }
        }
    }

    #[test]
    fn exact_regions_mixed_case_two_nested_shared_regions() {
        // frob:tests frob-core/src/lib.rs::exact_regions kind="unit"
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
        let (regions, _) = exact_regions(vec![doc0, doc1, doc2], 3, 10_000);

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
        // frob:tests frob-core/src/lib.rs::exact_regions kind="unit"
        // T-0273: reviewer finding on T-0193 -- 2000 identical documents
        // sharing a block produced 1,999,000 unbounded pairs. With the
        // default cap (200) a 500-document run must emit at most
        // C(200, 2) = 19,900 pairs, never the unbounded C(500, 2) =
        // 124,750, and the truncation signal must be set so a caller
        // never mistakes the capped result for exhaustive.
        let block: Vec<String> = ["a", "b", "c", "d"].iter().map(|s| s.to_string()).collect();
        let docs: Vec<Vec<String>> = (0..500).map(|_| block.clone()).collect();
        let (regions, truncated) = exact_regions(docs, 2, 200);
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
        // frob:tests frob-core/src/lib.rs::exact_regions kind="unit"
        // A run at or below max_run_size is unaffected: no truncation
        // signal, and every pair among the (small) run is still reported.
        let block: Vec<String> = ["a", "b", "c", "d"].iter().map(|s| s.to_string()).collect();
        let docs: Vec<Vec<String>> = (0..5).map(|_| block.clone()).collect();
        let (regions, truncated) = exact_regions(docs, 2, 200);
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
}

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
    m.add_function(wrap_pyfunction!(exact_regions, m)?)?;
    Ok(())
}
