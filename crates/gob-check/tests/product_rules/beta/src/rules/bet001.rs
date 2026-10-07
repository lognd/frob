//! Fixture repo rule.

use gob_rules::{Out, RepoRule, rule};

use crate::Host;

#[rule(
    id = "BET001",
    slug = "beta-one",
    severity = Warn,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = Host,
    version = 1,
    since = "0.1.0",
)]
/// Fires once when the host reports a bad repository.
pub struct Bet001;

impl<P: ?Sized + Host> RepoRule<P> for Bet001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        if host.bad_repo() {
            out.fire(0, "bad repository");
        }
    }
}
