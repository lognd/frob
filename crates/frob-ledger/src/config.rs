//! The `[tickets]` and `[git]` tables of `frob.toml`: the one parser of the ledger's settings, shared by every crate that opens a ledger.

use gob_path::Shown;
use std::path::Path;

use gob_config::{ConfigDocument, ConfigError, ConfigTable};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::r#gen::tour::{Entry, Pins, TourSettings};
use crate::id::TicketId;
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
    /// Name of the orphan branch `frob ticket branch init` creates for the ledger (`tickets.md` section 2.1).
    #[config(default = "frob-tickets".to_owned(), enforcement)]
    pub branch: String,
    /// Directory of ticket files, relative to the repository root.
    #[config(default = "tickets".to_owned())]
    pub dir: String,
    /// `trunk` commits to `ref`; `branch` commits to the checked-out branch; `orphan` commits to the ticket branch `branch` in the ticket-branch layout and keeps `ref` as the code base.
    #[config(default = RefModeKnob::Trunk, enforcement)]
    pub ref_mode: RefModeKnob,
    /// `local`: a parent or title change writes its reindex commit at once; `ci`: it writes only the decision commit and the CI job runs `frob ticket reindex` (`tickets.md` 11.2).
    #[config(default = IndexWriterKnob::Local)]
    pub index_writer: IndexWriterKnob,
    /// Shortest ticket handle shown (`~` plus this many id characters).
    #[config(default = 7)]
    pub handle_min_len: u32,
    /// Actor recorded on events; empty means git `user.name`.
    #[config(default = String::new())]
    pub actor: String,
    /// Most points a ticket labelled `good-first` may carry before PM031 fires (`docs/design/shared/documentation.md section 11.4.2`).
    // frob:ticket 01M3ZX87KRP6G49GHANMAK5JA8
    #[config(default = 2)]
    pub good_first_max_points: u32,
    /// Fewest ready good-first tickets before PM032 warns; 0 turns the rule off (`docs/design/shared/documentation.md section 11.4.2`).
    // frob:ticket 01M3ZX87ZJR4YVZZ4AS7VSR4BQ
    #[config(default = 3)]
    pub good_first_min: u32,
}

/// The pinned examples, code map and gates of the generated tour (`docs/design/shared/documentation.md section 11.5`).
// frob:ticket 01M4PWQPZHABWZJ3VXT4KXPVAV
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "tour", materialize)]
pub struct TourTable {
    /// Ticket id of the stop 3 example (a done ticket with evidence and a land); empty picks one.
    #[config(default = String::new())]
    pub closed: String,
    /// Ticket id of the stop 2 epic; empty picks the largest open epic.
    #[config(default = String::new())]
    pub epic: String,
    /// Ticket id of the stop 5 good-first ticket; empty picks the first ready one.
    #[config(default = String::new())]
    pub good_first: String,
    /// Stop 1 code map, each `"path: one-line description"`.
    #[config(default = Vec::<String>::new())]
    pub code_map: Vec<String>,
    /// Stop 4 gates, each `"name: one-line description"`.
    #[config(default = Vec::<String>::new())]
    pub gates: Vec<String>,
}

impl TourTable {
    /// The [`TourSettings`] this table holds.
    ///
    /// # Errors
    ///
    /// A message naming the key when a pin is not a ticket id or a list line has no `name: description` shape.
    pub fn settings(&self) -> Result<TourSettings, String> {
        let pin = |key: &str, v: &str| -> Result<Option<TicketId>, String> {
            if v.is_empty() {
                return Ok(None);
            }
            v.parse::<TicketId>()
                .map(Some)
                .map_err(|e| format!("`{key}` is not a ticket id ({v}): {e}"))
        };
        let list = |key: &str, lines: &[String]| -> Result<Vec<Entry>, String> {
            lines
                .iter()
                .map(|l| {
                    Entry::parse(l)
                        .ok_or_else(|| format!("`{key}` entry `{l}` is not `name: description`"))
                })
                .collect()
        };
        let settings = TourSettings {
            pins: Pins {
                closed: pin("closed", &self.closed)?,
                epic: pin("epic", &self.epic)?,
                good_first: pin("good_first", &self.good_first)?,
            },
            code_map: list("code_map", &self.code_map)?,
            gates: list("gates", &self.gates)?,
        };
        tracing::debug!(
            map = settings.code_map.len(),
            gates = settings.gates.len(),
            "tour settings read"
        );
        Ok(settings)
    }
}

