//! The mirror's per-ticket map shard and the ticket-path lookup `frob ticket url` needs.
//!
//! `mirror.md` 3.2 keeps the map "sharded per ticket on the ticket branch". A shard is
//! `.mirror/map/<ULID>.toml` holding at least `issue = <number>`: the tracker issue the ticket is
//! mirrored to. The tracker stays the identity authority and the shard is a cache of it, so this
//! module only reads the number; the mirror run owns writing shards.
// frob:ticket 01M4M85N13CXXPTEE7PYVCV0NS

use crate::error::{LedgerError, Result};
use crate::id::TicketId;
use crate::layout::Layout;
use crate::ledger::Ledger;

/// Directory of map shards on the ticket branch, one `<ULID>.toml` per mirrored ticket.
pub const MAP_DIR: &str = ".mirror/map";

/// The branch-relative path of the map shard of `id`.
#[must_use]
pub fn shard_path(id: TicketId) -> String {
    format!("{MAP_DIR}/{id}.toml")
}

/// The tracker issue number a map shard binds its ticket to, `None` while the shard has no `issue` yet.
///
/// # Errors
///
/// [`LedgerError`] (malformed) when `text` is not TOML, or `issue` is present but not a positive integer.
pub fn parse_shard(path: &str, text: &str) -> Result<Option<u64>> {
    let table: toml::Table = text
        .parse()
        .map_err(|e: toml::de::Error| LedgerError::malformed(path, e.message()))?;
    let Some(value) = table.get("issue") else {
        tracing::debug!(path, "map shard has no issue yet; treating as unmapped");
        return Ok(None);
    };
    value
        .as_integer()
        .and_then(|n| u64::try_from(n).ok())
        .filter(|n| *n > 0)
        .map(Some)
        .ok_or_else(|| LedgerError::malformed(path, "`issue` must be a positive integer"))
}

impl Ledger {
    /// The current repository path of the file of ticket `id` at the ledger tip, `None` on an empty ledger.
    ///
    /// On the ticket branch this is the computed `<top-epic>/<slug>.md` path, or wherever a hand
    /// move left the file (identity is the frontmatter ULID); in the legacy layout it is
    /// `tickets/<ULID>/ticket.md`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::NotFound`] when the ticket is absent, or store failures.
    pub fn ticket_path(&self, id: TicketId) -> Result<Option<String>> {
        let s = self.synced()?;
        Self::load(&s, id)?;
        match s.tip {
            Some(tip) => self.ticket_file_at(&tip.to_string(), id, None),
            None => Ok(None),
        }
    }

    /// The ticket whose file sits at `path` (ticket-branch relative) at the ledger tip.
    ///
    /// `None` in the legacy layout, on an empty ledger, or when no ticket file is at `path`.
    ///
    /// # Errors
    ///
    /// Store or git failures.
    // frob:ticket 01M3ZX86MA30ABW915Z943BQYB
    pub fn ticket_at_path(&self, path: &str) -> Result<Option<TicketId>> {
        if self.layout() != Layout::Branch {
            return Ok(None);
        }
        let s = self.synced()?;
        let Some(tip) = s.tip else {
            return Ok(None);
        };
        let scan = self.branch_scan_at(&tip.to_string())?;
        Ok(scan
            .files
            .iter()
            .find(|(_, p)| p.as_str() == path)
            .map(|(id, _)| *id))
    }

    /// The tracker issue number ticket `id` is mirrored to, `None` when it has no map shard or the shard has no `issue` yet.
    ///
    /// # Errors
    ///
    /// [`LedgerError::NotFound`] when the ticket is absent, [`LedgerError`] (malformed) for a
    /// shard whose `issue` is not a positive integer, or store failures.
    pub fn mirror_issue(&self, id: TicketId) -> Result<Option<u64>> {
        let s = self.synced()?;
        Self::load(&s, id)?;
        let Some(tip) = s.tip else {
            return Ok(None);
        };
        let path = shard_path(id);
        self.text(&tip.to_string(), &path)?
            .map(|t| parse_shard(&path, &t))
            .transpose()
            .map(Option::flatten)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shard_binds_a_positive_issue_number() {
        // frob:tests crates/frob-ledger/src/mirror_map.rs::parse_shard
        assert_eq!(parse_shard("p", "issue = 42\n").ok(), Some(Some(42)));
        assert!(parse_shard("p", "issue = 0\n").is_err());
        assert!(parse_shard("p", "issue = \"x\"\n").is_err());
        assert!(parse_shard("p", "not toml [").is_err());
    }

    #[test]
    fn shard_without_issue_is_unmapped_not_malformed() {
        // frob:tests crates/frob-ledger/src/mirror_map.rs::parse_shard
        assert_eq!(parse_shard("p", "other = 1\n").ok(), Some(None));
        assert_eq!(parse_shard("p", "").ok(), Some(None));
    }
}
