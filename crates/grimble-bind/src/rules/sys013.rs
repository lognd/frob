//! SYS013: An import or call edge between two owners with no flow between them.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// An import or call edge between two owners with no flow between them.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS013",
    slug = "sys-undeclared-flow",
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
pub struct Sys013;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys013 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
