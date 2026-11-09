use gob_rules::{FileCx, FileRule, Out, rule};

pub trait ObligationHost {}

#[rule(
    id = "ABCDEFGHIJKL001",
    slug = "bare-work-marker",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = ObligationHost,
    version = 1,
    since = "0.0.0",
)]
pub struct Abcdefghijkl001;

impl<P: ?Sized + ObligationHost> FileRule<P> for Abcdefghijkl001 {
    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {}
}

fn main() {}
