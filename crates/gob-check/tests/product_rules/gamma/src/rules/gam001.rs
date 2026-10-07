//! Fixture measured repo rule with product-fact applicability.

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::Host;

#[rule(
    id = "GAM001",
    slug = "gamma-one",
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
/// Fires once when the host holds no item, and counts the items it measured.
pub struct Gam001;

impl<P: ?Sized + Host> RepoRule<P> for Gam001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        if host.items() == 0 {
            out.note("no items");
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        host.disabled()
            .then(|| "the product has no item store configured".to_owned())
    }
}

impl<P: ?Sized + Host> Measured<P> for Gam001 {
    fn subjects(&self, host: &P) -> usize {
        host.items()
    }
}
