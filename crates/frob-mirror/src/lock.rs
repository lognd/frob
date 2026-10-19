//! Writer lock and ledger watermark (mirror.md 3.1, MIR-AUD-13): one mirror writer at a time.
//!
//! The lock is a record stored under a CAS key; a live holder makes a second run exit
//! without work, a stale one (past the TTL) is taken over by CAS. The watermark is the last
//! processed ledger commit; the mirror's own ledger commits never start a run.

// frob:ticket 01M4052S40VQGKG930DZPSM01K

use serde::{Deserialize, Serialize};
use tracing::{debug, info};

use crate::mapfile::{MapError, ShardStore, content_hash, decode, encode};

/// Key under which the writer lock is stored.
pub const LOCK_KEY: &str = "writer-lock";
/// Key under which the watermark is stored.
pub const WATERMARK_KEY: &str = "watermark";

/// The stored lock record.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LockRecord {
    /// The run holding the lock.
    pub run_id: String,
    /// Unix time (seconds) the lock was taken or last refreshed.
    pub taken_at: u64,
}

/// The outcome of trying to take the writer lock.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Acquire {
    /// The lock is ours; `takeover` names the stale holder we replaced, if any.
    Held {
        /// The run whose stale lock was taken over.
        takeover: Option<String>,
    },
    /// A live run holds the lock: exit without work and without error.
    Busy {
        /// The live holder.
        holder: String,
    },
}

/// Takes the writer lock for `run_id` at unix time `now`; a lock older than `ttl_secs` is stale.
///
/// # Errors
/// `MapError::Corrupt` when the stored record does not decode; `MapError::Conflict`
/// when another run wins the CAS race (the caller treats that as busy).
pub fn acquire<S: ShardStore>(
    store: &mut S,
    run_id: &str,
    now: u64,
    ttl_secs: u64,
) -> Result<Acquire, MapError> {
    let current = store.get(LOCK_KEY);
    let mut takeover = None;
    if let Some(bytes) = &current {
        let held: LockRecord = decode(LOCK_KEY, bytes)?;
        if held.run_id.is_empty() {
            debug!("writer lock was released");
        } else if now.saturating_sub(held.taken_at) < ttl_secs {
            debug!(holder = %held.run_id, "writer lock held by a live run");
            return Ok(Acquire::Busy {
                holder: held.run_id,
            });
        } else {
            info!(stale = %held.run_id, run = run_id, "taking over stale writer lock");
            takeover = Some(held.run_id);
        }
    }
    let expected = current.as_deref().map(content_hash);
    let record = LockRecord {
        run_id: run_id.to_string(),
        taken_at: now,
    };
    store.put_if(LOCK_KEY, expected.as_deref(), encode(&record))?;
    info!(run = run_id, "writer lock acquired");
    Ok(Acquire::Held { takeover })
}

/// Releases the lock if `run_id` still holds it; a lock taken over by another run stays.
///
/// # Errors
/// `MapError::Corrupt` when the stored record does not decode; `MapError::Conflict` on a lost race.
pub fn release<S: ShardStore>(store: &mut S, run_id: &str) -> Result<(), MapError> {
    let Some(bytes) = store.get(LOCK_KEY) else {
        return Ok(());
    };
    let held: LockRecord = decode(LOCK_KEY, &bytes)?;
    if held.run_id != run_id {
        info!(run = run_id, holder = %held.run_id, "lock no longer ours; not releasing");
        return Ok(());
    }
    // An empty record marks the lock free while keeping CAS history simple.
    let free = LockRecord {
        run_id: String::new(),
        taken_at: 0,
    };
    store.put_if(LOCK_KEY, Some(&content_hash(&bytes)), encode(&free))?;
    info!(run = run_id, "writer lock released");
    Ok(())
}

/// A ledger commit as the run sees it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LedgerCommit {
    /// The commit id.
    pub id: String,
    /// True when the mirror itself authored it.
    pub own: bool,
}

/// The last processed ledger commit.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Watermark {
    /// Id of the last processed commit.
    pub commit: String,
}

