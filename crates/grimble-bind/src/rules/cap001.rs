//! CAP001: Code a node owns uses a capability atom the node does not grant.

// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// Code a node owns uses a capability atom the node does not grant.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CAP001",
    slug = "cap-undeclared",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cap001;

impl<P: ?Sized + BindHost> RepoRule<P> for Cap001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
