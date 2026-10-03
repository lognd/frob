//! The `[lease]` config table: TTL, lock wait and shared files.

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};

/// The product whose `frob.toml` carries the table.
const PRODUCT: &str = "frob";

/// Knobs of the lease store (tickets.md section 6, decision D26).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "lease", materialize)]
pub struct LeaseConfig {
    /// Seconds a lease stays live after its last renewal (default two hours).
    #[config(default = 7200)]
    pub ttl_secs: u64,
    /// Milliseconds to wait for the lease lock before refusing with a timeout.
    #[config(default = 5000)]
    pub lock_timeout_ms: u64,
    /// Append-shared files (such as `Cargo.lock`) exempt from overlap checks.
    #[config(default = Vec::new())]
    pub shared_files: Vec<String>,
}

impl LeaseConfig {
    /// Load `[lease]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }
}
