//! `COV003`: alias of TEST001; declared so references resolve, never emitted.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Out, RepoRule, rule};

use crate::host::ObligationHost;

/// Alias of TEST001; declared so references resolve, never emitted.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COV003",
    slug = "tests-names-missing-test",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ObligationHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cov003;

/// The finding is raised by exception handling ([`crate::apply_exceptions`]); this declaration registers the id.
impl<P: ?Sized + ObligationHost> RepoRule<P> for Cov003 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
