//! Ticket-branch shard store: [`ShardStore`] over files committed to a git ref with CAS.
//!
//! Each key is one file `<prefix>/<key>.json` on `ref_name`. A write commits only when the
//! file's content hash at the ref tip still equals the caller's expectation; the ref
//! compare-and-swap is run without blind retry (`cas_retries = 0`), so a lost ref race is
//! re-read and re-verified here and surfaces as `MapError::Conflict` if the content moved.

// frob:ticket 01M5ASPRNKH3X9W5N9FDERAFCQ

use gob_git::{CommitOptions, GitError, RelPath, Repo};
use tracing::{debug, error, info, warn};

use crate::mapfile::{MapError, ShardStore, content_hash};

/// How many times a lost ref race is re-read and re-verified before giving up.
const RACE_RETRIES: u32 = 8;

/// A [`ShardStore`] persisted as files on a git ref (the ticket branch).
pub struct BranchShardStore {
    repo: Repo,
    ref_name: String,
    prefix: String,
    author: Option<(String, String)>,
}

impl BranchShardStore {
    /// A store writing `<prefix>/<key>.json` on `ref_name`; `author` overrides git config.
    pub fn new(repo: Repo, ref_name: &str, prefix: &str, author: Option<(String, String)>) -> Self {
        Self {
            repo,
            ref_name: ref_name.to_string(),
            prefix: prefix.trim_matches('/').to_string(),
            author,
        }
    }

    /// Repo-relative path of the file holding `key`.
    fn path_of(&self, key: &str) -> String {
        if self.prefix.is_empty() {
            format!("{key}.json")
        } else {
            format!("{}/{key}.json", self.prefix)
        }
    }

    /// Current bytes of `key` at the ref tip; a missing ref or file is absent.
    fn read(&self, key: &str) -> Result<Option<Vec<u8>>, GitError> {
        if self.repo.rev_parse(&self.ref_name).is_err() {
            debug!(ref_name = %self.ref_name, key, "shard ref absent; key absent");
            return Ok(None);
        }
        self.repo.read_blob_at(&self.ref_name, &self.path_of(key))
    }
}

/// Maps an unexpected git failure onto the store's error type (the trait has no I/O variant).
fn store_failure(key: &str, e: &GitError) -> MapError {
    error!(key, error = %e, "shard store git failure");
    MapError::Corrupt {
        key: key.to_string(),
        reason: format!("shard store failure: {e}"),
    }
}

impl ShardStore for BranchShardStore {
    /// Reads the shard file at the ref tip; git failures read as absent (logged).
    fn get(&self, key: &str) -> Option<Vec<u8>> {
        match self.read(key) {
            Ok(v) => v,
            Err(e) => {
                warn!(key, error = %e, "shard read failed; treating as absent");
                None
            }
        }
    }

    /// Commits `bytes` iff the stored content hash equals `expected`.
    fn put_if(
        &mut self,
        key: &str,
        expected: Option<&str>,
        bytes: Vec<u8>,
    ) -> Result<(), MapError> {
        let path = self.path_of(key);
        let rel = RelPath::new(path.clone()).map_err(|e| MapError::Corrupt {
            key: key.to_string(),
            reason: format!("invalid shard path {path}: {e}"),
        })?;
        let opts = CommitOptions {
            cas_retries: 0,
            author: self.author.clone(),
        };
        for attempt in 0..=RACE_RETRIES {
            let current = self.read(key).map_err(|e| store_failure(key, &e))?;
            let found = current.as_deref().map(content_hash);
            if found.as_deref() != expected {
                info!(key, ?expected, ?found, "shard CAS conflict");
                return Err(MapError::Conflict {
                    key: key.to_string(),
                    expected: expected.map(String::from),
                    found,
                });
            }
            let msg = format!("mirror: update shard {key}");
            match self.repo.commit_paths(
                &self.ref_name,
                &[(rel.clone(), Some(bytes.clone()))],
                &msg,
                &opts,
            ) {
                Ok(out) => {
                    info!(key, oid = %out.oid, attempt, "shard committed");
                    return Ok(());
                }
                Err(GitError::CasExhausted { .. }) => {
                    debug!(key, attempt, "ref moved under shard write; re-verifying");
                }
                Err(e) => return Err(store_failure(key, &e)),
            }
        }
        warn!(key, "shard write lost the ref race repeatedly");
        Err(MapError::Conflict {
            key: key.to_string(),
            expected: expected.map(String::from),
            found: self.get(key).as_deref().map(content_hash),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn store(dir: &std::path::Path) -> BranchShardStore {
        let repo = Repo::init(dir).unwrap();
        BranchShardStore::new(
            repo,
            "refs/heads/tickets",
            ".mirror",
            Some(("t".into(), "t@example.com".into())),
        )
    }

    // frob:tests BranchShardStore
    #[test]
    fn put_get_and_cas_round_trip() {
        let dir = tempfile::tempdir().unwrap();
        let mut s = store(dir.path());
        assert_eq!(s.get("a"), None);
        s.put_if("a", None, b"one".to_vec()).unwrap();
        assert_eq!(s.get("a").unwrap(), b"one");
        let h = content_hash(b"one");
        s.put_if("a", Some(&h), b"two".to_vec()).unwrap();
        assert_eq!(s.get("a").unwrap(), b"two");
    }

    // frob:tests BranchShardStore
    #[test]
    fn stale_expectation_conflicts() {
        let dir = tempfile::tempdir().unwrap();
        let mut s = store(dir.path());
        s.put_if("a", None, b"one".to_vec()).unwrap();
        let err = s.put_if("a", None, b"x".to_vec()).unwrap_err();
        assert!(matches!(err, MapError::Conflict { found: Some(_), .. }));
        let err = s.put_if("a", Some("bogus"), b"x".to_vec()).unwrap_err();
        assert!(matches!(err, MapError::Conflict { .. }));
        assert_eq!(s.get("a").unwrap(), b"one");
    }

    // frob:tests BranchShardStore
    #[test]
    fn keys_are_independent_and_second_handle_sees_writes() {
        let dir = tempfile::tempdir().unwrap();
        let mut s = store(dir.path());
        s.put_if("a", None, b"1".to_vec()).unwrap();
        s.put_if("b", None, b"2".to_vec()).unwrap();
        let other = BranchShardStore::new(
            Repo::discover(dir.path()).unwrap(),
            "refs/heads/tickets",
            ".mirror",
            None,
        );
        assert_eq!(other.get("a").unwrap(), b"1");
        assert_eq!(other.get("b").unwrap(), b"2");
    }
}
