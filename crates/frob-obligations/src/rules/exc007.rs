//! `EXC007`: a defer whose ticket is not in the ledger (emitted by exception handling).

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Out, RepoRule, rule};

use crate::host::ObligationHost;

/// A defer whose ticket is not in the ledger (emitted by exception handling).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "EXC007",
    slug = "defer-ticket-missing",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = ObligationHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Exc007;

/// The finding is raised by exception handling ([`crate::apply_exceptions`]); this declaration registers the id.
impl<P: ?Sized + ObligationHost> RepoRule<P> for Exc007 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
