//! MDL005: A selector's path matches no file in the walk.
//!
//! One finding is reported per distinct selector, not per clause: a selector written in
//! several clauses lists every clause site (`path:line`) in the one message. Selectors under
//! different `accept` scopes stay separate so an exception parks only the finding it covers.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A selector's path matches no file in the walk.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL005",
    slug = "mdl-selector-no-file",
    severity = Warn,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = MdlHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Mdl005;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl005 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
