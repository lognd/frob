//! The `frob.toml` tables the M1 verbs need.

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::PRODUCT;

/// `[check]` and `[perf]` are owned by `frob-check`; re-exported for callers of this crate.
pub use frob_check::{CheckTable, FailOn, PerfTable};

/// Where ledger commits go (`[tickets] ref_mode`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum RefModeKnob {
    /// Commits advance the configured `ref`, whatever branch is checked out.
    Trunk,
    /// Commits go on the currently checked-out branch (protected trunk, forks).
    Branch,
}

impl From<RefModeKnob> for frob_ledger::RefMode {
    fn from(k: RefModeKnob) -> Self {
        match k {
            RefModeKnob::Trunk => Self::Trunk,
            RefModeKnob::Branch => Self::Branch,
        }
    }
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
    /// `trunk` commits to `ref`; `branch` commits to the checked-out branch.
    #[config(default = RefModeKnob::Trunk, enforcement)]
    pub ref_mode: RefModeKnob,
    /// Shortest ticket handle shown (`~` plus this many id characters).
    #[config(default = 7)]
    pub handle_min_len: u32,
    /// Actor recorded on events; empty means git `user.name`.
    #[config(default = String::new())]
    pub actor: String,
    /// Compatibility alias read from v1 `frob.toml`: append-shared files that
    /// extend `[lease] shared_files` (for example `Cargo.lock`).
    #[config(default = Vec::new())]
    pub registry_files: Vec<String>,
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
    /// `[check]`, owned by `frob-check`.
    pub check: CheckTable,
    /// `[perf]`, owned by `frob-check`.
    pub perf: PerfTable,
    /// `[cache]`.
    pub cache: CacheTable,
    /// `[git]`.
    pub git: GitTable,
    /// `[lease]`, owned by `frob-lease`.
    pub lease: frob_lease::LeaseConfig,
    /// `[worktree]`, owned by `frob-worktree`.
    pub worktree: frob_worktree::WorktreeConfig,
    /// `[evidence]`, owned by `frob-evidence`.
    pub evidence: frob_evidence::EvidenceTable,
}

impl FrobConfig {
    /// The ledger settings these tables imply.
    pub fn ledger(&self) -> frob_ledger::LedgerConfig {
        frob_ledger::LedgerConfig {
            ref_name: self.tickets.r#ref.clone(),
            mode: self.tickets.ref_mode.into(),
            dir: self.tickets.dir.clone(),
            cas_retries: self.git.cas_retries,
            handle_min_len: self.tickets.handle_min_len as usize,
            actor: (!self.tickets.actor.is_empty()).then(|| self.tickets.actor.clone()),
        }
    }

    /// The lease settings with the `[tickets] registry_files` alias folded
    /// into `shared_files` (duplicates dropped, file order kept).
    pub fn lease_config(&self) -> frob_lease::LeaseConfig {
        let mut cfg = self.lease.clone();
        for f in &self.tickets.registry_files {
            if !cfg.shared_files.contains(f) {
                cfg.shared_files.push(f.clone());
            }
        }
        cfg
    }

    /// Load every table from `<root>/frob.toml` (a missing file is defaults).
    ///
    /// # Errors
    ///
    /// The first [`ConfigError`] from any table: unreadable file, bad TOML,
    /// unknown key (with a suggestion) or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        let cfg = Self {
            tickets: gob_config::load::<TicketsTable>(root, PRODUCT)?.value,
            check: gob_config::load::<CheckTable>(root, PRODUCT)?.value,
            perf: gob_config::load::<PerfTable>(root, PRODUCT)?.value,
            cache: gob_config::load::<CacheTable>(root, PRODUCT)?.value,
            git: gob_config::load::<GitTable>(root, PRODUCT)?.value,
            lease: gob_config::load::<frob_lease::LeaseConfig>(root, PRODUCT)?.value,
            worktree: gob_config::load::<frob_worktree::WorktreeConfig>(root, PRODUCT)?.value,
            evidence: gob_config::load::<frob_evidence::EvidenceTable>(root, PRODUCT)?.value,
        };
        tracing::debug!(root = %root.display(), "frob config loaded");
        Ok(cfg)
    }
}

#[cfg(test)]
mod tests {
    use super::FrobConfig;

    #[test]
    fn registry_files_alias_extends_lease_shared_files_without_duplicates() {
        let mut cfg = FrobConfig::default();
        cfg.lease.shared_files = vec!["Cargo.lock".to_owned()];
        cfg.tickets.registry_files = vec!["Cargo.lock".to_owned(), "go.sum".to_owned()];
        assert_eq!(cfg.lease_config().shared_files, ["Cargo.lock", "go.sum"]);
    }
}
