//! The `frob.toml` tables the M1 verbs need.

use std::path::Path;

use gob_config::{ConfigDocument, ConfigError, ConfigTable};

/// `[tickets]` and `[git]` are owned by `frob-ledger`; re-exported for callers of this crate.
pub use frob_ledger::config::{GitTable, IndexWriterKnob, RefModeKnob, TicketsTable};

use crate::PRODUCT;

/// `[check]` and `[perf]` are owned by `frob-check`; re-exported for callers of this crate.
pub use frob_check::{CheckTable, FailOn, PerfTable};

/// Settings of the per-worktree cache.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "cache")]
pub struct CacheTable {
    /// Milliseconds a connection waits on a locked cache database.
    #[config(default = 500)]
    pub busy_timeout_ms: u64,
}

// frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ
/// The agent-neutral manifest `frob agent sync` publishes into each coding agent's home.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "agent")]
pub struct AgentTable {
    /// Canonical items, each `"KIND:NAME = SRC"` (kind: instruction, hook, agent, skill, support).
    #[config(default = Vec::<String>::new())]
    pub items: Vec<String>,
    /// Hook registrations, each `"NAME:EVENT:MATCHER"` naming a `hook` item.
    #[config(default = Vec::<String>::new())]
    pub hooks: Vec<String>,
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
    /// `[types]`, owned by `gob-check`.
    pub types: gob_check::TypesTable,
    /// `[cache]`.
    pub cache: CacheTable,
    /// `[agent]`.
    pub agent: AgentTable,
    /// `[git]`.
    pub git: GitTable,
    /// `[lease]`, owned by `frob-lease`.
    pub lease: frob_lease::LeaseConfig,
    /// `[worktree]`, owned by `frob-worktree`.
    pub worktree: frob_worktree::WorktreeConfig,
    // frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
    /// `[gc]`, owned by `frob-worktree`.
    pub gc: frob_worktree::GcConfig,
    /// `[evidence]`, owned by `frob-evidence`.
    pub evidence: frob_evidence::EvidenceTable,
    /// `[pm]`, `[pm.wip]` and `[pm.classes]`, owned by `frob-pm`.
    pub pm: frob_pm::PmConfig,
    /// `[release]`, owned by `frob-release`.
    pub release: frob_release::ReleaseConfig,
    // frob:ticket 01M4D6NWQ3F11S4MB3KT5K4JHZ
    /// `[land]`, owned by `frob-land`.
    pub land: frob_land::LandConfig,
    // frob:ticket 01M5BA1W8S9BW9Z47AV2ZKVEX0
    /// `[mirror]`, owned by `gob-config`: tracker identity for `frob mirror recreate`.
    pub mirror: gob_config::MirrorTable,
}

impl FrobConfig {
    /// The ledger settings these tables imply.
    pub fn ledger(&self) -> frob_ledger::LedgerConfig {
        frob_ledger::LedgerConfig::from_tables(&self.tickets, &self.git)
    }

    /// Load every table from `<root>/frob.toml` (a missing file is defaults).
    ///
    /// # Errors
    ///
    /// The first [`ConfigError`] from any table: unreadable file, bad TOML,
    /// unknown key (with a suggestion) or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        let doc = ConfigDocument::read(root, PRODUCT)?;
        let cfg = Self {
            tickets: doc.table::<TicketsTable>()?.value,
            check: CheckTable::from_document(&doc)?,
            perf: doc.table::<PerfTable>()?.value,
            types: gob_check::TypesTable::from_document(&doc)?,
            cache: doc.table::<CacheTable>()?.value,
            agent: doc.table::<AgentTable>()?.value,
            git: doc.table::<GitTable>()?.value,
            lease: doc.table::<frob_lease::LeaseConfig>()?.value,
            worktree: doc.table::<frob_worktree::WorktreeConfig>()?.value,
            // frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
            gc: doc.table::<frob_worktree::GcConfig>()?.value,
            evidence: doc.table::<frob_evidence::EvidenceTable>()?.value,
            pm: frob_pm::PmConfig::from_document(&doc)?,
            release: doc.table::<frob_release::ReleaseConfig>()?.value,
            // frob:ticket 01M4D6NWQ3F11S4MB3KT5K4JHZ
            land: doc.table::<frob_land::LandConfig>()?.value,
            // frob:ticket 01M5BA1W8S9BW9Z47AV2ZKVEX0
            mirror: doc.table::<gob_config::MirrorTable>()?.value,
        };
        tracing::debug!(root = %root.display(), "frob config loaded");
        Ok(cfg)
    }
}
