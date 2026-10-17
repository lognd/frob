use gob_rules::{FileInterner, Finding, RelayRule, rule};

pub trait ObligationHost {}

#[rule(
    id = "TODO001",
    slug = "bare-work-marker",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = ObligationHost,
    version = 1,
    since = "0.0.0",
)]
pub struct Todo001;

impl<P: ?Sized + ObligationHost> RelayRule<P> for Todo001 {
    fn relay(&self, _host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        Vec::new()
    }

    fn examined(&self, _host: &P) -> Option<usize> {
        Some(0)
    }
}

fn main() {}
