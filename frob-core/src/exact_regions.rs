//! R1.5: exact-region suffix-array matching rung, split out of lib.rs by
//! T-2846.
//! frob:ticket T-2846

use pyo3::prelude::*;
use std::collections::HashMap;

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
pub(crate) fn build_suffix_array(s: &[i64]) -> Vec<usize> {
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
pub(crate) fn kasai_lcp(s: &[i64], sa: &[usize]) -> Vec<usize> {
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
pub fn exact_regions(
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

