//! The host trait the `#[rule]` declarations of this crate evaluate against.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use frob_ledger::LedgerView;

use crate::ObligationInputs;

/// What the obligation rules may ask of their product: its inputs.
pub trait ObligationHost {
    /// Everything the rules read, borrowed from the product's snapshot.
    fn obligations(&self) -> ObligationInputs<'_>;

    /// Whether the walk holds a file of a test-capable language, readable or not; `COV001` is inapplicable otherwise.
    // frob:ticket 01M561ZF9TSJF59M2CAXW3KTP0
    fn has_test_capable_files(&self) -> bool {
        true
    }

    /// What the product knows about the ticket ledger; `None` when it keeps none (`TODO002` then has nothing to judge).
    // frob:ticket 01M561ZF9TSJF59M2CAXW3KTP0
    fn ledger_facts(&self) -> Option<LedgerView<'_>> {
        None
    }
}
