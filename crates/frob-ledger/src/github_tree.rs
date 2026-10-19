//! `TICK010`: a `.github/` tree on the ticket branch other than the generated nudge workflow.
// frob:ticket 01M4052VK08NTRJS6HZZ9B82RZ
//!
//! The ticket branch may carry exactly one `.github/` file, the nudge workflow of
//! [`crate::nudge`], and its bytes must equal [`crate::nudge::render`]. Anything else under
//! `.github/` (a second workflow, an action, a different byte) is an Error, because a workflow on
//! the ticket branch runs with the repository's token.

use gob_rules::{Finding, Severity};

use crate::error::Result;
use crate::layout::Layout;
use crate::ledger::Ledger;
use crate::legacy::{Tick010, id_of};
use crate::nudge::{NUDGE_PATH, NudgeSpec, render};

/// True when `path` is the `.github` directory's content (the tree is `.github/` at the branch root).
fn in_github_tree(path: &str) -> bool {
    path == ".github" || path.starts_with(".github/")
}

/// `TICK010` findings over `files` (path, bytes) of a ticket-branch tip against the expected nudge bytes.
///
/// A path outside `.github/` is ignored; the nudge path with exactly the `expected` bytes is clean; every other
/// `.github/` path, and the nudge path with other bytes, is an Error naming the path.
pub fn github_tree_findings(files: &[(String, Vec<u8>)], expected: &str) -> Vec<Finding> {
    files
        .iter()
        .filter(|(path, _)| in_github_tree(path))
        .filter_map(|(path, bytes)| {
            let msg = if path != NUDGE_PATH {
                format!(
                    "{path} is under .github/ on the ticket branch; only the generated {NUDGE_PATH} may be there \
                     (a workflow on this branch runs with the repository token); delete it"
                )
            } else if bytes != expected.as_bytes() {
                format!(
                    "{path} differs from the generated nudge workflow; do not edit it, regenerate it or delete it"
                )
            } else {
                return None;
            };
            Some(Finding::new(
                id_of(&Tick010),
                Severity::Error,
                None,
                msg,
                path,
            ))
        })
        .collect()
}

impl Ledger {
    /// `TICK010` findings for the ticket-branch tip against the nudge workflow `spec` renders; none outside the branch layout.
    ///
    /// # Errors
    ///
    /// Git read failures. A `spec` that cannot render is reported as a malformed-ledger error.
    pub fn github_tree_findings(&self, spec: &NudgeSpec) -> Result<Vec<Finding>> {
        // frob:ticket 01M4052VK08NTRJS6HZZ9B82RZ
        if self.layout() != Layout::Branch {
            return Ok(Vec::new());
        }
        let ref_name = self.ledger_ref()?;
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok(Vec::new());
        };
        let Some(tree) = self.tickets_tree(Some(tip))? else {
            return Ok(Vec::new());
        };
        let expected = render(spec)
            .map_err(|e| crate::error::LedgerError::malformed(NUDGE_PATH, e.to_string()))?;
        let mut files = Vec::new();
        for (rel, oid) in self.list_blobs(&tree.to_string())? {
            if in_github_tree(&rel) {
                files.push((rel, self.repo.read_blob(&oid)?));
            }
        }
        let out = github_tree_findings(&files, &expected);
        tracing::info!(
            github_files = files.len(),
            findings = out.len(),
            "ledger-branch-workflow scan finished"
        );
        Ok(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn expected() -> String {
        render(&NudgeSpec {
            ticket_branch: "frob/tickets".into(),
            bot_ids: vec![],
        })
        .unwrap()
    }

    // frob:tests github_tree_findings
    #[test]
    fn an_extra_github_file_is_an_error_naming_the_path() {
        let files = vec![(".github/workflows/ci.yml".to_owned(), b"x".to_vec())];
        let out = github_tree_findings(&files, &expected());
        assert_eq!(out.len(), 1);
        assert!(out[0].message.contains(".github/workflows/ci.yml"));
    }

    // frob:tests github_tree_findings
    #[test]
    fn an_edited_nudge_is_an_error() {
        let mut bytes = expected().into_bytes();
        bytes.push(b'#');
        let files = vec![(NUDGE_PATH.to_owned(), bytes)];
        assert_eq!(github_tree_findings(&files, &expected()).len(), 1);
    }

    // frob:tests github_tree_findings
    #[test]
    fn only_the_generated_nudge_is_clean() {
        let files = vec![
            (NUDGE_PATH.to_owned(), expected().into_bytes()),
            ("_unfiled/a.md".to_owned(), b"t".to_vec()),
        ];
        assert!(github_tree_findings(&files, &expected()).is_empty());
    }
}
