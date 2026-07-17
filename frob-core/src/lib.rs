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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_hash_is_deterministic_and_shape_sensitive() {
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
}

#[pymodule]
fn frob_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(r3_canonical_hash, m)?)?;
    m.add_function(wrap_pyfunction!(winnow_fingerprints, m)?)?;
    m.add_function(wrap_pyfunction!(candidate_pairs, m)?)?;
    m.add_function(wrap_pyfunction!(tree_edit_similarity, m)?)?;
    Ok(())
}
