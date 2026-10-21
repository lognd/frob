//! Progress commits (mirror.md 3.2, MIR-AUD-14): shards are committed every K operations.
//!
//! A shard batch is written first and the index (round-robin cursor) last, so a crash
//! repeats at most the K uncommitted operations and never an already-committed one.

// frob:ticket 01M4052W2RYSRASA1PE0PRJJ1V

use std::collections::BTreeMap;

use tracing::{debug, info};

use crate::mapfile::{
    INDEX_KEY, Index, MapError, Shard, ShardStore, content_hash, decode, encode, write_shard,
};

/// Why a run ended.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StopReason {
    /// All planned work finished.
    Completed,
    /// The rate limit stopped the run; `reset` is the unix time the next window opens.
    RateLimited {
        /// Unix time the window resets, when the headers gave it.
        reset: Option<u64>,
    },
}

/// What a finished run reports.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RunReport {
    /// Operations whose progress was committed by this run.
    pub committed_ops: u64,
    /// MIR001 message naming the next window, when the run was rate limited.
    pub mir001: Option<String>,
}

/// Buffers per-ticket progress and commits it to the map every `k` operations.
pub struct ProgressWriter<'a, S: ShardStore> {
    store: &'a mut S,
    k: u64,
    pending: BTreeMap<String, Shard>,
    ops_since_commit: u64,
    committed_ops: u64,
    index: Index,
    index_dirty: bool,
}

/// Reads the index shard; a missing index is a fresh one.
///
/// # Errors
/// `MapError::Corrupt` when the stored index does not decode.
pub fn read_index<S: ShardStore>(store: &S) -> Result<Index, MapError> {
    match store.get(INDEX_KEY) {
        None => Ok(Index::default()),
        Some(bytes) => decode(INDEX_KEY, &bytes),
    }
}

/// Commits `index` through CAS against what is currently stored.
///
/// # Errors
/// `MapError::Conflict` when another writer changed the index first.
pub fn write_index<S: ShardStore>(store: &mut S, index: &Index) -> Result<(), MapError> {
    let expected = store.get(INDEX_KEY).map(|b| content_hash(&b));
    store.put_if(INDEX_KEY, expected.as_deref(), encode(index))
}

impl<'a, S: ShardStore> ProgressWriter<'a, S> {
    /// Starts a writer committing every `k` operations (a `k` of 0 is treated as 1).
    ///
    /// # Errors
    /// `MapError::Corrupt` when the stored index does not decode.
    pub fn new(store: &'a mut S, k: u64) -> Result<Self, MapError> {
        let index = read_index(store)?;
        Ok(Self {
            store,
            k: k.max(1),
            pending: BTreeMap::new(),
            ops_since_commit: 0,
            committed_ops: 0,
            index,
            index_dirty: false,
        })
    }

    /// The ULID the next run resumes after (the committed round-robin cursor).
    pub fn resume_after(&self) -> Option<&str> {
        self.index.round_robin.as_deref()
    }

    /// Advances the change-feed cursor; it is written with the next commit, even with no ops.
    pub fn set_change_feed(&mut self, cursor: String) {
        if self.index.change_feed.as_deref() != Some(cursor.as_str()) {
            debug!(%cursor, "mirror progress: change-feed cursor advanced");
            self.index.change_feed = Some(cursor);
            self.index_dirty = true;
        }
    }

    /// The store the writer commits to, for reads while the run holds it.
    #[must_use]
    pub fn store(&self) -> &S {
        self.store
    }

    /// The store the writer commits to, lent to the host for one item's writes.
    pub fn store_mut(&mut self) -> &mut S {
        self.store
    }

    /// Records one completed operation for `shard`; commits when K have accumulated.
    ///
    /// # Errors
    /// `MapError::Conflict` when a CAS write loses to another writer.
    pub fn record(&mut self, shard: Shard) -> Result<(), MapError> {
        self.index.round_robin = Some(shard.ulid.clone());
        self.pending.insert(shard.ulid.clone(), shard);
        self.ops_since_commit += 1;
        if self.ops_since_commit >= self.k {
            self.commit()?;
        }
        Ok(())
    }

