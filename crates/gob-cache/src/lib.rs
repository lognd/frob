//! SQLite cache, one per repository (architecture.md sections 3 and 9, D30, ~TSK0M4Y).
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
#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]

use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};
use std::time::Duration;

use rusqlite::{Connection, OptionalExtension, TransactionBehavior, params};

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
            busy_timeout: Duration::from_secs(5),
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
    clock: std::sync::Arc<dyn gob_time::Clock>,
}

/// Environment variable that, when set to a non-empty value, folds the executable's digest into the engine.
///
/// For rule development: an edited rule whose `version` was not bumped then cannot reuse
/// results cached by an older build.
pub const EXE_IDENTITY_ENV: &str = "FROB_CACHE_EXE_IDENTITY";

/// The engine string for crate `version`, with the executable digest `exe_id` only when strict identity is on.
// frob:ticket 01M4MGNX1RJNX032GWZ1NN2YCK
fn engine_string(version: &str, exe_id: Option<&str>) -> String {
    match exe_id {
        Some(id) => format!("gob-cache/{version}/exe:{id}"),
        None => format!("gob-cache/{version}"),
    }
}

/// The default engine fingerprint of the running binary: the crate version, plus the executable digest on opt-in.
///
/// Every rule result is already keyed by file digest, rule id and rule version, and
/// callers add their extractor version, so the fingerprint need not change on each
/// rebuild. Keying on the executable's bytes made every build of the shared target
/// dir (any worker, any source edit) start with a cold cache: 30k stale rows per
/// build and a 23 percent hit rate. Set [`EXE_IDENTITY_ENV`] to restore per-build
/// scoping while editing rules.
// frob:ticket 01M4MGNX1RJNX032GWZ1NN2YCK
pub fn default_engine() -> &'static str {
    static ENGINE: OnceLock<String> = OnceLock::new();
    ENGINE.get_or_init(|| {
        let strict = std::env::var_os(EXE_IDENTITY_ENV).is_some_and(|v| !v.is_empty());
        let id = strict.then(|| {
            std::env::current_exe()
                .and_then(|exe| exe_digest(&exe))
                .unwrap_or_else(|e| {
                    tracing::warn!(error = %e, "executable unreadable; engine fingerprint is unknown");
                    "unknown".to_owned()
                })
        });
        let engine = engine_string(env!("CARGO_PKG_VERSION"), id.as_deref());
        tracing::debug!(%engine, "default engine fingerprint");
        engine
    })
}

/// The hex blake3 digest of the file at `path`, streamed so a large debug binary is never held in memory.
// frob:ticket 01M4GS7C37A8JVNEBMJEWJGM32
fn exe_digest(path: &Path) -> std::io::Result<String> {
    let started = std::time::Instant::now();
    let mut hasher = blake3::Hasher::new();
    hasher.update_reader(std::fs::File::open(path)?)?;
    let digest = hasher.finalize().to_hex().to_string();
    tracing::debug!(path = %path.display(), elapsed_ms = started.elapsed().as_millis(), "hashed executable");
    Ok(digest)
}

/// The clock a cache uses until [`Cache::with_clock`] replaces it: rows are dated, never compared across runs.
fn default_clock() -> std::sync::Arc<dyn gob_time::Clock> {
    std::sync::Arc::new(gob_time::SystemClock)
}

/// Folds `engine` into a stored key so two engines never share a row.
fn scoped(engine: &str, key: &str) -> String {
    format!("{engine}|{key}")
}

// frob:ticket 01M42B6T28RX9PVM3X6TSK0M4Y
fn migrate(conn: &mut Connection) -> rusqlite::Result<()> {
    // One writer at a time: the version table is created and read inside the write
    // transaction, so two processes opening a fresh shared cache cannot both run the same
    // migration or collide on the table creation.
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    tx.execute_batch("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);")?;
    let current: Option<i64> =
        tx.query_row("SELECT MAX(version) FROM schema_version", [], |r| r.get(0))?;
    let current = usize::try_from(current.unwrap_or(0)).unwrap_or(0);
    for (i, sql) in MIGRATIONS.iter().enumerate().skip(current) {
        tx.execute_batch(sql)?;
        tx.execute("DELETE FROM schema_version", [])?;
        tx.execute("INSERT INTO schema_version(version) VALUES (?1)", [i + 1])?;
        tracing::info!(from = i, to = i + 1, "cache schema migrated");
    }
    tx.commit()
}

