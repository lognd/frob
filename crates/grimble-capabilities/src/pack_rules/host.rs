//! The host trait the PACK `#[rule]` declarations evaluate against.

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

/// What a PACK rule may ask of its product: how many subjects the pack pass examined.
///
/// The pack pass evaluates every PACK rule in one sweep (see [`super::evaluate`]), so the declared
/// rules are staged and never run one by one.
pub trait PackHost {
    /// Subjects the pack pass examined for rule `id` on this run (0 when it examined none).
    fn subjects_of(&self, id: &str) -> usize;
}
