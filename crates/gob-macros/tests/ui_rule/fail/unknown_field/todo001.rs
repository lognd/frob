use gob_rules::{FileCx, FileRule, Out, rule};

pub trait ObligationHost {}

#[rule(
    id = "TODO001",
    slug = "bare-work-marker",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = ObligationHost,
    version = 1,
    flavour = Mild,
    since = "0.0.0",
)]
pub struct Todo001;

impl<P: ?Sized + ObligationHost> FileRule<P> for Todo001 {
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}

fn main() {}
