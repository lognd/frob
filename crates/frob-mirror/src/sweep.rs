//! Round-robin sweep (mirror.md 3.2): each run reconciles the next K issues after a persisted
//! cursor, so every issue is visited within ceil(N/K) runs even when the feed misses a change.

// frob:ticket 01M4052S04N2E2A08NNPAZKPYT

use tracing::debug;

/// The next up-to-`k` ULIDs of `all` after `cursor`, wrapping to the start; `all` need not be
/// sorted. A `cursor` that is absent or no longer present resumes at the first ULID after it in
/// sorted order, so a deleted cursor issue never stalls the sweep.
pub fn next_batch(all: &[String], cursor: Option<&str>, k: usize) -> Vec<String> {
    let mut sorted: Vec<&String> = all.iter().collect();
    sorted.sort();
    sorted.dedup();
    let start = cursor.map_or(0, |c| sorted.partition_point(|u| u.as_str() <= c));
    let take = k.min(sorted.len());
    let batch: Vec<String> = (0..take)
        .map(|i| sorted[(start + i) % sorted.len()].clone())
        .collect();
    debug!(
        n = sorted.len(),
        k,
        batch = batch.len(),
        "sweep: batch selected"
    );
    batch
}

/// The bound `frob mirror status` states: every issue is visited within ceil(n/k) runs
/// (a `k` of 0 never visits anything, reported as `None`).
pub fn visit_bound(n: u64, k: u64) -> Option<u64> {
    (k != 0).then(|| n.div_ceil(k))
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeSet;

    use super::*;

    fn ids(n: usize) -> Vec<String> {
        (0..n).map(|i| format!("U{i:03}")).collect()
    }

    // frob:tests next_batch
    // frob:tests visit_bound
    #[test]
    fn every_issue_visited_within_ceil_n_over_k_runs() {
        for (n, k) in [(10usize, 3usize), (9, 3), (1, 5), (7, 1), (0, 4)] {
            let all = ids(n);
            let mut seen = BTreeSet::new();
            let mut cursor: Option<String> = None;
            let runs = visit_bound(n as u64, k as u64).unwrap();
            for _ in 0..runs {
                let batch = next_batch(&all, cursor.as_deref(), k);
                if let Some(last) = batch.last() {
                    cursor = Some(last.clone());
                }
                seen.extend(batch);
            }
            assert_eq!(seen.len(), n, "n={n} k={k}");
        }
        assert_eq!(visit_bound(10, 0), None);
    }

    // frob:tests next_batch
    #[test]
    fn stopped_midway_resumes_after_last_completed() {
        let all = ids(10);
        let first = next_batch(&all, None, 4);
        // The run stopped after completing only two of the four.
        let cursor = first[1].clone();
        let next = next_batch(&all, Some(&cursor), 4);
        assert_eq!(next, ["U002", "U003", "U004", "U005"]);
        // Wraps past the end and survives a vanished cursor.
        assert_eq!(next_batch(&all, Some("U008"), 3), ["U009", "U000", "U001"]);
        assert_eq!(next_batch(&all, Some("U0035"), 2), ["U004", "U005"]);
    }
}
