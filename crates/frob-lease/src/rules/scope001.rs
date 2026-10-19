//! `SCOPE001`: a diff touches paths outside the ticket's lease

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Out, RepoRule, rule};

use crate::host::ScopeHost;

/// A diff touches paths outside the ticket's lease
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SCOPE001",
    slug = "path-outside-lease",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ScopeHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Scope001;

/// The finding is raised by [`crate::scope001`] from the `--ticket` scope, which reads the diff; this declaration registers the id.
impl<P: ?Sized + ScopeHost> RepoRule<P> for Scope001 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
