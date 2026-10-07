//! Fixture file rule.

use gob_rules::{FileCx, FileRule, Out, rule};

use crate::Host;

#[rule(
    id = "ALP001",
    slug = "alpha-one",
    severity = Warn,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = Host,
    version = 1,
    since = "0.1.0",
)]
/// Fires once on any file whose text contains `bad`.
pub struct Alp001;

impl<P: ?Sized + Host> FileRule<P> for Alp001 {
    fn check(&self, cx: &FileCx<'_, P>, out: &mut Out<'_, Self>) {
        if let Some(at) = cx.text.find("bad") {
            out.fire(at, "bad word");
        }
    }
}