/// Settings of in-process git access.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "git", materialize)]
pub struct GitTable {
    /// Compare-and-swap retries when moving a ledger ref.
    #[config(default = 5, enforcement)]
    pub cas_retries: u32,
}

/// Settings of the freshness probe behind `frob refresh` (`distributed-tickets.md` section 5).
// frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "sync", materialize)]
pub struct SyncTable {
    /// The one authoritative remote; other remotes are never probed.
    #[config(default = "origin".to_owned())]
    pub remote: String,
    /// Seconds a successful probe stays fresh before the next one is due.
    #[config(default = 300)]
    pub ttl_secs: u32,
    /// Milliseconds before a hung `git ls-remote` is killed.
    #[config(default = 2500)]
    pub probe_timeout_ms: u32,
    /// Ceiling in seconds of the exponential backoff after failed probes.
    #[config(default = 3600)]
    pub backoff_max_secs: u32,
    /// Seconds of cache age after which read verbs footnote that the ticket view is old.
    #[config(default = 3600)]
    pub warn_after_secs: u32,
    /// Seconds of cache age past which mutating verbs refuse (`E-SYNC-STALE`) when the remote cannot be reached.
    #[config(default = 86400)]
    pub stale_error_secs: u32,
    /// Milliseconds a mutating verb may spend probing in the foreground before it falls back to the cache.
    #[config(default = 3000)]
    pub foreground_budget_ms: u32,
    /// Milliseconds a `frob refresh` fetch or push may run before it is killed.
    #[config(default = 10000)]
    pub fetch_timeout_ms: u32,
}

impl LedgerConfig {
    /// The ledger settings the `[tickets]` and `[git]` tables imply.
    #[must_use]
    pub fn from_tables(tickets: &TicketsTable, git: &GitTable, tour: TourSettings) -> Self {
        Self {
            tour,
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

/// The [`TourSettings`] of a parsed `frob.toml`.
///
/// # Errors
///
/// The [`ConfigError`] for an unknown or mistyped `[tour]` key, a pin that is not a ticket id or a malformed list line.
pub fn tour_settings(doc: &ConfigDocument) -> Result<TourSettings, ConfigError> {
    doc.table::<TourTable>()?
        .value
        .settings()
        .map_err(|message| ConfigError::Invalid {
            table: "tour".to_owned(),
            message,
        })
}

/// [`LedgerConfig`] from a parsed `frob.toml`.
///
/// # Errors
///
/// The [`ConfigError`] for an unknown or mistyped `[tickets]` or `[git]` key.
pub fn ledger_config_from(doc: &ConfigDocument) -> Result<LedgerConfig, ConfigError> {
    let tickets = doc.table::<TicketsTable>()?.value;
    let git = doc.table::<GitTable>()?.value;
    let tour = tour_settings(doc)?;
    Ok(LedgerConfig::from_tables(&tickets, &git, tour))
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

    // frob:ticket 01M5D6XDTZ9ZBGRVV71YNH5KJJ
    #[test]
    fn fetch_timeout_ms_defaults_and_overrides() {
        let doc = ConfigDocument::parse("", Path::new("frob.toml")).expect("toml");
        assert_eq!(
            doc.table::<SyncTable>()
                .expect("sync")
                .value
                .fetch_timeout_ms,
            10_000
        );
        let doc = ConfigDocument::parse("[sync]\nfetch_timeout_ms = 42\n", Path::new("frob.toml"))
            .expect("toml");
        assert_eq!(
            doc.table::<SyncTable>()
                .expect("sync")
                .value
                .fetch_timeout_ms,
            42
        );
    }
}
