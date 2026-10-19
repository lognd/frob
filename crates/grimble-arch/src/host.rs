//! The host trait the CYCLE, LARGE and DEAD `#[rule]` declarations evaluate against.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

/// What an architecture rule may ask of its product: how many subjects the analysis examined.
///
/// The three rules are evaluated in one pass over the symbol graph, so the declared rules are
/// staged (never run one by one); `arch_subjects_of` is what the must-measure rules report from.
pub trait ArchHost {
    /// Subjects the architecture pass examined for rule `id` on this run (0 when it examined none).
    fn arch_subjects_of(&self, id: &str) -> usize;
}
