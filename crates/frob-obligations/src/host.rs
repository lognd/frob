//! The host trait the `#[rule]` declarations of this crate evaluate against.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use crate::ObligationInputs;

/// What the obligation rules may ask of their product: its inputs.
pub trait ObligationHost {
    /// Everything the rules read, borrowed from the product's snapshot.
    fn obligations(&self) -> ObligationInputs<'_>;
}
