//! Reading [`LedgerConfig`] from a `frob.toml`, shared by every crate that opens a ledger without the `frob` binary's validated tables.

use std::path::Path;

use crate::ledger::{LedgerConfig, RefMode};

/// The [`LedgerConfig`] in `<root>/frob.toml`, defaults for anything absent.
///
/// The `[tickets]` and `[git]` tables are validated by the `frob` binary; this reads the
/// handful of keys a ledger needs and ignores the rest.
///
/// # Errors
///
/// A message naming the file when it cannot be read or parsed, or a known key has the wrong type or value.
pub fn load_ledger_config(root: &Path) -> Result<LedgerConfig, String> {
    let path = root.join("frob.toml");
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            return Ok(LedgerConfig::default());
        }
        Err(e) => return Err(format!("{}: {e}", path.display())),
    };
    let table: toml::Table = text
        .parse()
        .map_err(|e: toml::de::Error| format!("{}: {e}", path.display()))?;
    let cfg = ledger_config_from(&table)?;
    tracing::debug!(root = %root.display(), ref_name = %cfg.ref_name, mode = ?cfg.mode, "ledger settings read");
    Ok(cfg)
}

/// [`LedgerConfig`] from a parsed `frob.toml`.
///
/// # Errors
///
/// A message naming the key that has the wrong type or an unknown `ref_mode`.
pub fn ledger_config_from(table: &toml::Table) -> Result<LedgerConfig, String> {
    let mut cfg = LedgerConfig::default();
    let bad = |key: &str| format!("{key} has the wrong type");
    if let Some(t) = table.get("tickets").and_then(toml::Value::as_table) {
        for (key, slot) in [
            ("ref", &mut cfg.ref_name),
            ("dir", &mut cfg.dir),
            ("branch", &mut cfg.branch),
        ] {
            if let Some(v) = t.get(key) {
                v.as_str()
                    .ok_or_else(|| bad(&format!("tickets.{key}")))?
                    .clone_into(slot);
            }
        }
        if let Some(v) = t.get("ref_mode") {
            cfg.mode = v
                .as_str()
                .ok_or_else(|| bad("tickets.ref_mode"))?
                .parse::<RefMode>()
                .map_err(|e| format!("[tickets] ref_mode: {e}"))?;
        }
        if let Some(v) = t.get("handle_min_len") {
            let n = v
                .as_integer()
                .ok_or_else(|| bad("tickets.handle_min_len"))?;
            cfg.handle_min_len = usize::try_from(n).map_err(|_| bad("tickets.handle_min_len"))?;
        }
        if let Some(v) = t.get("actor") {
            let a = v.as_str().ok_or_else(|| bad("tickets.actor"))?;
            cfg.actor = (!a.is_empty()).then(|| a.to_owned());
        }
    }
    if let Some(v) = table
        .get("git")
        .and_then(toml::Value::as_table)
        .and_then(|g| g.get("cas_retries"))
    {
        let n = v.as_integer().ok_or_else(|| bad("git.cas_retries"))?;
        cfg.cas_retries = u32::try_from(n).map_err(|_| bad("git.cas_retries"))?;
    }
    Ok(cfg)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M4CTTSAZC93K94KNXH3WVSYM
    #[test]
    fn orphan_mode_and_branch_are_read() {
        let t: toml::Table = "[tickets]\nref = \"main\"\nref_mode = \"orphan\"\nbranch = \"tix\"\n"
            .parse()
            .expect("toml");
        let cfg = ledger_config_from(&t).expect("config");
        assert_eq!(cfg.mode, RefMode::Orphan);
        assert_eq!(
            (cfg.ref_name.as_str(), cfg.branch.as_str()),
            ("main", "tix")
        );
        let bad: toml::Table = "[tickets]\nref_mode = \"nope\"\n".parse().expect("toml");
        assert!(ledger_config_from(&bad).is_err());
    }
}
