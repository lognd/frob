//! Fixture stage-emitted rule, bound only through `RuleSet::stage_when` (~Z0816YV).

use gob_rules::{Out, RepoRule, rule};

use crate::Host;

#[rule(
    id = "STG001",
    slug = "stage-one",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = Host,
    version = 1,
    since = "0.1.0",
)]
/// Stage-emitted; never run by the pipeline.
pub struct Stg001;

impl<P: ?Sized + Host> RepoRule<P> for Stg001 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