/// Reads the watermark; none yet means every ledger commit is new.
///
/// # Errors
/// `MapError::Corrupt` when the stored watermark does not decode.
pub fn read_watermark<S: ShardStore>(store: &S) -> Result<Option<Watermark>, MapError> {
    store
        .get(WATERMARK_KEY)
        .map(|b| decode(WATERMARK_KEY, &b))
        .transpose()
}

/// Advances the watermark to `commit` by CAS.
///
/// # Errors
/// `MapError::Conflict` when another writer moved it first.
pub fn write_watermark<S: ShardStore>(store: &mut S, commit: &str) -> Result<(), MapError> {
    let expected = store.get(WATERMARK_KEY).map(|b| content_hash(&b));
    let mark = Watermark {
        commit: commit.to_string(),
    };
    store.put_if(WATERMARK_KEY, expected.as_deref(), encode(&mark))?;
    debug!(commit, "watermark advanced");
    Ok(())
}

/// Commits to process: those after the watermark (oldest first), minus the mirror's own.
///
/// A watermark absent from `commits` (history rewritten) yields every non-own commit.
pub fn pending_commits<'a>(
    watermark: Option<&Watermark>,
    commits: &'a [LedgerCommit],
) -> Vec<&'a LedgerCommit> {
    let start = watermark
        .and_then(|w| commits.iter().position(|c| c.id == w.commit))
        .map_or(0, |i| i + 1);
    commits[start..].iter().filter(|c| !c.own).collect()
}

/// Whether a ledger commit starts a run: the mirror's own never does.
pub fn triggers_run(commit: &LedgerCommit) -> bool {
    !commit.own
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

    fn commit(id: &str, own: bool) -> LedgerCommit {
        LedgerCommit { id: id.into(), own }
    }

    // frob:tests acquire
    #[test]
    fn live_lock_makes_second_run_busy() {
        let mut s = Mem::default();
        assert_eq!(
            acquire(&mut s, "r1", 100, 60).unwrap(),
            Acquire::Held { takeover: None }
        );
        assert_eq!(
            acquire(&mut s, "r2", 130, 60).unwrap(),
            Acquire::Busy {
                holder: "r1".into()
            }
        );
    }

    // frob:tests acquire
    // frob:tests release
    #[test]
    fn stale_lock_is_taken_over_by_cas() {
        let mut s = Mem::default();
        acquire(&mut s, "r1", 100, 60).unwrap();
        assert_eq!(
            acquire(&mut s, "r2", 160, 60).unwrap(),
            Acquire::Held {
                takeover: Some("r1".into())
            }
        );
        // The old run no longer owns it, so its release leaves r2 in place.
        release(&mut s, "r1").unwrap();
        assert_eq!(
            acquire(&mut s, "r3", 161, 60).unwrap(),
            Acquire::Busy {
                holder: "r2".into()
            }
        );
        release(&mut s, "r2").unwrap();
        assert_eq!(
            acquire(&mut s, "r3", 162, 60).unwrap(),
            Acquire::Held { takeover: None }
        );
    }

    // frob:tests pending_commits
    // frob:tests triggers_run
    // frob:tests write_watermark
    // frob:tests read_watermark
    #[test]
    fn watermark_limits_work_and_skips_own_commits() {
        let mut s = Mem::default();
        assert!(read_watermark(&s).unwrap().is_none());
        write_watermark(&mut s, "c2").unwrap();
        write_watermark(&mut s, "c3").unwrap();
        let w = read_watermark(&s).unwrap();
        let log = [
            commit("c1", false),
            commit("c2", false),
            commit("c3", false),
            commit("c4", true),
            commit("c5", false),
        ];
        let ids: Vec<_> = pending_commits(w.as_ref(), &log)
            .iter()
            .map(|c| c.id.as_str())
            .collect();
        assert_eq!(ids, ["c5"]);
        assert!(!triggers_run(&log[3]));
        assert!(triggers_run(&log[4]));
    }
}
