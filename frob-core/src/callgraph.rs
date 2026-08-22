//! Callgraph/arch-similarity rung (called_names/resolve_call_edges and the
//! difflib-style ratio helpers), split out of lib.rs by T-2846.
//! frob:ticket T-2846

use pyo3::prelude::*;
use std::collections::HashMap;

/// Approximates Python's `str.isidentifier()` over the token alphabet
/// `frob.lang`'s tokenizers actually emit (identifiers vs punctuation/
/// operator/literal tokens) -- first char a letter or underscore, every
/// other char alphanumeric or underscore, Unicode-aware via Rust's own
/// `char::is_alphabetic`/`is_alphanumeric` (T-0930, same "close enough
/// for real source token text, documented rather than silently assumed"
/// posture as this crate's `is_numeric_literal`/`is_string_literal`).
fn is_identifier_token(tok: &str) -> bool {
    let mut chars = tok.chars();
    match chars.next() {
        Some(c) if c == '_' || c.is_alphabetic() => {}
        _ => return false,
    }
    chars.all(|c| c == '_' || c.is_alphanumeric())
}

/// T-0930: the `frob.graph.callgraph._called_names`/`_ordered_called_names`
/// shared token scan -- an identifier token immediately followed by `(`
/// is a call name; a bare-identifier argument to a known wrapper marker
/// (`memoize_per_run(_target)`) is rescued too (T-0583). `ordered`
/// selects which of the two Python functions' contracts to match:
/// `false` collapses into a de-duplicated, UNORDERED name list
/// (`_called_names`'s frozenset contract); `true` preserves source-text
/// order with duplicates kept (`_ordered_called_names`'s contract) --
/// same scan, two output shapes, avoiding two near-identical loops.
fn scan_call_tokens(body_tokens: &[String], wrapper_markers: &[String], ordered: bool) -> Vec<String> {
    let markers: std::collections::HashSet<&str> =
        wrapper_markers.iter().map(|s| s.as_str()).collect();
    let n = body_tokens.len();
    let mut ordered_out: Vec<String> = Vec::new();
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    for i in 0..n.saturating_sub(1) {
        let tok = &body_tokens[i];
        if body_tokens[i + 1] != "(" || !is_identifier_token(tok) {
            continue;
        }
        if ordered || seen.insert(tok.clone()) {
            ordered_out.push(tok.clone());
        }
        if markers.contains(tok.as_str())
            && i + 2 < n
            && is_identifier_token(&body_tokens[i + 2])
            && (i + 3 >= n || body_tokens[i + 3] == ")" || body_tokens[i + 3] == ",")
        {
            let wrapped = &body_tokens[i + 2];
            if ordered || seen.insert(wrapped.clone()) {
                ordered_out.push(wrapped.clone());
            }
        }
    }
    ordered_out
}

/// T-0930: `frob.graph.callgraph._called_names` -- de-duplicated call-name
/// scan (see `scan_call_tokens`).
// frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
#[pyfunction]
pub fn called_names(body_tokens: Vec<String>, wrapper_markers: Vec<String>) -> Vec<String> {
    scan_call_tokens(&body_tokens, &wrapper_markers, false)
}

/// T-0930: `frob.graph.callgraph._ordered_called_names` -- source-order,
/// duplicates-kept call-name scan (see `scan_call_tokens`).
// frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
#[pyfunction]
pub fn ordered_called_names(body_tokens: Vec<String>, wrapper_markers: Vec<String>) -> Vec<String> {
    scan_call_tokens(&body_tokens, &wrapper_markers, true)
}

/// T-0930: `frob.graph.callgraph._referenced_names` -- every identifier
/// token across `sig_tokens` then `body_tokens`, de-duplicated (broader
/// recall than `called_names`: catches dispatch-table/decorator/default-
/// value mentions that never appear as a `name(` call token at all).
// frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
#[pyfunction]
pub fn referenced_names(sig_tokens: Vec<String>, body_tokens: Vec<String>) -> Vec<String> {
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut out: Vec<String> = Vec::new();
    for tok in sig_tokens.iter().chain(body_tokens.iter()) {
        if is_identifier_token(tok) && seen.insert(tok.clone()) {
            out.push(tok.clone());
        }
    }
    out
}

