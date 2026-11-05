//! MDL033: A match over an `open` outcome set has neither `unknown` nor `_`.

// frob:ticket 01M6P033KB0H2X52QC73P40F6M

use gob_rules::{Out, RepoRule, rule};

use crate::host::MdlHost;

/// A match over an `open` outcome set has neither `unknown` nor `_`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "MDL033",
    slug = "mdl-open-match",
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
pub struct Mdl033;

impl<P: ?Sized + MdlHost> RepoRule<P> for Mdl033 {
    /// The verdict is computed by the planning pass in `plan_check`; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
