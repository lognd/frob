//! `COV001`: a public function or method that no test reaches.

// frob:ticket 01M561ZF9TSJF59M2CAXW3KTP0

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::cov;
use crate::host::ObligationHost;

/// A public function or method that no test reaches.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COV001",
    slug = "untested-public-function",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [TestItems], min_fidelity = F2),
    host = ObligationHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cov001;

impl<P: ?Sized + ObligationHost> RepoRule<P> for Cov001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let inputs = host.obligations();
        cov::cov001(
            inputs.root,
            inputs.graph,
            inputs.directives,
            inputs.unity,
            out,
        );
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        // Without a file of a test-capable language there is nothing to require a verdict on.
        (!host.has_test_capable_files())
            .then(|| "no file of a language with a test capability".to_owned())
    }
}

impl<P: ?Sized + ObligationHost> Measured<P> for Cov001 {
    fn subjects(&self, host: &P) -> usize {
        cov::test_capable_files(host.obligations().graph)
    }
}
