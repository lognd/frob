//! The `frob.toml` tables the M1 verbs need.

use gob_path::Shown;
use std::path::Path;

use gob_config::{ConfigDocument, ConfigError, ConfigTable};

/// `[tickets]` and `[git]` are owned by `frob-ledger`; re-exported for callers of this crate.
pub use frob_ledger::config::{GitTable, IndexWriterKnob, RefModeKnob, SyncTable, TicketsTable};

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
    // frob:ticket 01M4P2N1M00A5XSDA8SW5FBRR8
    /// Byte budget of `frob agent brief`; longer output is cut and marked.
    #[config(default = 2048)]
    pub brief_max_bytes: u64,
    /// Standing rules `frob agent brief` prints, one line each.
    #[config(default = vec![
        "Edit only files inside the lease scope; widen it with `frob lease widen`.".to_owned(),
        "Verify with `frob check --ticket` before landing.".to_owned(),
        "Log with tracing, never print; ASCII only.".to_owned(),
    ])]
    pub brief_rules: Vec<String>,
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
    // frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2
    /// `[sync]`, owned by `frob-ledger`: remote and freshness-probe settings.
    pub sync: SyncTable,
    // frob:ticket 01M5CW04YABDJW6ZXSWFGTCB9E
    /// `[claims]` and `[claims.class]`, owned by `frob-ledger`: claim idle windows and warnings.
    pub claims: frob_ledger::claim_window::ClaimWindows,
    /// `[lease]`, owned by `frob-lease`.
    pub lease: frob_lease::LeaseConfig,
    /// `[worktree]`, owned by `frob-worktree`.
    pub worktree: frob_worktree::WorktreeConfig,
    // frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
    /// `[gc]`, owned by `frob-worktree`.
    pub gc: frob_worktree::GcConfig,
    /// `[evidence]`, owned by `frob-evidence`.
    pub evidence: frob_evidence::EvidenceTable,
    // frob:ticket 01M4DYPG8A4CEY04ARSW3H4AJR
    /// `[evidence.dotnet]`, owned by `frob-evidence`.
    pub dotnet: frob_evidence::DotnetTable,
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
            sync: doc.table::<SyncTable>()?.value,
            // frob:ticket 01M5CW04YABDJW6ZXSWFGTCB9E
            claims: frob_ledger::claim_window::ClaimWindows::from_tables(
                &doc.table::<frob_ledger::claim_window::ClaimsTable>()?.value,
                &doc.table::<frob_ledger::claim_window::ClaimsClassTable>()?
                    .value,
            )
            .map_err(|message| ConfigError::Invalid {
                table: "claims".to_owned(),
                message,
            })?,
            lease: doc.table::<frob_lease::LeaseConfig>()?.value,
            worktree: doc.table::<frob_worktree::WorktreeConfig>()?.value,
            // frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
            gc: doc.table::<frob_worktree::GcConfig>()?.value,
            evidence: doc.table::<frob_evidence::EvidenceTable>()?.value,
            // frob:ticket 01M4DYPG8A4CEY04ARSW3H4AJR
            dotnet: doc.table::<frob_evidence::DotnetTable>()?.value,
            pm: frob_pm::PmConfig::from_document(&doc)?,
            release: doc.table::<frob_release::ReleaseConfig>()?.value,
            // frob:ticket 01M4D6NWQ3F11S4MB3KT5K4JHZ
            land: doc.table::<frob_land::LandConfig>()?.value,
            // frob:ticket 01M5BA1W8S9BW9Z47AV2ZKVEX0
            mirror: doc.table::<gob_config::MirrorTable>()?.value,
        };
        tracing::debug!(root = %Shown::of(root), "frob config loaded");
        Ok(cfg)
    }
}
