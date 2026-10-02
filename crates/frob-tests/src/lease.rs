//! Finding the ticket a worktree holds a lease for.
//!
//! `frob-lease` (T-0019) owns the lease file format and is built in parallel,
//! so the TOML is read loosely: a top-level string `ticket` and a string
//! `holder.worktree`. Every file under `<common_dir>/frob/leases/` is tried.

use std::path::Path;

/// The ticket reference of the lease whose `holder.worktree` is `worktree`, if any.
pub fn lease_ticket(common_dir: &Path, worktree: &Path) -> Option<String> {
    let dir = common_dir.join("frob").join("leases");
    let want = canonical(worktree);
    let entries = std::fs::read_dir(&dir).ok()?;
    let mut names: Vec<_> = entries.filter_map(std::result::Result::ok).collect();
    names.sort_by_key(std::fs::DirEntry::file_name);
    for entry in names {
        let path = entry.path();
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let Ok(table) = text.parse::<toml::Table>() else {
            tracing::debug!(path = %path.display(), "lease file is not TOML; skipped");
            continue;
        };
        let held = table
            .get("holder")
            .and_then(|h| h.get("worktree"))
            .and_then(toml::Value::as_str);
        let ticket = table.get("ticket").and_then(toml::Value::as_str);
        if let (Some(held), Some(ticket)) = (held, ticket)
            && canonical(Path::new(held)) == want
        {
            tracing::info!(ticket, lease = %path.display(), "worktree lease found");
            return Some(ticket.to_owned());
        }
    }
    tracing::debug!(dir = %dir.display(), "no lease for this worktree");
    None
}

fn canonical(p: &Path) -> std::path::PathBuf {
    std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf())
}
