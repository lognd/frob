//! The host trait the PATH `#[rule]` declarations evaluate against.

// frob:ticket 01M59A2N1QCS2E5GPGD09V34R1

/// What a PATH rule may ask of its product: how many files the scan examined.
///
/// The three rules are evaluated in one pass over the walk, so the declared rules are staged
/// (never run one by one); `path_subjects_of` is what the must-measure rules report from.
pub trait PathHost {
    /// Files the PATH pass examined for rule `id` on this run (0 when it examined none).
    fn path_subjects_of(&self, id: &str) -> usize;
}
