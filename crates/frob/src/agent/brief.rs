//! The compact session brief behind `frob agent brief`: active ticket, lease scope, worktree and standing rules, capped to a byte budget.

// frob:ticket 01M4P2N1M00A5XSDA8SW5FBRR8

use schemars::JsonSchema;
use serde::Serialize;

/// Marker appended when the brief had to be cut to fit the budget.
pub const TRUNCATION_MARK: &str = "[brief truncated]";

/// The active ticket a session works on, as the brief shows it.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ActiveTicket {
    /// Ticket handle with its `~`.
    pub handle: String,
    /// Ticket title (empty when the ledger could not be read).
    pub title: String,
    /// Workflow category (empty when unknown).
    pub category: String,
}

/// Everything the brief prints, gathered before rendering.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BriefInput {
    /// The ticket leased from this worktree, if any.
    pub ticket: Option<ActiveTicket>,
    /// Lease scope globs of that ticket.
    pub scope: Vec<String>,
    /// The worktree the session runs in.
    pub worktree: String,
    /// Standing rules, one line each.
    pub rules: Vec<String>,
}

/// The rendered lines of `input`, in the order ticket, scope, worktree, rules.
#[must_use]
pub fn lines(input: &BriefInput) -> Vec<String> {
    let mut out = Vec::new();
    match &input.ticket {
        Some(t) => {
            out.push(format!("Active ticket: {}  {}", t.handle, t.title));
            if !t.category.is_empty() {
                out.push(format!("Category: {}", t.category));
            }
            out.push(format!("Lease scope: {}", input.scope.join(", ")));
        }
        None => out.push(
            "Active ticket: none (no live lease is held from this worktree; start one with `frob work`)"
                .to_owned(),
        ),
    }
    out.push(format!("Worktree: {}", input.worktree));
    if !input.rules.is_empty() {
        out.push("Standing rules:".to_owned());
        out.extend(input.rules.iter().map(|r| format!("- {r}")));
    }
    out
}

/// Join `lines` with newlines and cut to at most `max_bytes` on a line-friendly char boundary, marking a cut; the flag says whether it was cut.
#[must_use]
pub fn cap(lines: &[String], max_bytes: usize) -> (String, bool) {
    let full = lines.join("\n");
    if full.len() <= max_bytes {
        return (full, false);
    }
    let mark = format!("\n{TRUNCATION_MARK}");
    let room = max_bytes.saturating_sub(mark.len());
    let mut end = room.min(full.len());
    while !full.is_char_boundary(end) {
        end -= 1;
    }
    // Prefer to cut at the last whole line when one fits.
    if let Some(nl) = full[..end].rfind('\n') {
        end = nl;
    }
    let mut text = full[..end].to_owned();
    if text.len() + mark.len() <= max_bytes {
        text.push_str(&mark);
    }
    tracing::debug!(
        full = full.len(),
        kept = text.len(),
        max_bytes,
        "brief truncated"
    );
    (text, true)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn input() -> BriefInput {
        BriefInput {
            ticket: Some(ActiveTicket {
                handle: "~ABC1234".to_owned(),
                title: "do the thing".to_owned(),
                category: "in-progress".to_owned(),
            }),
            scope: vec!["crates/x/**".to_owned(), "docs/y.md".to_owned()],
            worktree: "/w/ABC1234".to_owned(),
            rules: vec!["stay in scope".to_owned(), "log, do not print".to_owned()],
        }
    }

    // frob:tests crates/frob/src/agent/brief.rs::lines
    #[test]
    fn lines_cover_ticket_scope_worktree_and_rules() {
        let text = lines(&input()).join("\n");
        assert!(text.contains("~ABC1234  do the thing"));
        assert!(text.contains("crates/x/**, docs/y.md"));
        assert!(text.contains("Worktree: /w/ABC1234"));
        assert!(text.contains("- stay in scope"));
    }

    // frob:tests crates/frob/src/agent/brief.rs::lines
    #[test]
    fn no_lease_says_none() {
        let mut i = input();
        i.ticket = None;
        assert!(lines(&i)[0].starts_with("Active ticket: none"));
    }

    // frob:tests crates/frob/src/agent/brief.rs::cap
    #[test]
    fn cap_bounds_output_and_marks_the_cut() {
        let ls = lines(&input());
        let (whole, cut) = cap(&ls, 10_000);
        assert!(!cut);
        assert!(!whole.contains(TRUNCATION_MARK));
        for budget in [40, 64, 100] {
            let (text, cut) = cap(&ls, budget);
            assert!(cut);
            assert!(text.len() <= budget, "{} > {budget}", text.len());
        }
        let (text, _) = cap(&ls, 100);
        assert!(text.ends_with(TRUNCATION_MARK));
    }

    // frob:tests crates/frob/src/agent/brief.rs::cap
    #[test]
    fn cap_never_splits_a_char() {
        let ls = vec!["caf\u{e9}".repeat(40)];
        let (text, cut) = cap(&ls, 33);
        assert!(cut && text.len() <= 33);
    }
}
