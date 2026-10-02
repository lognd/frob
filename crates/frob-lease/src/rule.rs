//! `SCOPE001`: a diff touches paths outside the ticket's lease.

use gob_git::RelPath;
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::model::Lease;
use crate::overlap::{glob_set, matcher};

/// A changed path lies outside the globs of the ticket's scope lease.
///
/// Widen the ticket's scope (`frob ticket update`) and re-acquire the lease, or
/// move the change to a ticket that owns the path. Paths matching
/// `[lease] shared_files` are exempt.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "SCOPE001",
    slug = "path-outside-lease",
    family = "SCOPE",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Scope001;

/// `SCOPE001`: one finding per path of `diff_paths` outside `lease.scope` and not in `shared`.
///
/// The caller supplies the diff (`gob_git::Repo::diff_names` of the worktree
/// against the base). A scope glob that does not parse matches nothing.
pub fn scope001(diff_paths: &[RelPath], lease: &Lease, shared: &[String]) -> Vec<Finding> {
    let id: RuleId = Scope001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let scope: Vec<_> = lease
        .scope
        .iter()
        .filter_map(|g| match matcher(g) {
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
        .filter(|p| !scope.iter().any(|m| m.is_match(p.as_str())) && !shared.is_match(p.as_str()))
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