/// Retries `op` while SQLite reports BUSY/LOCKED, up to `timeout`.
///
/// Switching a fresh database to WAL fails with BUSY without consulting the busy handler when
/// a peer is mid-switch, so `busy_timeout` alone does not cover a concurrent first open.
// frob:ticket 01M42G1XH9FARCHDA7KCE69AVN
fn retry_busy<T>(
    timeout: Duration,
    mut op: impl FnMut() -> rusqlite::Result<T>,
) -> rusqlite::Result<T> {
    let start = std::time::Instant::now();
    loop {
        match op() {
            Err(rusqlite::Error::SqliteFailure(e, _))
                if matches!(
                    e.code,
                    rusqlite::ErrorCode::DatabaseBusy | rusqlite::ErrorCode::DatabaseLocked
                ) && start.elapsed() < timeout =>
            {
                tracing::debug!("cache database busy; retrying");
                std::thread::sleep(Duration::from_millis(5));
            }
            other => return other,
        }
    }
}

// frob:ticket 01M41ZSWGC86TY3K0NSA8AMNGF
fn open_conn(dir: &Path, config: CacheConfig) -> Result<Connection, String> {
    std::fs::create_dir_all(dir).map_err(|e| format!("create dir: {e}"))?;
    let mut conn = Connection::open(dir.join(DB_FILE)).map_err(|e| format!("open: {e}"))?;
    conn.busy_timeout(config.busy_timeout)
        .map_err(|e| format!("busy_timeout: {e}"))?;
    retry_busy(config.busy_timeout, || {
        conn.pragma_update(None, "journal_mode", "WAL")
    })
    .map_err(|e| format!("wal: {e}"))?;
    // The cache is regenerable, and in WAL mode NORMAL only risks the last commits on power loss:
    // FULL would fsync every one of the thousands of per-file puts of a cold run.
    conn.pragma_update(None, "synchronous", "NORMAL")
        .map_err(|e| format!("synchronous: {e}"))?;
    migrate(&mut conn).map_err(|e| format!("migrate: {e}"))?;
    Ok(conn)
}

/// Directory under the git common dir that holds frob's per-repository state.
pub const SHARED_DIR: &str = "frob";

// frob:ticket 01M4M52WKHGXADHPQ08J1AS8BJ
pub use gob_fs::git_common_dir;

/// The repository-wide cache directory for the state directory `state_dir` (for example `.frob`) of `root`.
///
/// It lives under the git common dir, so the primary checkout, every ticket worktree and the
/// land ratchet's base worktree share one cache; keys are content digests, so sharing is safe.
/// `None` outside a git checkout, where the caller keeps its per-checkout directory.
pub fn shared_dir(root: &Path, state_dir: &str) -> Option<PathBuf> {
    let name = state_dir.trim_matches(|c| c == '.' || c == '/');
    Some(
        git_common_dir(root)?
            .join(SHARED_DIR)
            .join("cache")
            .join(name),
    )
}

/// What [`seed_shared`] did.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Seeded {
    /// The shared cache already exists; nothing was copied.
    AlreadyShared,
    /// No shared location (not a git checkout) or no per-checkout cache to copy.
    NothingToSeed,
    /// The per-checkout cache of the primary was snapshotted into the shared location.
    Copied,
    /// The copy failed (logged at warn); the shared cache starts empty.
    Failed,
}

