//! Per-worktree SQLite cache (architecture.md section 3, D30).
//!
//! Stores parse artifacts keyed by (content digest, producer identity),
//! per-file findings keyed by (file digest, rule id, rule version,
//! side-input digest) and repo-scope findings keyed by (graph digest, rule
//! id). Findings and repo-scope rows are additionally scoped by an engine
//! fingerprint (see [`default_engine`] and [`Cache::with_engine`]): a result
//! computed by another binary is a miss, never a stale hit. Payloads are opaque bytes; serialization is the caller's concern.
//! Writes are best-effort: a failure is logged at warn and never surfaces.
//! When the database cannot be opened the cache degrades to a null cache
//! where every read misses and every write is a no-op.

use std::path::Path;
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use rusqlite::{Connection, OptionalExtension, params};

/// File name of the database inside the cache directory.
pub const DB_FILE: &str = "cache.sqlite";

/// Forward-only migrations; index `i` upgrades schema version `i` to `i + 1`.
const MIGRATIONS: &[&str] = &["
    CREATE TABLE artifacts(
        key TEXT PRIMARY KEY,
        producer TEXT NOT NULL,
        bytes BLOB NOT NULL,
        created_at INTEGER NOT NULL
    );
    CREATE TABLE findings(
        file_digest TEXT NOT NULL,
        rule_id TEXT NOT NULL,
        rule_version INTEGER NOT NULL,
        side_input_digest TEXT NOT NULL,
        payload BLOB NOT NULL,
        PRIMARY KEY (file_digest, rule_id, rule_version, side_input_digest)
    );
    CREATE TABLE repo_rule(
        graph_digest TEXT NOT NULL,
        rule_id TEXT NOT NULL,
        payload BLOB NOT NULL,
        PRIMARY KEY (graph_digest, rule_id)
    );
"];

/// Cache knobs.
#[derive(Clone, Copy, Debug)]
pub struct CacheConfig {
    /// How long a connection waits on a locked database.
    pub busy_timeout: Duration,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            busy_timeout: Duration::from_millis(500),
        }
    }
}

/// Key of a parse artifact.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct ArtifactKey {
    /// Hex blake3 digest of the source content.
    pub content_digest: String,
    /// Producer identity, e.g. adapter id plus schema version.
    pub producer_identity: String,
}

impl ArtifactKey {
    fn row_key(&self) -> String {
        format!("{}:{}", self.content_digest, self.producer_identity)
    }
}

/// Key of a per-file findings entry.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct FindingsKey {
    /// Hex blake3 digest of the file.
    pub file_digest: String,
    /// Rule id.
    pub rule_id: String,
    /// Rule version.
    pub rule_version: u32,
    /// Digest of the rule's side inputs (config, etc.).
    pub side_input_digest: String,
}

/// Row counts for `frob doctor`.
#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub struct CacheStats {
    /// True when the cache is the null fallback.
    pub null: bool,
    /// Rows in `artifacts`.
    pub artifacts: u64,
    /// Rows in `findings`.
    pub findings: u64,
    /// Rows in `repo_rule`.
    pub repo_rule: u64,
}

/// The cache handle; real or null, with one API.
pub struct Cache {
    conn: Option<Mutex<Connection>>,
    engine: String,
}

/// The default engine fingerprint of the running binary: crate version plus the executable's size and mtime.
///
/// A rebuilt binary (upgrade, worktree build, any source edit) differs in
/// size or mtime, so results cached by another build are misses. Measured
/// at runtime from the executable's metadata (no build script, so editing a
/// low-level crate does not force a rebuild of everything above it); when
/// the metadata is unreadable the fingerprint is `unknown` and still scoped
/// by the crate version.
pub fn default_engine() -> &'static str {
    static ENGINE: OnceLock<String> = OnceLock::new();
    ENGINE.get_or_init(|| {
        let id = std::env::current_exe()
            .and_then(std::fs::metadata)
            .ok()
            .map_or_else(
                || "unknown".to_owned(),
                |m| {
                    let ns = m
                        .modified()
                        .ok()
                        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                        .map_or(0, |d| d.as_nanos());
                    format!("{}-{ns}", m.len())
                },
            );
        let engine = format!("gob-cache/{}/exe:{id}", env!("CARGO_PKG_VERSION"));
        tracing::debug!(%engine, "default engine fingerprint");
        engine
    })
}

