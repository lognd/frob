//! SYS009: One end of a flow binds no code while the other does.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::BindHost;

/// One end of a flow binds no code while the other does.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SYS009",
    slug = "sys-flow-end-unbound",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = BindHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Sys009;

impl<P: ?Sized + BindHost> RepoRule<P> for Sys009 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
