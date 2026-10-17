//! `TEST001`: a `frob:tests` directive names nothing the graph can find.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_rules::{Finding, RelayRule, rule};
use gob_text::FileInterner;

use crate::host::TestsHost;
use crate::rule::test001_with_sources;

/// A `frob:tests` directive whose target resolves to no test (or, inside a test, to no symbol).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TEST001",
    slug = "tests-target-missing",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = TestsHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Test001;

impl<P: ?Sized + TestsHost> RelayRule<P> for Test001 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let found = test001_with_sources(host.directives(), host.graph(), &|p| host.read_source(p));
        tracing::debug!(found = found.len(), "TEST001 evaluated");
        found
    }
}
