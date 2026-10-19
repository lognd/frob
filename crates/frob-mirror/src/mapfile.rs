//! Mirror map shards (mirror.md 3.2-3.4): a per-ticket cache of tracker identity.
//!
//! The tracker is the identity authority; the map only caches it. A lost shard or map is
//! rebuilt from the tracker listing by ULID marker and never by creating.

// frob:ticket 01M3ZX83J29R620BVRAVK5Z6DZ

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{debug, info, warn};

/// A create whose outcome is unknown: blocks further creates until recovery matches the nonce.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CreateUncertain {
    /// Nonce embedded in the marker of the attempted create.
    pub nonce: String,
    /// Create-start time (RFC 3339); recovery lists issues back to it.
    pub started: String,
}

/// One ticket's cached tracker identity, cursors and observed values.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Shard {
    /// The ticket ULID.
    pub ulid: String,
    /// Tracker issue number (the tracker key), once known.
    pub issue_number: Option<u64>,
    /// Tracker node id of the issue.
    pub node_id: Option<String>,
    /// Cached issue location (updated on a verified 301).
    pub location: Option<String>,
    /// Last observed normalized value per repository-owned field.
    pub observed: BTreeMap<String, String>,
    /// History cursor: the tracker event id actually read.
    pub history_cursor: Option<String>,
    /// Hash of the last ledger event published for this ticket.
    pub last_event: Option<String>,
    /// Create-uncertain flag with nonce and start time.
    pub create_uncertain: Option<CreateUncertain>,
}

impl Shard {
    /// A fresh shard for a ticket that has no tracker identity yet.
    pub fn new(ulid: &str) -> Self {
        Self {
            ulid: ulid.to_string(),
            issue_number: None,
            node_id: None,
            location: None,
            observed: BTreeMap::new(),
            history_cursor: None,
            last_event: None,
            create_uncertain: None,
        }
    }
}

/// The small index shard: round-robin and change-feed cursors.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Index {
    /// ULID the round-robin sweep resumes after.
    pub round_robin: Option<String>,
    /// Change-feed cursor (update time of the last issue seen).
    pub change_feed: Option<String>,
}

/// Errors from the map store.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum MapError {
    /// The shard content no longer matches the expected hash (CAS lost).
    #[error("shard {key} changed under us: expected {expected:?}, found {found:?}")]
    Conflict {
        /// Shard key.
        key: String,
        /// Hash the writer expected.
        expected: Option<String>,
        /// Hash actually present.
        found: Option<String>,
    },
    /// Shard bytes are not valid shard JSON.
    #[error("shard {key} is corrupt: {reason}")]
    Corrupt {
        /// Shard key.
        key: String,
        /// Decoder message.
        reason: String,
    },
}

/// Key under which the index shard is stored.
pub const INDEX_KEY: &str = "index";

/// Content hash used as the CAS token for a shard's bytes.
pub fn content_hash(bytes: &[u8]) -> String {
    blake3::hash(bytes).to_hex().to_string()
}

/// Canonical bytes of a serializable shard (pretty JSON, stable key order).
///
/// # Panics
/// Never for shard types: they contain only strings, numbers and maps.
pub fn encode<T: Serialize>(shard: &T) -> Vec<u8> {
    let mut out = serde_json::to_vec_pretty(shard).expect("shard types always serialize");
    out.push(b'\n');
    out
}

/// Decodes shard bytes read from `key`.
///
/// # Errors
/// `MapError::Corrupt` when the bytes are not valid shard JSON.
pub fn decode<T: for<'a> Deserialize<'a>>(key: &str, bytes: &[u8]) -> Result<T, MapError> {
    serde_json::from_slice(bytes).map_err(|e| MapError::Corrupt {
        key: key.to_string(),
        reason: e.to_string(),
    })
}

/// Storage for shards with compare-and-swap on content (the ticket branch implements it).
pub trait ShardStore {
    /// Reads the bytes of `key`, if present.
    fn get(&self, key: &str) -> Option<Vec<u8>>;
    /// Writes `bytes` only if the current content hash equals `expected` (None = absent).
    ///
    /// # Errors
    /// `MapError::Conflict` when the content hash differs from `expected`.
    fn put_if(&mut self, key: &str, expected: Option<&str>, bytes: Vec<u8>)
    -> Result<(), MapError>;
}

/// Reads and decodes the shard for `ulid`; `Ok(None)` when it is lost or never written.
///
/// # Errors
/// `MapError::Corrupt` when the stored bytes do not decode.
pub fn read_shard<S: ShardStore>(store: &S, ulid: &str) -> Result<Option<Shard>, MapError> {
    match store.get(ulid) {
        None => Ok(None),
        Some(bytes) => decode(ulid, &bytes).map(Some),
    }
}