/// T-0930: `frob.graph.callgraph._unresolved_exempt_names` -- every call
/// name whose EVERY occurrence is an attribute call on a receiver other
/// than `self` (T-0813's `obj._method(...)`/`super().__init__(...)`
/// false-positive disposition).
// frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
#[pyfunction]
pub fn unresolved_exempt_names(body_tokens: Vec<String>) -> Vec<String> {
    let mut confident: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut all_calls: std::collections::HashSet<String> = std::collections::HashSet::new();
    let n = body_tokens.len();
    for i in 0..n.saturating_sub(1) {
        let tok = &body_tokens[i];
        if body_tokens[i + 1] != "(" || !is_identifier_token(tok) {
            continue;
        }
        all_calls.insert(tok.clone());
        let is_attr_call = i > 0 && body_tokens[i - 1] == ".";
        let receiver_is_self = is_attr_call && i > 1 && body_tokens[i - 2] == "self";
        if !is_attr_call || receiver_is_self {
            confident.insert(tok.clone());
        }
    }
    all_calls.difference(&confident).cloned().collect()
}

/// T-0930: resolve caller->callee edges over a PRE-EXTRACTED per-caller
/// name list against a shared by-short-name candidate index -- the hot
/// `O(names * candidates)` matching + `UNRESOLVED_CALLEE` bookkeeping loop
/// inside `frob.graph.callgraph._resolve_edges` (dead_symbols's DEAD001
/// gate, `build_call_graph`, `build_reference_graph` all share this
/// substrate, docs/audits/check-performance.md rust-candidate row 8).
///
/// Data-in/data-out, matching this crate's whole-file convention: token
/// extraction (`_called_names`/`_referenced_names`) and privacy
/// classification (`RawSymbol.public`) both stay in Python -- this is
/// only the matching loop, byte-identical in behavior to
/// `frob.graph.callgraph._resolve_edges_python` (the pure-Python fallback
/// kept alongside this for when `frob_core` is unavailable).
///
/// `callers`/`names_per_caller`/`exempt_per_caller` are parallel, same
/// length, one entry per symbol. Returns `(caller, callees)` pairs in
/// CALLER-ITERATION ORDER (not a `HashMap`, deliberately -- Python's own
/// dict-insertion-order contract must survive the FFI boundary) with
/// callers that resolved to zero callees omitted, exactly like the
/// Python original.
// frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
#[pyfunction]
pub fn resolve_call_edges(
    callers: Vec<String>,
    names_per_caller: Vec<Vec<String>>,
    exempt_per_caller: Vec<Vec<String>>,
    by_name: HashMap<String, Vec<(String, String, bool)>>,
    mark_unresolved: bool,
    unresolved_sentinel: String,
) -> Vec<(String, Vec<String>)> {
    let mut out: Vec<(String, Vec<String>)> = Vec::with_capacity(callers.len());
    for ((caller, names), exempt) in callers
        .into_iter()
        .zip(names_per_caller.into_iter())
        .zip(exempt_per_caller.into_iter())
    {
        let exempt_set: std::collections::HashSet<&str> =
            exempt.iter().map(|s| s.as_str()).collect();
        let mut callees: Vec<String> = Vec::new();
        let mut saw_unresolved = false;
        for name in &names {
            let candidates = by_name.get(name);
            let mut matched_private = false;
            if let Some(cands) = candidates {
                for (symref, _cand_path, is_private) in cands {
                    if symref == &caller {
                        continue;
                    }
                    if *is_private {
                        callees.push(symref.clone());
                        matched_private = true;
                    }
                }
            }
            let has_candidates = candidates.is_some_and(|c| !c.is_empty());
            if mark_unresolved
                && !matched_private
                && !has_candidates
                && name.starts_with('_')
                && !exempt_set.contains(name.as_str())
            {
                saw_unresolved = true;
            }
        }
        if saw_unresolved {
            callees.push(unresolved_sentinel.clone());
        }
        if !callees.is_empty() {
            out.push((caller, callees));
        }
    }
    out
}

