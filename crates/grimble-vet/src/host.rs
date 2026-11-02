//! The host trait the VET `#[rule]` declarations evaluate against.

// frob:ticket 01M5A63T4BZ3XH842F3RDFJ929

/// What a VET rule may ask of its product: how many packages the vet pass examined.
///
/// The VET rules are evaluated in one pass over `Cargo.lock`, so the declared rules are staged
/// (never run one by one); `vet_subjects_of` is what the must-measure rules report from.
pub trait VetHost {
    /// Subjects the vet pass examined for rule `id` on this run (0 when it examined none).
    fn vet_subjects_of(&self, id: &str) -> usize;
}
