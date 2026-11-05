//! AMB005: An ambient class or a root catch-all is a source in a waypoint outcome map.

// frob:ticket 01M6P033P70RJ9JZJ5NWV5AWNB

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An ambient class or a root catch-all is a source in a waypoint outcome map.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "AMB005",
    slug = "amb-overcatch",
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
pub struct Amb005;

impl<P: ?Sized + MdlHost> RepoRule<P> for Amb005 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