// T-0953: archgate's `_near_duplicate_cluster` (src/frob/arch/_python.py)
// body-similarity clustering, ported from a statement-for-statement read of
// CPython's `difflib.py` (`SequenceMatcher`, autojunk enabled, no explicit
// `isjunk` -- exactly the call shape `_near_duplicate_cluster` uses:
// `difflib.SequenceMatcher(None, a, b).ratio()`). Parity here means
// byte-identical cluster membership, not merely close scores -- a
// near-duplicate detector that quietly drifts from its Python twin would
// silently change which functions get flagged as extractable abstractions.

/// `b2j`: char -> ascending list of indices in `b` where it occurs, and
/// `bjunk`: the "popular" chars CPython's autojunk heuristic excludes from
/// `b2j` when `b` is long enough (`len(b) >= 200`) for a char occurring in
/// more than 1% of it to be noise rather than signal. Mirrors
/// `difflib.SequenceMatcher.__chain_b` exactly (no explicit `isjunk`, so
/// `bjunk` here is purely the autojunk set).
fn arch_sim_build_b2j(
    b: &[char],
) -> (HashMap<char, Vec<usize>>, std::collections::HashSet<char>) {
    let mut b2j: HashMap<char, Vec<usize>> = HashMap::new();
    for (i, &c) in b.iter().enumerate() {
        b2j.entry(c).or_default().push(i);
    }
    let mut bjunk = std::collections::HashSet::new();
    let n = b.len();
    if n >= 200 {
        let ntest = n / 100 + 1;
        let popular: Vec<char> = b2j
            .iter()
            .filter(|(_, idxs)| idxs.len() > ntest)
            .map(|(&c, _)| c)
            .collect();
        for c in popular {
            bjunk.insert(c);
            b2j.remove(&c);
        }
    }
    (b2j, bjunk)
}

/// Port of `difflib.SequenceMatcher.find_longest_match`: the longest
/// matching block of `a[alo:ahi]` against `b[blo:bhi]`, extended first over
/// non-junk boundary chars, then over junk ones -- same two-phase extension
/// CPython's own implementation does, in the same order (order matters:
/// swapping phases can pick a different, still-maximal, block).
fn arch_sim_find_longest_match(
    a: &[char],
    b: &[char],
    b2j: &HashMap<char, Vec<usize>>,
    bjunk: &std::collections::HashSet<char>,
    alo: usize,
    ahi: usize,
    blo: usize,
    bhi: usize,
) -> (usize, usize, usize) {
    let mut besti = alo;
    let mut bestj = blo;
    let mut bestsize = 0usize;
    let mut j2len: HashMap<usize, usize> = HashMap::new();
    for i in alo..ahi {
        let mut newj2len: HashMap<usize, usize> = HashMap::new();
        if let Some(js) = b2j.get(&a[i]) {
            for &j in js {
                if j < blo {
                    continue;
                }
                if j >= bhi {
                    break;
                }
                let k = if j == 0 {
                    1
                } else {
                    j2len.get(&(j - 1)).copied().unwrap_or(0) + 1
                };
                newj2len.insert(j, k);
                if k > bestsize {
                    besti = i + 1 - k;
                    bestj = j + 1 - k;
                    bestsize = k;
                }
            }
        }
        j2len = newj2len;
    }
    while besti > alo
        && bestj > blo
        && !bjunk.contains(&b[bestj - 1])
        && a[besti - 1] == b[bestj - 1]
    {
        besti -= 1;
        bestj -= 1;
        bestsize += 1;
    }
    while besti + bestsize < ahi
        && bestj + bestsize < bhi
        && !bjunk.contains(&b[bestj + bestsize])
        && a[besti + bestsize] == b[bestj + bestsize]
    {
        bestsize += 1;
    }
    while besti > alo
        && bestj > blo
        && bjunk.contains(&b[bestj - 1])
        && a[besti - 1] == b[bestj - 1]
    {
        besti -= 1;
        bestj -= 1;
        bestsize += 1;
    }
    while besti + bestsize < ahi
        && bestj + bestsize < bhi
        && bjunk.contains(&b[bestj + bestsize])
        && a[besti + bestsize] == b[bestj + bestsize]
    {
        bestsize += 1;
    }
    (besti, bestj, bestsize)
}

