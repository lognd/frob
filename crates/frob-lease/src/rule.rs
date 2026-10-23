//! `SCOPE001`: a diff touches paths outside the ticket's lease.

use gob_git::RelPath;
use gob_rules::{Finding, RuleDecl, RuleId, Severity};

use crate::model::Lease;
use crate::overlap::{ScopeMatcher, covers_foreign_fragments, glob_set, is_own_fragment};
use crate::rules::scope001::Scope001;

/// `SCOPE001`: one finding per path of `diff_paths` outside `lease.scope` and not in `shared`.
///
/// The caller supplies the diff (`gob_git::Repo::diff_names` of the worktree
/// against the base). A scope glob that does not parse matches nothing.
pub fn scope001(diff_paths: &[RelPath], lease: &Lease, shared: &[String]) -> Vec<Finding> {
    let id: RuleId = Scope001::DEF
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("declaration validates the id: {e}"));
    let scope: Vec<_> = lease
        .scope
        .iter()
        .filter(|g| {
            let skip = covers_foreign_fragments(g);
            if skip {
                tracing::warn!(ticket = %lease.ticket, glob = %g, "scope glob covering other tickets' fragments ignored");
            }
            !skip
        })
        .filter_map(|g| match ScopeMatcher::new(g) {
            Ok(m) => Some(m),
            Err(e) => {
                tracing::warn!(ticket = %lease.ticket, error = %e, "scope glob ignored");
                None
            }
        })
        .collect();
    let shared = glob_set(shared).unwrap_or_else(|e| {
        tracing::warn!(error = %e, "shared globs ignored");
        globset::GlobSet::empty()
    });
    diff_paths
        .iter()
        .filter(|p| {
            !scope.iter().any(|m| m.is_match(p.as_str()))
                && !shared.is_match(p.as_str())
                && !is_own_fragment(p.as_str(), lease.ticket)
        })
        .map(|p| {
            tracing::debug!(path = %p, ticket = %lease.ticket, "SCOPE001 finding");
            Finding::new(
                id.clone(),
                Severity::Error,
                None,
                format!(
                    "{p} is outside the scope lease of ticket {} ({}); widen the scope or move the change",
                    lease.ticket,
                    lease.scope.join(", ")
                ),
                p.as_str(),
            )
        })
        .collect()
}
