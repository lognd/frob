//! The host trait the CI and DK `#[rule]` declarations evaluate against.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

/// What a CI or DK rule may ask of its product: how many subjects the analysis examined.
///
/// The rules are evaluated in one pass over the workflows and Dockerfiles, so the declared rules
/// are staged (never run one by one); `ci_subjects_of` is what the must-measure rules report from.
pub trait CiHost {
    /// Subjects the CI pass examined for rule `id` on this run (0 when it examined none).
    fn ci_subjects_of(&self, id: &str) -> usize;
}
