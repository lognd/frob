//! PLAN042: An outcome map targets a variant the step does not declare.

// frob:ticket 01M6P033S4VV7JST84C3Q0TF80

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// An outcome map targets a variant the step does not declare.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PLAN042",
    slug = "plan-unproducible-mapping",
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
pub struct Plan042;

impl<P: ?Sized + MdlHost> RepoRule<P> for Plan042 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
