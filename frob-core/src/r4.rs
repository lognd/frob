//! R4: winnowing/candidate-pairing/tree-edit-distance rung, split out of
//! lib.rs by T-2846.
//! frob:ticket T-2846

use pyo3::prelude::*;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::collections::HashMap;

/// R4: winnowing fingerprints (Moss-style) over sliding token windows.
///
/// Returns the set of selected k-gram hashes after winnowing with window
/// `w`, so fingerprints are position-independent -- the same substring
/// anywhere in the token stream produces the same fingerprint, which is
/// what makes region-granular matching (docs/modules/dup.md's "regions, not just
/// functions") fall out for free.
#[pyfunction]
pub fn winnow_fingerprints(tokens: Vec<String>, k: usize, w: usize) -> Vec<u64> {
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
pub fn candidate_pairs(fingerprint_sets: Vec<Vec<u64>>, min_shared: usize) -> Vec<(usize, usize)> {
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
pub fn tree_edit_similarity(a: Vec<u64>, b: Vec<u64>) -> (f64, Vec<(usize, usize)>) {
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
pub(crate) fn build_postorder(parents: &[i64]) -> (Vec<usize>, Vec<usize>, usize) {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
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
pub(crate) fn zhang_shasha_distance(
    labels_a: &[String],
    postorder_a: &[usize],
    lmd_a: &[usize],
    labels_b: &[String],
    postorder_b: &[usize],
    lmd_b: &[usize],
) -> usize {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
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
pub fn apted_similarity(
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

