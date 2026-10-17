//! Fixture stage-emitted `must_measure` rule, bound through `RuleSet::stage_counted` (~Z0816YV).

use gob_rules::{Out, RepoRule, rule};

use crate::Host;

#[rule(
    id = "STC001",
    slug = "stage-counted",
    severity = Warn,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = Host,
    version = 1,
    since = "0.1.0",
)]
/// Stage-emitted; its subject count is read from the product.
pub struct Stc001;

impl<P: ?Sized + Host> RepoRule<P> for Stc001 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + Host> gob_rules::Measured<P> for Stc001 {
    fn subjects(&self, host: &P) -> usize {
        host.items()
    }
}
