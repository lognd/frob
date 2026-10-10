//! The `[lease]` config table: TTL, lock wait and shared files.

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};

/// The product whose `frob.toml` carries the table.
const PRODUCT: &str = "frob";

/// The well-known generated lockfiles exempt from overlap when `[lease] shared_files` is unset (frob:ticket 01M418TM2GZ24YPQE7ECTKE1J4).
pub const LOCKFILES: [&str; 10] = [
    "Cargo.lock",
    "uv.lock",
    "poetry.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "go.sum",
    "Gemfile.lock",
    "composer.lock",
    "flake.lock",
];

/// The default of `[lease] shared_files`: `**/<lockfile>` for each of [`LOCKFILES`], so any directory matches.
#[must_use]
pub fn default_shared_files() -> Vec<String> {
    LOCKFILES.iter().map(|n| format!("**/{n}")).collect()
}

/// True when `path` matches the default shared-file patterns (the very ones [`default_shared_files`] returns).
#[must_use]
pub fn is_lockfile(path: &str) -> bool {
    static SET: std::sync::OnceLock<globset::GlobSet> = std::sync::OnceLock::new();
    SET.get_or_init(|| {
        crate::overlap::glob_set(&default_shared_files())
            .unwrap_or_else(|e| unreachable!("default lockfile patterns are valid globs: {e}"))
    })
    .is_match(path)
}

/// True when every file in an overlap description (`a, b` or `a and b`) is a lockfile.
#[must_use]
pub fn overlap_is_lockfiles(overlap: &str) -> bool {
    let mut parts = overlap
        .split(", ")
        .flat_map(|p| p.split(" and "))
        .peekable();
    parts.peek().is_some() && parts.all(|p| is_lockfile(p.trim()))
}

// frob:ticket 01M4H6M6DYW002R049JG7AD7YA
/// Knobs of the lease store (tickets.md section 3, decision D26).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "lease", materialize)]
pub struct LeaseConfig {
    /// Seconds a lease stays live after its last renewal (default two hours).
    #[config(default = 7200)]
    pub ttl_secs: u64,
    /// Milliseconds to wait for the lease lock before refusing with a timeout.
    #[config(default = 5000)]
    pub lock_timeout_ms: u64,
    /// Append-shared files exempt from overlap checks; unset means the well-known lockfiles (`Cargo.lock`, `uv.lock`, ...), an explicit list (even `[]`) replaces them.
    #[config(default = default_shared_files())]
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
