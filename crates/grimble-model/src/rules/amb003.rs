//! AMB003: A `retry` or `restart` ambient policy has no `max` or no `else` tail.

// frob:ticket 01M6P033P70RJ9JZJ5NWV5AWNB

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A `retry` or `restart` ambient policy has no `max` or no `else` tail.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "AMB003",
    slug = "amb-unbounded",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = MdlHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Amb003;

impl<P: ?Sized + MdlHost> RepoRule<P> for Amb003 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