/// Seeds the repository-shared cache for `state_dir` from the primary checkout's own `<primary>/<state_dir>/cache.sqlite`.
///
/// A repository warmed before cache sharing (or by a per-checkout run) keeps its rows in the
/// primary's directory; a new worktree would otherwise start from an empty shared cache and
/// analyse every file cold. The snapshot is a consistent `VACUUM INTO` a temporary file renamed
/// into place, so a concurrent opener never sees a partial database. An existing shared cache wins.
// frob:ticket 01M4DPJJW8D3KXZVTEN5D4WN5G
pub fn seed_shared(primary: &Path, state_dir: &str) -> Seeded {
    let Some(dest_dir) = shared_dir(primary, state_dir) else {
        tracing::debug!(primary = %primary.display(), "no shared cache location; nothing to seed");
        return Seeded::NothingToSeed;
    };
    let dest = dest_dir.join(DB_FILE);
    if dest.exists() {
        tracing::debug!(dest = %dest.display(), "shared cache present; not seeding");
        return Seeded::AlreadyShared;
    }
    let src = primary.join(state_dir).join(DB_FILE);
    if !src.is_file() {
        tracing::debug!(src = %src.display(), "no per-checkout cache to seed from");
        return Seeded::NothingToSeed;
    }
    let started = std::time::Instant::now();
    let tmp = dest_dir.join(format!("{DB_FILE}.seed-{}", std::process::id()));
    let result = std::fs::create_dir_all(&dest_dir)
        .map_err(|e| format!("create dir: {e}"))
        .and_then(|()| {
            let _ = std::fs::remove_file(&tmp);
            Connection::open_with_flags(&src, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
                .map_err(|e| format!("open source: {e}"))
        })
        .and_then(|conn| {
            conn.busy_timeout(CacheConfig::default().busy_timeout)
                .map_err(|e| format!("busy timeout: {e}"))?;
            conn.execute("VACUUM INTO ?1", [tmp.to_string_lossy().as_ref()])
                .map_err(|e| format!("snapshot: {e}"))
        })
        .and_then(|_| {
            // hard_link fails when a racing seeder won, which is the desired "existing wins".
            let linked = std::fs::hard_link(&tmp, &dest);
            let _ = std::fs::remove_file(&tmp);
            linked.map_err(|e| format!("install: {e}"))
        });
    match result {
        Ok(()) => {
            tracing::info!(src = %src.display(), dest = %dest.display(), elapsed_ms = started.elapsed().as_millis(), "shared cache seeded from the primary");
            Seeded::Copied
        }
        Err(err) if dest.exists() => {
            tracing::debug!(%err, "lost the seeding race; shared cache present");
            Seeded::AlreadyShared
        }
        Err(err) => {
            tracing::warn!(src = %src.display(), %err, "shared cache not seeded; it starts empty");
            let _ = std::fs::remove_file(&tmp);
            Seeded::Failed
        }
    }
}

impl Cache {
    /// Opens the repository-shared cache for `root`'s `state_dir`, else `<root>/<state_dir>`.
    pub fn open_shared(root: &Path, state_dir: &str) -> Self {
        match shared_dir(root, state_dir) {
            Some(dir) => {
                tracing::debug!(dir = %dir.display(), "shared cache selected");
                Self::open(&dir)
            }
            None => Self::open(&root.join(state_dir)),
        }
    }

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
                    clock: default_clock(),
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
            clock: default_clock(),
        }
    }

    /// Replaces the clock that dates stored rows (the command's clock; the system clock otherwise).
    #[must_use]
    pub fn with_clock(mut self, clock: std::sync::Arc<dyn gob_time::Clock>) -> Self {
        self.clock = clock;
        self
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
                params![
                    key.row_key(),
                    key.producer_identity,
                    bytes,
                    self.clock.now().unix()
                ],
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

    // frob:tests exe_digest
    // frob:ticket 01M4GS7C37A8JVNEBMJEWJGM32
    #[test]
    fn engine_is_build_independent_unless_strict() {
        let lax = engine_string("1.2.3", None);
        assert_eq!(lax, "gob-cache/1.2.3");
        // Two builds with different bytes share the lax engine and split the strict one.
        assert_ne!(
            engine_string("1.2.3", Some("aa")),
            engine_string("1.2.3", Some("bb"))
        );
        assert_ne!(lax, engine_string("1.2.4", None));
        // The lax default is what an unconfigured process uses.
        if std::env::var_os(EXE_IDENTITY_ENV).is_none() {
            assert_eq!(
                default_engine(),
                engine_string(env!("CARGO_PKG_VERSION"), None)
            );
        }
    }

    #[test]
    fn exe_digest_follows_content_not_path_or_mtime() {
        let dir = tempfile::tempdir().unwrap();
        let a = dir.path().join("a");
        let b = dir.path().join("b");
        std::fs::write(&a, b"build one").unwrap();
        let first = exe_digest(&a).unwrap();
        // Same bytes at a new path written later (new mtime): same build identity.
        std::thread::sleep(Duration::from_millis(20));
        std::fs::copy(&a, &b).unwrap();
        assert_eq!(exe_digest(&b).unwrap(), first);
        // Different bytes, even of the same length: a different build.
        std::fs::write(&b, b"build two").unwrap();
        assert_ne!(exe_digest(&b).unwrap(), first);
        assert!(exe_digest(&dir.path().join("missing")).is_err());
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