/// Folds `engine` into a stored key so two engines never share a row.
fn scoped(engine: &str, key: &str) -> String {
    format!("{engine}|{key}")
}

fn now_secs() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

fn migrate(conn: &mut Connection) -> rusqlite::Result<()> {
    conn.execute_batch("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);")?;
    let current: Option<i64> =
        conn.query_row("SELECT MAX(version) FROM schema_version", [], |r| r.get(0))?;
    let current = usize::try_from(current.unwrap_or(0)).unwrap_or(0);
    for (i, sql) in MIGRATIONS.iter().enumerate().skip(current) {
        let tx = conn.transaction()?;
        tx.execute_batch(sql)?;
        tx.execute("DELETE FROM schema_version", [])?;
        tx.execute("INSERT INTO schema_version(version) VALUES (?1)", [i + 1])?;
        tx.commit()?;
        tracing::info!(from = i, to = i + 1, "cache schema migrated");
    }
    Ok(())
}

// frob:ticket 01M41ZSWGC86TY3K0NSA8AMNGF
fn open_conn(dir: &Path, config: CacheConfig) -> Result<Connection, String> {
    std::fs::create_dir_all(dir).map_err(|e| format!("create dir: {e}"))?;
    let mut conn = Connection::open(dir.join(DB_FILE)).map_err(|e| format!("open: {e}"))?;
    conn.busy_timeout(config.busy_timeout)
        .map_err(|e| format!("busy_timeout: {e}"))?;
    conn.pragma_update(None, "journal_mode", "WAL")
        .map_err(|e| format!("wal: {e}"))?;
    // The cache is regenerable, and in WAL mode NORMAL only risks the last commits on power loss:
    // FULL would fsync every one of the thousands of per-file puts of a cold run.
    conn.pragma_update(None, "synchronous", "NORMAL")
        .map_err(|e| format!("synchronous: {e}"))?;
    migrate(&mut conn).map_err(|e| format!("migrate: {e}"))?;
    Ok(conn)
}

impl Cache {
    /// Opens `<dir>/cache.sqlite`, falling back to a null cache on any failure.
    pub fn open(dir: &Path) -> Self {
        Self::open_with(dir, CacheConfig::default())
    }

    /// Like [`Cache::open`] with explicit knobs.
    pub fn open_with(dir: &Path, config: CacheConfig) -> Self {
        match open_conn(dir, config) {
            Ok(conn) => {
                tracing::debug!(dir = %dir.display(), "cache opened");
                Self {
                    conn: Some(Mutex::new(conn)),
                    engine: default_engine().to_owned(),
                }
            }
            Err(err) => {
                tracing::warn!(dir = %dir.display(), %err, "cache unavailable; using null cache");
                Self::null()
            }
        }
    }

    /// Returns a cache whose reads all miss and whose writes are no-ops.
    pub fn null() -> Self {
        Self {
            conn: None,
            engine: default_engine().to_owned(),
        }
    }

    /// Replaces the engine fingerprint that scopes findings and repo-rule rows.
    #[must_use]
    pub fn with_engine(mut self, engine: impl Into<String>) -> Self {
        self.engine = engine.into();
        tracing::debug!(engine = %self.engine, "cache engine set");
        self
    }

    /// The engine fingerprint scoping findings and repo-rule rows.
    pub fn engine(&self) -> &str {
        &self.engine
    }

    /// True when this is the null fallback.
    pub fn is_null(&self) -> bool {
        self.conn.is_none()
    }

    fn with<T>(&self, op: &str, f: impl FnOnce(&Connection) -> rusqlite::Result<T>) -> Option<T> {
        let conn = self.conn.as_ref()?;
        let guard = conn
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        match f(&guard) {
            Ok(v) => Some(v),
            Err(err) => {
                tracing::warn!(op, %err, "cache operation failed");
                None
            }
        }
    }

