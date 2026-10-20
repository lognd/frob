//! The `[tickets]` and `[git]` tables of `frob.toml`: the one parser of the ledger's settings, shared by every crate that opens a ledger.

use gob_path::Shown;
use std::path::Path;

use gob_config::{ConfigDocument, ConfigError, ConfigTable};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::ledger::{LedgerConfig, RefMode};

/// The product whose config file holds the ledger tables.
const PRODUCT: &str = "frob";

/// Where ledger commits go (`[tickets] ref_mode`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum RefModeKnob {
    /// Commits advance the configured `ref`, whatever branch is checked out.
    Trunk,
    /// Commits go on the currently checked-out branch (protected trunk, forks).
    Branch,
    /// Commits go on the orphan ticket branch `[tickets] branch`; `ref` stays the code base branch.
    Orphan,
}

impl From<RefModeKnob> for RefMode {
    fn from(k: RefModeKnob) -> Self {
        match k {
            RefModeKnob::Trunk => Self::Trunk,
            RefModeKnob::Branch => Self::Branch,
            RefModeKnob::Orphan => Self::Orphan,
        }
    }
}

/// Who writes the reindex commit after a parent or title change (`[tickets] index_writer`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum IndexWriterKnob {
    /// The verb writes the reindex commit right after the decision commit.
    Local,
    /// Only the decision commit is written; the CI job runs `frob ticket reindex`.
    Ci,
}

/// Where the ticket ledger lives.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "tickets", materialize)]
pub struct TicketsTable {
    /// Ref holding the ledger; the ledger merge driver and `doctor` resolve it.
    #[config(default = "refs/heads/main".to_owned(), enforcement)]
    pub r#ref: String,
    /// Name of the orphan branch `frob ticket branch init` creates for the ledger (`mirror.md` section 1).
    #[config(default = "frob-tickets".to_owned(), enforcement)]
    pub branch: String,
    /// Directory of ticket files, relative to the repository root.
    #[config(default = "tickets".to_owned())]
    pub dir: String,
    /// `trunk` commits to `ref`; `branch` commits to the checked-out branch; `orphan` commits to the ticket branch `branch` in the ticket-branch layout and keeps `ref` as the code base.
    #[config(default = RefModeKnob::Trunk, enforcement)]
    pub ref_mode: RefModeKnob,
    /// `local`: a parent or title change writes its reindex commit at once; `ci`: it writes only the decision commit and the CI job runs `frob ticket reindex` (`navigation.md` 2.2).
    #[config(default = IndexWriterKnob::Local)]
    pub index_writer: IndexWriterKnob,
    /// Shortest ticket handle shown (`~` plus this many id characters).
    #[config(default = 7)]
    pub handle_min_len: u32,
    /// Actor recorded on events; empty means git `user.name`.
    #[config(default = String::new())]
    pub actor: String,
    /// Most points a ticket labelled `good-first` may carry before PM031 fires (`navigation.md` section 4.2).
    // frob:ticket 01M3ZX87KRP6G49GHANMAK5JA8
    #[config(default = 2)]
    pub good_first_max_points: u32,
    /// Fewest ready good-first tickets before PM032 warns; 0 turns the rule off (`navigation.md` section 4.2).
    // frob:ticket 01M3ZX87ZJR4YVZZ4AS7VSR4BQ
    #[config(default = 3)]
    pub good_first_min: u32,
}

/// Settings of in-process git access.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "git", materialize)]
pub struct GitTable {
    /// Compare-and-swap retries when moving a ledger ref.
    #[config(default = 5, enforcement)]
    pub cas_retries: u32,
}

impl LedgerConfig {
    /// The ledger settings the `[tickets]` and `[git]` tables imply.
    #[must_use]
    pub fn from_tables(tickets: &TicketsTable, git: &GitTable) -> Self {
        Self {
            ref_name: tickets.r#ref.clone(),
            mode: tickets.ref_mode.into(),
            branch: tickets.branch.clone(),
            dir: tickets.dir.clone(),
            cas_retries: git.cas_retries,
            handle_min_len: tickets.handle_min_len as usize,
            actor: (!tickets.actor.is_empty()).then(|| tickets.actor.clone()),
        }
    }
}

/// The [`LedgerConfig`] in `<root>/frob.toml`, defaults for anything absent.
///
/// # Errors
///
/// A message naming the file when it cannot be read or parsed, or a `[tickets]`/`[git]` key is unknown or mistyped.
pub fn load_ledger_config(root: &Path) -> Result<LedgerConfig, String> {
    let doc = ConfigDocument::read(root, PRODUCT).map_err(|e| e.to_string())?;
    let cfg = ledger_config_from(&doc).map_err(|e| e.to_string())?;
    tracing::debug!(root = %Shown::of(root), ref_name = %cfg.ref_name, mode = ?cfg.mode, "ledger settings read");
    Ok(cfg)
}

/// [`LedgerConfig`] from a parsed `frob.toml`.
///
/// # Errors
///
/// The [`ConfigError`] for an unknown or mistyped `[tickets]` or `[git]` key.
pub fn ledger_config_from(doc: &ConfigDocument) -> Result<LedgerConfig, ConfigError> {
    let tickets = doc.table::<TicketsTable>()?.value;
    let git = doc.table::<GitTable>()?.value;
    Ok(LedgerConfig::from_tables(&tickets, &git))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M4CTTSAZC93K94KNXH3WVSYM
    #[test]
    fn orphan_mode_and_branch_are_read() {
        let doc = ConfigDocument::parse(
            "[tickets]\nref = \"main\"\nref_mode = \"orphan\"\nbranch = \"tix\"\n",
            Path::new("frob.toml"),
        )
        .expect("toml");
        let cfg = ledger_config_from(&doc).expect("config");
        assert_eq!(cfg.mode, RefMode::Orphan);
        assert_eq!(
            (cfg.ref_name.as_str(), cfg.branch.as_str()),
            ("main", "tix")
        );
        let bad = ConfigDocument::parse("[tickets]\nref_mode = \"nope\"\n", Path::new("frob.toml"))
            .expect("toml");
        assert!(ledger_config_from(&bad).is_err());
    }
}
