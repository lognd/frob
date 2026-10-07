use gob_rules::{Out, RepoRule, rule};

pub trait ObligationHost {}

#[rule(
    id = "TODO001",
    slug = "bare-work-marker",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = ObligationHost,
    version = 1,
    since = "0.0.0",
)]
pub struct Todo001;

impl<P: ?Sized + ObligationHost> RepoRule<P> for Todo001 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

fn main() {}