    /// Looks up an artifact; any failure reads as a miss.
    pub fn get_artifact(&self, key: &ArtifactKey) -> Option<Vec<u8>> {
        self.with("get_artifact", |c| {
            c.query_row(
                "SELECT bytes FROM artifacts WHERE key = ?1",
                [key.row_key()],
                |r| r.get(0),
            )
            .optional()
        })
        .flatten()
    }

    /// Stores an artifact, best-effort.
    pub fn put_artifact(&self, key: &ArtifactKey, bytes: &[u8]) {
        let done = self.with("put_artifact", |c| {
            c.execute(
                "INSERT OR REPLACE INTO artifacts(key, producer, bytes, created_at)
                 VALUES (?1, ?2, ?3, ?4)",
                params![key.row_key(), key.producer_identity, bytes, now_secs()],
            )
        });
        if done.is_some() {
            tracing::debug!(key = key.row_key(), len = bytes.len(), "artifact stored");
        }
    }

    /// Looks up per-file findings; any failure reads as a miss.
    pub fn get_findings(&self, key: &FindingsKey) -> Option<Vec<u8>> {
        self.with("get_findings", |c| {
            c.query_row(
                "SELECT payload FROM findings WHERE file_digest = ?1 AND rule_id = ?2
                 AND rule_version = ?3 AND side_input_digest = ?4",
                params![
                    key.file_digest,
                    key.rule_id,
                    key.rule_version,
                    scoped(&self.engine, &key.side_input_digest)
                ],
                |r| r.get(0),
            )
            .optional()
        })
        .flatten()
    }

