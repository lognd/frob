//! The host the declared rules of frob's rule crates run against: [`FrobInputs`] behind one trait.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use frob_ack::{AckHost, Inputs};
use frob_obligations::{ObligationHost, ObligationInputs};
use frob_tests::TestsHost;
use gob_directives::DirectiveRecord;
use gob_symbols::SymbolGraph;

use crate::snapshot::FrobInputs;

/// Everything the migrated rule crates ask of frob: obligations, ack and test-coverage facts.
pub trait FrobHost: ObligationHost + AckHost + TestsHost {}

impl<T: ObligationHost + AckHost + TestsHost + ?Sized> FrobHost for T {}

impl ObligationHost for FrobInputs {
    fn obligations(&self) -> ObligationInputs<'_> {
        FrobInputs::obligations(self)
    }
}

impl AckHost for FrobInputs {
    fn inputs(&self) -> &Inputs {
        &self.ack
    }
}

impl TestsHost for FrobInputs {
    fn directives(&self) -> &[DirectiveRecord] {
        &self.directives
    }

    fn graph(&self) -> &SymbolGraph {
        &self.ack.graph
    }

    fn read_source(&self, path: &str) -> Option<String> {
        std::fs::read_to_string(self.root.join(path)).ok()
    }
}