/// Port of `difflib.SequenceMatcher.get_matching_blocks`: the maximal set of
/// non-adjacent matching `(a_start, b_start, size)` triples covering `a`/`b`,
/// via the same iterative divide-and-conquer queue (not recursion, to avoid
/// a Rust stack-depth concern the Python original's recursion doesn't have
/// to worry about at CPython's default recursion limit) followed by the
/// same adjacent-block merge pass.
fn arch_sim_matching_blocks(
    a: &[char],
    b: &[char],
    b2j: &HashMap<char, Vec<usize>>,
    bjunk: &std::collections::HashSet<char>,
) -> Vec<(usize, usize, usize)> {
    let la = a.len();
    let lb = b.len();
    let mut queue = vec![(0usize, la, 0usize, lb)];
    let mut raw: Vec<(usize, usize, usize)> = Vec::new();
    while let Some((alo, ahi, blo, bhi)) = queue.pop() {
        let (i, j, k) = arch_sim_find_longest_match(a, b, b2j, bjunk, alo, ahi, blo, bhi);
        if k > 0 {
            raw.push((i, j, k));
            if alo < i && blo < j {
                queue.push((alo, i, blo, j));
            }
            if i + k < ahi && j + k < bhi {
                queue.push((i + k, ahi, j + k, bhi));
            }
        }
    }
    raw.sort();
    let mut non_adjacent: Vec<(usize, usize, usize)> = Vec::new();
    let (mut i1, mut j1, mut k1) = (0usize, 0usize, 0usize);
    for (i2, j2, k2) in raw {
        if i1 + k1 == i2 && j1 + k1 == j2 {
            k1 += k2;
        } else {
            if k1 > 0 {
                non_adjacent.push((i1, j1, k1));
            }
            i1 = i2;
            j1 = j2;
            k1 = k2;
        }
    }
    if k1 > 0 {
        non_adjacent.push((i1, j1, k1));
    }
    non_adjacent
}

/// Port of `difflib.SequenceMatcher(None, a, b).ratio()`: `2*M / T` where
/// `M` is the total matched length from `get_matching_blocks` and `T` is
/// `len(a) + len(b)` (1.0 when both are empty, matching CPython's
/// `_calculate_ratio`'s zero-length special case).
pub(crate) fn arch_sim_ratio(a: &[char], b: &[char]) -> f64 {
    // frob:doc docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface
    let (b2j, bjunk) = arch_sim_build_b2j(b);
    let blocks = arch_sim_matching_blocks(a, b, &b2j, &bjunk);
    let matches: usize = blocks.iter().map(|&(_, _, k)| k).sum();
    let length = a.len() + b.len();
    if length == 0 {
        1.0
    } else {
        2.0 * matches as f64 / length as f64
    }
}

/// `_near_duplicate_cluster`'s pairwise body-similarity clustering
/// (docs/modules/arch.md, T-0370/T-0953), moved to Rust as ONE marshal per
/// same-signature group (not per pairwise comparison -- the batching shape
/// T-0930's reverted `resolve_call_edges` prototype lacked). `bodies` are
/// already-eligible (`>= _BODY_MIN_TOKENS`), already-normalized
/// body-fingerprint strings; returns the sorted indices of members that
/// have at least one same-group partner scoring `>= threshold` under
/// `arch_sim_ratio` (difflib-`SequenceMatcher.ratio()`-equivalent).
// frob:doc docs/modules/dup.md#rust-core
#[pyfunction]
pub fn near_duplicate_indices(bodies: Vec<String>, threshold: f64) -> Vec<usize> {
    let chars: Vec<Vec<char>> = bodies.iter().map(|s| s.chars().collect()).collect();
    let mut cluster: std::collections::HashSet<usize> = std::collections::HashSet::new();
    for i in 0..chars.len() {
        for j in (i + 1)..chars.len() {
            if arch_sim_ratio(&chars[i], &chars[j]) >= threshold {
                cluster.insert(i);
                cluster.insert(j);
            }
        }
    }
    let mut out: Vec<usize> = cluster.into_iter().collect();
    out.sort_unstable();
    out
}