    /// Writes the pending shards, then the index cursor last.
    ///
    /// # Errors
    /// `MapError::Conflict` when a CAS write loses to another writer.
    pub fn commit(&mut self) -> Result<(), MapError> {
        if self.ops_since_commit == 0 && !self.index_dirty {
            return Ok(());
        }
        for shard in self.pending.values() {
            write_shard(self.store, shard)?;
        }
        write_index(self.store, &self.index)?;
        debug!(
            shards = self.pending.len(),
            ops = self.ops_since_commit,
            "mirror progress committed"
        );
        self.committed_ops += self.ops_since_commit;
        self.pending.clear();
        self.ops_since_commit = 0;
        self.index_dirty = false;
        Ok(())
    }

    /// Commits what remains and reports the run, naming the next window when rate limited.
    ///
    /// # Errors
    /// `MapError::Conflict` when the final commit loses to another writer.
    pub fn finish(mut self, reason: StopReason) -> Result<RunReport, MapError> {
        self.commit()?;
        let mir001 = match reason {
            StopReason::Completed => None,
            StopReason::RateLimited { reset } => {
                let window =
                    reset.map_or_else(|| "unknown".to_string(), |r| format!("unix time {r}"));
                info!(%window, "run stopped by rate limit; progress committed");
                Some(format!("MIR001 rate-limited: next window at {window}"))
            }
        };
        Ok(RunReport {
            committed_ops: self.committed_ops,
            mir001,
        })
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use super::*;

    #[derive(Default)]
    struct Mem(HashMap<String, Vec<u8>>);

    impl ShardStore for Mem {
        fn get(&self, key: &str) -> Option<Vec<u8>> {
            self.0.get(key).cloned()
        }
        fn put_if(
            &mut self,
            key: &str,
            expected: Option<&str>,
            bytes: Vec<u8>,
        ) -> Result<(), MapError> {
            let found = self.get(key).map(|b| content_hash(&b));
            if found.as_deref() != expected {
                return Err(MapError::Conflict {
                    key: key.into(),
                    expected: expected.map(String::from),
                    found,
                });
            }
            self.0.insert(key.into(), bytes);
            Ok(())
        }
    }

    // frob:tests finish
    // frob:tests record
    #[test]
    fn rate_limited_stop_commits_and_names_window() {
        let mut store = Mem::default();
        let mut w = ProgressWriter::new(&mut store, 10).unwrap();
        w.record(Shard::new("A")).unwrap();
        w.record(Shard::new("B")).unwrap();
        let report = w
            .finish(StopReason::RateLimited { reset: Some(1234) })
            .unwrap();
        assert_eq!(report.committed_ops, 2);
        assert!(report.mir001.unwrap().contains("MIR001 rate-limited"));
        assert!(store.get("A").is_some() && store.get("B").is_some());
        assert_eq!(
            read_index(&store).unwrap().round_robin.as_deref(),
            Some("B")
        );
    }

    // frob:tests set_change_feed
    // frob:tests finish
    #[test]
    fn change_feed_cursor_is_written_without_ops_and_keeps_round_robin() {
        let mut store = Mem::default();
        let mut w = ProgressWriter::new(&mut store, 10).unwrap();
        w.record(Shard::new("A")).unwrap();
        w.finish(StopReason::Completed).unwrap();
        let mut w = ProgressWriter::new(&mut store, 10).unwrap();
        w.set_change_feed("2026-10-05T00:00:00Z".into());
        w.finish(StopReason::Completed).unwrap();
        let index = read_index(&store).unwrap();
        assert_eq!(index.change_feed.as_deref(), Some("2026-10-05T00:00:00Z"));
        assert_eq!(index.round_robin.as_deref(), Some("A"));
    }

    // frob:tests record
    // frob:tests resume_after
    #[test]
    fn crash_repeats_at_most_k_and_none_duplicated() {
        let mut store = Mem::default();
        let ulids: Vec<String> = (0..7).map(|i| format!("U{i}")).collect();
        {
            // Crash (drop without finish) after 7 ops with K=3: 6 committed, 1 lost.
            let mut w = ProgressWriter::new(&mut store, 3).unwrap();
            for u in &ulids {
                w.record(Shard::new(u)).unwrap();
            }
        }
        let w = ProgressWriter::new(&mut store, 3).unwrap();
        let resume = w.resume_after().unwrap().to_string();
        assert_eq!(resume, "U5");
        let pos = ulids.iter().position(|u| *u == resume).unwrap();
        let repeated = &ulids[pos + 1..];
        assert!(repeated.len() as u64 <= 3);
        assert_eq!(repeated, ["U6"]);
        // Every committed ulid is behind the cursor: none is redone.
        assert!(ulids[..=pos].iter().all(|u| store.get(u).is_some()));
    }
}
