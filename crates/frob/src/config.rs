//! The `frob.toml` tables the M1 verbs need.

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::PRODUCT;

/// Severity at which `frob check` fails (cli.md section 2, exit 1).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum FailOn {
    /// Never fail on findings.
    None,
    /// Fail on advisory findings and above.
    Advisory,
    /// Fail on warnings and above.
    Warn,
    /// Fail on errors only.
    Error,
}

/// Where the ticket ledger lives.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "tickets", materialize)]
pub struct TicketsTable {
    /// Ref holding the ledger; the ledger merge driver and `doctor` resolve it.
    #[config(default = "refs/heads/main".to_owned(), enforcement)]
    pub r#ref: String,
    /// Directory of ticket files, relative to the repository root.
    #[config(default = "tickets".to_owned())]
    pub dir: String,
}

/// Settings of `frob check`.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "check", materialize)]
pub struct CheckTable {
    /// Lowest severity that makes `frob check` exit 1; `none` never fails.
    #[config(default = FailOn::Error, enforcement)]
    pub fail_on: FailOn,
    /// Glob patterns of paths no rule inspects.
    #[config(default = Vec::new())]
    pub exclude: Vec<String>,
    /// Files larger than this many bytes are skipped.
    #[config(default = 4_194_304)]
    pub size_cap: u64,
}

/// Settings of the per-worktree cache.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "cache")]
pub struct CacheTable {
    /// Milliseconds a connection waits on a locked cache database.
    #[config(default = 500)]
    pub busy_timeout_ms: u64,
}

/// Settings of in-process git access.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "git", materialize)]
pub struct GitTable {
    /// Compare-and-swap retries when moving a ledger ref.
    #[config(default = 5, enforcement)]
    pub cas_retries: u32,
}

/// Every table above, loaded and validated from one `frob.toml`.
#[derive(Debug, Clone, Default)]
pub struct FrobConfig {
    /// `[tickets]`.
    pub tickets: TicketsTable,
    /// `[check]`.
    pub check: CheckTable,
    /// `[cache]`.
    pub cache: CacheTable,
    /// `[git]`.
    pub git: GitTable,
}

impl FrobConfig {
    /// Load all four tables from `<root>/frob.toml` (a missing file is defaults).
    ///
    /// # Errors
    ///
    /// The first [`ConfigError`] from any table: unreadable file, bad TOML,
    /// unknown key (with a suggestion) or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        let cfg = Self {
            tickets: gob_config::load::<TicketsTable>(root, PRODUCT)?.value,
            check: gob_config::load::<CheckTable>(root, PRODUCT)?.value,
            cache: gob_config::load::<CacheTable>(root, PRODUCT)?.value,
            git: gob_config::load::<GitTable>(root, PRODUCT)?.value,
        };
        tracing::debug!(root = %root.display(), "frob config loaded");
        Ok(cfg)
    }
}
