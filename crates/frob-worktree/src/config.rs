//! The `[worktree]` config table and the slice of `[tickets]` and `[git]` the verbs need.

use std::path::Path;

use frob_ledger::{LedgerConfig, RefMode};
use gob_config::{ConfigError, ConfigTable};
use serde::Deserialize;

/// The product whose `frob.toml` carries the tables.
const PRODUCT: &str = "frob";

/// Where `frob work` creates worktrees.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "worktree", materialize)]
pub struct WorktreeConfig {
    /// Parent directory of ticket worktrees; relative paths resolve against the
    /// primary checkout and `{repo}` stands for its directory name.
    #[config(default = "../{repo}-wt".to_owned())]
    pub dir: String,
}

impl WorktreeConfig {
    /// Load `[worktree]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }
}

/// The `[tickets]` keys the ledger reads, tolerant of every other key.
#[derive(Debug, Default, Deserialize)]
struct RawTickets {
    r#ref: Option<String>,
    dir: Option<String>,
    ref_mode: Option<String>,
    handle_min_len: Option<usize>,
    actor: Option<String>,
}

/// The `[git]` keys the ledger reads.
#[derive(Debug, Default, Deserialize)]
struct RawGit {
    cas_retries: Option<u32>,
}

/// The tables of `frob.toml` that make up a [`LedgerConfig`].
#[derive(Debug, Default, Deserialize)]
struct RawFile {
    #[serde(default)]
    tickets: RawTickets,
    #[serde(default)]
    git: RawGit,
}

/// The ledger settings in `<root>/frob.toml`, defaults for anything absent.
///
/// The `frob` binary owns the validated `[tickets]` and `[git]` tables and
/// depends on this crate, so this reads just the keys [`LedgerConfig`] needs and
/// ignores the rest; `frob config show` remains the place that validates them.
///
/// # Errors
///
/// A message naming the file when it cannot be read or parsed, or when `ref_mode` is unknown.
pub fn ledger_config(root: &Path) -> Result<LedgerConfig, String> {
    let path = root.join("frob.toml");
    let raw: RawFile = match std::fs::read_to_string(&path) {
        Ok(text) => toml::from_str(&text).map_err(|e| format!("{}: {e}", path.display()))?,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => RawFile::default(),
        Err(e) => return Err(format!("{}: {e}", path.display())),
    };
    let mut cfg = LedgerConfig::default();
    if let Some(r) = raw.tickets.r#ref {
        cfg.ref_name = r;
    }
    if let Some(d) = raw.tickets.dir {
        cfg.dir = d;
    }
    if let Some(m) = raw.tickets.ref_mode {
        cfg.mode = m
            .parse::<RefMode>()
            .map_err(|e| format!("{}: [tickets] ref_mode: {e}", path.display()))?;
    }
    if let Some(n) = raw.tickets.handle_min_len {
        cfg.handle_min_len = n;
    }
    cfg.actor = raw.tickets.actor.filter(|a| !a.is_empty());
    if let Some(n) = raw.git.cas_retries {
        cfg.cas_retries = n;
    }
    tracing::debug!(root = %root.display(), ref_name = %cfg.ref_name, "ledger settings read");
    Ok(cfg)
}
