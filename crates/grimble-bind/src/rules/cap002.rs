//! CAP002: A node grants a capability atom that no code it owns uses.

// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// A node grants a capability atom that no code it owns uses.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CAP002",
    slug = "cap-declared-unused",
    severity = Warn,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cap002;

impl<P: ?Sized + BindHost> RepoRule<P> for Cap002 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
