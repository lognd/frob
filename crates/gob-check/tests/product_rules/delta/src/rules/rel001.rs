//! Fixture relay repo rule: relays findings a sibling stage already computed (~Z0816YV).

use gob_rules::{FileInterner, Finding, RelayRule, rule};

use crate::Host;

#[rule(
    id = "REL001",
    slug = "relay-one",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = project,
    host = Host,
    version = 1,
    since = "0.1.0",
)]
/// Relays the findings the sibling stage computed.
pub struct Rel001;

impl<P: ?Sized + Host> RelayRule<P> for Rel001 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        host.staged()
    }
    fn examined(&self, host: &P) -> Option<usize> {
        Some(host.staged().len())
    }
}