    /// Stores per-file findings, best-effort.
    pub fn put_findings(&self, key: &FindingsKey, payload: &[u8]) {
        let done = self.with("put_findings", |c| {
            c.execute(
                "INSERT OR REPLACE INTO findings(file_digest, rule_id, rule_version,
                 side_input_digest, payload) VALUES (?1, ?2, ?3, ?4, ?5)",
                params![
                    key.file_digest,
                    key.rule_id,
                    key.rule_version,
                    scoped(&self.engine, &key.side_input_digest),
                    payload
                ],
            )
        });
        if done.is_some() {
            tracing::debug!(rule = key.rule_id, len = payload.len(), "findings stored");
        }
    }

    /// Looks up repo-scope findings; any failure reads as a miss.
    pub fn get_repo_rule(&self, graph_digest: &str, rule_id: &str) -> Option<Vec<u8>> {
        self.with("get_repo_rule", |c| {
            c.query_row(
                "SELECT payload FROM repo_rule WHERE graph_digest = ?1 AND rule_id = ?2",
                params![scoped(&self.engine, graph_digest), rule_id],
                |r| r.get(0),
            )
            .optional()
        })
        .flatten()
    }

    /// Stores repo-scope findings, best-effort.
    pub fn put_repo_rule(&self, graph_digest: &str, rule_id: &str, payload: &[u8]) {
        let done = self.with("put_repo_rule", |c| {
            c.execute(
                "INSERT OR REPLACE INTO repo_rule(graph_digest, rule_id, payload)
                 VALUES (?1, ?2, ?3)",
                params![scoped(&self.engine, graph_digest), rule_id, payload],
            )
        });
        if done.is_some() {
            tracing::debug!(rule = rule_id, len = payload.len(), "repo rule stored");
        }
    }

    /// Row counts per table (zeros and `null = true` for the null cache).
    pub fn stats(&self) -> CacheStats {
        let count = |c: &Connection, t: &str| -> rusqlite::Result<u64> {
            c.query_row(&format!("SELECT COUNT(*) FROM {t}"), [], |r| r.get(0))
        };
        self.with("stats", |c| {
            Ok(CacheStats {
                null: false,
                artifacts: count(c, "artifacts")?,
                findings: count(c, "findings")?,
                repo_rule: count(c, "repo_rule")?,
            })
        })
        .unwrap_or(CacheStats {
            null: true,
            ..CacheStats::default()
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fkey() -> FindingsKey {
        FindingsKey {
            file_digest: "d".into(),
            rule_id: "R1".into(),
            rule_version: 1,
            side_input_digest: "s".into(),
        }
    }

    #[test]
    fn findings_miss_when_any_key_part_changes() {
        let dir = tempfile::tempdir().unwrap();
        let cache = Cache::open(dir.path());
        assert!(!cache.is_null());
        let k = fkey();
        cache.put_findings(&k, b"payload");
        assert_eq!(cache.get_findings(&k).as_deref(), Some(&b"payload"[..]));
        let variants = [
            FindingsKey {
                file_digest: "d2".into(),
                ..k.clone()
            },
            FindingsKey {
                rule_id: "R2".into(),
                ..k.clone()
            },
            FindingsKey {
                rule_version: 2,
                ..k.clone()
            },
            FindingsKey {
                side_input_digest: "s2".into(),
                ..k.clone()
            },
        ];
        for v in variants {
            assert!(cache.get_findings(&v).is_none(), "{v:?}");
        }
    }

    #[test]
    fn artifacts_and_repo_rules_round_trip() {
        let dir = tempfile::tempdir().unwrap();
        let cache = Cache::open(dir.path());
        let k = ArtifactKey {
            content_digest: "c".into(),
            producer_identity: "p1".into(),
        };
        cache.put_artifact(&k, b"ast");
        assert_eq!(cache.get_artifact(&k).as_deref(), Some(&b"ast"[..]));
        let other = ArtifactKey {
            producer_identity: "p2".into(),
            ..k.clone()
        };
        assert!(cache.get_artifact(&other).is_none());
        cache.put_repo_rule("g", "R", b"x");
        assert!(cache.get_repo_rule("g", "R").is_some());
        assert!(cache.get_repo_rule("g2", "R").is_none());
        let s = cache.stats();
        assert_eq!(
            (s.null, s.artifacts, s.findings, s.repo_rule),
            (false, 1, 0, 1)
        );
    }

    #[test]
    fn engines_never_share_findings_or_repo_rules() {
        let dir = tempfile::tempdir().unwrap();
        let a = Cache::open(dir.path()).with_engine("engine-a");
        a.put_findings(&fkey(), b"from-a");
        a.put_repo_rule("g", "R", b"from-a");
        let b = Cache::open(dir.path()).with_engine("engine-b");
        assert!(b.get_findings(&fkey()).is_none());
        assert!(b.get_repo_rule("g", "R").is_none());
        b.put_findings(&fkey(), b"from-b");
        b.put_repo_rule("g", "R", b"from-b");
        // The same fingerprint still hits, and each engine sees its own result.
        let a2 = Cache::open(dir.path()).with_engine("engine-a");
        assert_eq!(a2.get_findings(&fkey()).as_deref(), Some(&b"from-a"[..]));
        assert_eq!(a2.get_repo_rule("g", "R").as_deref(), Some(&b"from-a"[..]));
        assert_eq!(b.get_findings(&fkey()).as_deref(), Some(&b"from-b"[..]));
        assert_eq!(b.get_repo_rule("g", "R").as_deref(), Some(&b"from-b"[..]));
    }

    #[test]
    fn persists_across_reopen() {
        let dir = tempfile::tempdir().unwrap();
        Cache::open(dir.path()).put_findings(&fkey(), b"p");
        assert!(Cache::open(dir.path()).get_findings(&fkey()).is_some());
    }

    #[test]
    fn null_cache_when_dir_is_a_file() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("not-a-dir");
        std::fs::write(&file, "x").unwrap();
        let cache = Cache::open(&file);
        assert!(cache.is_null());
        cache.put_findings(&fkey(), b"p");
        assert!(cache.get_findings(&fkey()).is_none());
        assert!(cache.stats().null);
    }

    #[test]
    fn migrates_from_empty_db() {
        let dir = tempfile::tempdir().unwrap();
        // An existing but empty database file (no tables at all).
        Connection::open(dir.path().join(DB_FILE)).unwrap();
        let cache = Cache::open(dir.path());
        assert!(!cache.is_null());
        cache.put_repo_rule("g", "R", b"x");
        let v: i64 = cache
            .with("v", |c| {
                c.query_row("SELECT MAX(version) FROM schema_version", [], |r| r.get(0))
            })
            .unwrap();
        assert_eq!(usize::try_from(v).unwrap(), MIGRATIONS.len());
    }
}
