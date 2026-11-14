//! Pre-push gate: every `frob:ticket` id the branch adds must exist in a ledger
//! (frob:ticket 01M7BR4JX3EZVXK1A6JD49NB6Q).
//!
//! A citation of a ticket no ledger holds is a dangling reference that landing would bake into
//! the code branch. [`cited_in_diff`] extracts the ids from the added lines of a diff and [`gate`]
//! asks [`frob_ledger::Ledger::cited_ticket_issues`] about them. The refusal carries no waiver path:
//! the only remedy is to recover or push the ticket.

use std::path::Path;

use frob_ledger::Ledger;
use gob_git::Repo;

use crate::error::{LandError, needs_action};
use crate::git::git;

/// The directive whose argument is a ticket id.
const DIRECTIVE: &str = "frob:ticket";

/// `(path:line, id)` pairs for each `frob:ticket <id>` citation on an added line of a `-U0` diff.
pub(crate) fn cited_in_diff(diff: &str) -> Vec<(String, String)> {
    let mut out = Vec::new();
    let mut file: Option<String> = None;
    let mut line_no: u64 = 0;
    for line in diff.lines() {
        if let Some(p) = line.strip_prefix("+++ b/") {
            file = Some(p.to_owned());
        } else if line.starts_with("+++ ") {
            file = None;
        } else if line.starts_with("--- ") {
        } else if let Some(h) = line.strip_prefix("@@ ") {
            line_no = h
                .split('+')
                .nth(1)
                .and_then(|s| s.split([',', ' ']).next())
                .and_then(|s| s.parse().ok())
                .unwrap_or(0);
        } else if let (Some(f), Some(added)) = (&file, line.strip_prefix('+')) {
            for id in ids_in(added) {
                out.push((format!("{f}:{line_no}"), id));
            }
            line_no += 1;
        }
    }
    out
}

/// Every token following a `frob:ticket` directive on one line.
fn ids_in(line: &str) -> Vec<String> {
    line.match_indices(DIRECTIVE)
        .filter_map(|(i, _)| {
            let tok: String = line[i + DIRECTIVE.len()..]
                .trim_start()
                .chars()
                .take_while(char::is_ascii_alphanumeric)
                .collect();
            (!tok.is_empty()).then_some(tok)
        })
        .collect()
}

/// Refuse when the branch cites a ticket that exists in no ledger.
///
/// # Errors
///
/// A `E-LAND-CITED-MISSING` refusal naming each dangling citation, or a git/ledger read failure.
pub(crate) fn gate(
    repo: &Repo,
    wt_path: &Path,
    base_ref: &str,
    ledger: &Ledger,
) -> Result<(), LandError> {
    let range = format!("{base_ref}...HEAD");
    let run = git(repo, wt_path, &["diff", "-U0", "--no-color", &range])?;
    if !run.ok() {
        return Err(LandError::Config(format!(
            "git diff {range} failed: {}",
            run.text.trim()
        )));
    }
    let cited = cited_in_diff(&run.text);
    tracing::debug!(count = cited.len(), "ticket citations found in the diff");
    let pairs: Vec<(&str, &str)> = cited
        .iter()
        .map(|(a, b)| (a.as_str(), b.as_str()))
        .collect();
    let issues = ledger
        .cited_ticket_issues(&pairs)
        .map_err(|e| LandError::Config(e.to_string()))?;
    if issues.is_empty() {
        return Ok(());
    }
    let msg = issues
        .iter()
        .map(|i| format!("{}: {}", i.code, i.message))
        .collect::<Vec<_>>()
        .join("; ");
    tracing::error!(
        issues = issues.len(),
        "land blocked by dangling ticket citations"
    );
    Err(needs_action(
        "E-LAND-CITED-MISSING",
        msg,
        "frob ticket doctor",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-land/src/cited_tickets.rs::cited_in_diff
    #[test]
    fn extracts_ids_from_added_lines_only() {
        let diff = "+++ b/a.rs\n@@ -1,0 +5,2 @@\n+// frob:ticket 01M7BR4JX3EZVXK1A6JD49NB6Q\n+fn x() {}\n-// frob:ticket 01M7BR4JX3EZVXK1A6JD49NB6R\n";
        let got = cited_in_diff(diff);
        assert_eq!(
            got,
            vec![("a.rs:5".to_owned(), "01M7BR4JX3EZVXK1A6JD49NB6Q".to_owned())]
        );
    }

    // frob:tests crates/frob-land/src/cited_tickets.rs::cited_in_diff
    #[test]
    fn ignores_deleted_files_and_bare_directive() {
        let diff = "+++ /dev/null\n+// frob:ticket 01M7BR4JX3EZVXK1A6JD49NB6Q\n+++ b/b.rs\n@@ -0,0 +1 @@\n+// frob:ticket\n";
        assert!(cited_in_diff(diff).is_empty());
    }
}
