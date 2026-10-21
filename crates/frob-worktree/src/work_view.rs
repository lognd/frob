//! Human `--text` view of `frob work` and `frob start`: a pure function from the verb's data to printable rows.
// frob:ticket 01M5EFE44WSM03AW4771Y53GFT

use gob_path::Shown;

use crate::verbs::StartData;

/// The rows of `work` / `start`: a one-line verdict, then worktree, branch, merge, conflicts and lease facts.
pub(crate) fn work_rows(data: &StartData, already: bool) -> Vec<String> {
    let verdict = if already {
        "already leased"
    } else if data.created_worktree {
        "leased, worktree created"
    } else {
        "leased"
    };
    let mut out = vec![format!("{} {verdict}", data.handle)];
    out.push(format!("  worktree  {}", Shown::of(&data.path)));
    if let Some(branch) = &data.branch {
        out.push(format!("  branch    {branch}"));
    }
    if let Some(merge) = &data.merge {
        out.push(format!("  base      {merge}"));
    }
    let scope = if data.lease.scope.is_empty() {
        "(empty)".to_owned()
    } else {
        data.lease.scope.join(", ")
    };
    out.push(format!(
        "  lease     {} for {}s, scope {scope}",
        data.lease.holder.actor, data.lease.ttl_secs
    ));
    if let Some(prev) = &data.stolen_from {
        out.push(format!("  stolen    from {prev}"));
    }
    if !data.conflicts.is_empty() {
        out.push(String::new());
        out.push("Conflicts".to_owned());
        out.extend(data.conflicts.iter().map(|c| format!("  {c}")));
    }
    tracing::debug!(rows = out.len(), "work_view: work");
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_lease::{Holder, Lease};
    use frob_ledger::TicketId;

    /// A [`StartData`] for a fresh `work`, for the view tests.
    fn data() -> StartData {
        let holder = Holder {
            actor: "ann".to_owned(),
            worktree: "/wt/x".into(),
        };
        let lease: Lease = serde_json::from_value(serde_json::json!({
            "ticket": "01M5EFE44WSM03AW4771Y53GFT",
            "holder": {"actor": "ann", "worktree": "/wt/x"},
            "scope": ["a/**"],
            "acquired_at": "2026-10-21T08:26:18Z",
            "renewed_at": "2026-10-21T08:26:18Z",
            "ttl_secs": 7200
        }))
        .unwrap();
        StartData {
            id: "01M5EFE44WSM03AW4771Y53GFT".parse::<TicketId>().unwrap(),
            handle: "~1Y53GFT".to_owned(),
            path: holder.worktree.clone(),
            branch: Some("ticket/x".to_owned()),
            lease,
            created_worktree: true,
            merge: Some("up-to-date".to_owned()),
            conflicts: Vec::new(),
            stolen_from: None,
        }
    }

    // frob:tests crates/frob-worktree/src/work_view.rs::work_rows
    #[test]
    fn work_view_names_worktree_branch_and_lease() {
        let rows = work_rows(&data(), false);
        assert_eq!(rows[0], "~1Y53GFT leased, worktree created");
        assert!(rows.iter().any(|r| r.contains("branch    ticket/x")));
        assert!(rows.iter().any(|r| r.contains("scope a/**")));
    }

    // frob:tests crates/frob-worktree/src/work_view.rs::work_rows
    #[test]
    fn work_view_lists_conflicts_and_already() {
        let mut d = data();
        d.conflicts = vec!["src/a.rs".to_owned()];
        let rows = work_rows(&d, true);
        assert_eq!(rows[0], "~1Y53GFT already leased");
        assert_eq!(rows.last().map(String::as_str), Some("  src/a.rs"));
    }
}
