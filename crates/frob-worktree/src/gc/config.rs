//! The `[gc]` config table.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};

/// Bytes in a gibibyte, the unit of the size knobs.
pub const GIB: u64 = 1 << 30;
/// Bytes in a mebibyte.
pub const MIB: u64 = 1 << 20;

/// Garbage-collection settings: what the throttled pass may reclaim and how much to keep.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "gc", materialize)]
pub struct GcConfig {
    /// Run the automatic pass at all; `frob doctor --fix` still runs it on request.
    #[config(default = true)]
    pub enabled: bool,
    /// Minimum seconds between automatic passes (the stamp lives under the git common dir).
    #[config(default = 3600)]
    pub interval_secs: u64,
    /// Wall-clock bound in seconds of one pass; the rest waits for the next one.
    #[config(default = 30)]
    pub time_limit_secs: u64,
    /// Free GiB below which a pass runs regardless of the interval; 0 turns the guard off.
    #[config(default = 20)]
    pub guard_min_free_gb: u64,
    /// Remove build incremental directories not used within this many seconds.
    #[config(default = 21600)]
    pub incremental_max_age_secs: u64,
    /// Per-checkout build-output budget in GiB; the oldest artifacts are evicted past it.
    #[config(default = 30)]
    pub target_budget_gb: u64,
    /// Artifacts within this many seconds of the newest one belong to the latest build and are kept.
    #[config(default = 3600)]
    pub keep_recent_secs: u64,
    /// Binary names (without extension) whose build output is never collected.
    #[config(default = vec!["frob".to_owned(), "grimble".to_owned()])]
    pub keep_binaries: Vec<String>,
    /// Budget in MiB of the regenerable caches under each checkout's `.frob/`.
    #[config(default = 256)]
    pub cache_budget_mb: u64,
    /// Evidence blobs under `.git/frob/artifacts` older than this many days and unreferenced by an open ticket are removed.
    #[config(default = 30)]
    pub artifact_retention_days: u64,
    /// Remove worktrees of closed tickets and of expired leases with nothing unsaved.
    #[config(default = true)]
    pub worktrees: bool,
}

impl GcConfig {
    /// Load `[gc]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, "frob")?.value)
    }
}