/// Commits `shard` through CAS against what was last read; returns the new content hash.
///
/// # Errors
/// `MapError::Conflict` when another writer changed the shard first.
pub fn write_shard<S: ShardStore>(store: &mut S, shard: &Shard) -> Result<String, MapError> {
    let expected = store.get(&shard.ulid).map(|b| content_hash(&b));
    let bytes = encode(shard);
    let hash = content_hash(&bytes);
    store.put_if(&shard.ulid, expected.as_deref(), bytes)?;
    debug!(ulid = %shard.ulid, %hash, "mirror map shard committed");
    Ok(hash)
}

/// One bot issue seen in the tracker listing, with its valid marker's ULID.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ListedIssue {
    /// The ULID from the verified marker.
    pub ulid: String,
    /// Tracker issue number.
    pub number: u64,
    /// Tracker node id.
    pub node_id: String,
}

/// What the mirror may do for a ticket given the map and the tracker listing.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Resolution {
    /// The cached shard already names the issue.
    Known(Shard),
    /// The shard was lost; identity was re-found in the tracker (lowest number wins).
    Rebuilt(Shard),
    /// A create is uncertain: recovery must run first, no create allowed.
    Recover(Shard),
    /// No issue exists anywhere: a create is allowed.
    NeedsCreate,
}

/// Resolves a ticket's identity: the cache first, then the tracker listing, create last.
pub fn resolve(cached: Option<Shard>, listing: &[ListedIssue], ulid: &str) -> Resolution {
    if let Some(shard) = cached {
        if shard.issue_number.is_some() {
            return Resolution::Known(shard);
        }
        if shard.create_uncertain.is_some() && !listing.iter().any(|i| i.ulid == ulid) {
            warn!(
                ulid,
                "create outcome unknown; recovery required before any create"
            );
            return Resolution::Recover(shard);
        }
    }
    match listing
        .iter()
        .filter(|i| i.ulid == ulid)
        .min_by_key(|i| i.number)
    {
        Some(found) => {
            info!(
                ulid,
                number = found.number,
                "map entry rebuilt from tracker listing"
            );
            let mut shard = Shard::new(ulid);
            shard.issue_number = Some(found.number);
            shard.node_id = Some(found.node_id.clone());
            Resolution::Rebuilt(shard)
        }
        None => Resolution::NeedsCreate,
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

    // frob:tests write_shard
    // frob:tests read_shard
    // frob:tests encode
    #[test]
    fn published_shard_round_trips() {
        let mut shard = Shard::new("01ULID");
        shard.issue_number = Some(42);
        shard.node_id = Some("I_node".into());
        shard.last_event = Some("abc123".into());
        shard.history_cursor = Some("evt-9".into());
        shard.observed.insert("title".into(), "T".into());
        let mut store = Mem::default();
        let hash = write_shard(&mut store, &shard).unwrap();
        assert_eq!(hash, content_hash(&store.get("01ULID").unwrap()));
        assert_eq!(read_shard(&store, "01ULID").unwrap(), Some(shard));
    }

    // frob:tests write_shard
    #[test]
    fn stale_cas_is_rejected() {
        let mut store = Mem::default();
        store.0.insert("U".into(), b"{}".to_vec());
        let err = store.put_if("U", None, vec![]).unwrap_err();
        assert!(matches!(err, MapError::Conflict { .. }));
    }

    // frob:tests decode
    #[test]
    fn corrupt_shard_is_typed_error() {
        let r: Result<Shard, _> = decode("U", b"nope");
        assert!(matches!(r, Err(MapError::Corrupt { .. })));
    }

    // frob:tests resolve
    #[test]
    fn lost_map_refinds_by_ulid_without_create() {
        let listing = vec![
            ListedIssue {
                ulid: "U".into(),
                number: 9,
                node_id: "n9".into(),
            },
            ListedIssue {
                ulid: "U".into(),
                number: 5,
                node_id: "n5".into(),
            },
        ];
        match resolve(None, &listing, "U") {
            Resolution::Rebuilt(s) => assert_eq!(s.issue_number, Some(5)),
            other => panic!("expected rebuild, got {other:?}"),
        }
        assert_eq!(resolve(None, &[], "U"), Resolution::NeedsCreate);
    }

    // frob:tests resolve
    #[test]
    fn uncertain_create_blocks_new_create() {
        let mut shard = Shard::new("U");
        shard.create_uncertain = Some(CreateUncertain {
            nonce: "n".into(),
            started: "t".into(),
        });
        assert!(matches!(
            resolve(Some(shard), &[], "U"),
            Resolution::Recover(_)
        ));
    }
}
