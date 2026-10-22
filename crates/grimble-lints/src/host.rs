//! The host traits the PATH, TIME and PAIR `#[rule]` declarations evaluate against.

// frob:ticket 01M59A2N1QCS2E5GPGD09V34R1
// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5
// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01

/// What a PATH rule may ask of its product: how many files the scan examined.
///
/// The three rules are evaluated in one pass over the walk, so the declared rules are staged
/// (never run one by one); `path_subjects_of` is what the must-measure rules report from.
pub trait PathHost {
    /// Files the PATH pass examined for rule `id` on this run (0 when it examined none).
    fn path_subjects_of(&self, id: &str) -> usize;
}

/// What a TIME rule may ask of its product: how many files the scan examined.
///
/// The two rules are evaluated in one pass over the walk, like the PATH rules.
pub trait TimeHost {
    /// Files the TIME pass examined for rule `id` on this run (0 when it examined none).
    fn time_subjects_of(&self, id: &str) -> usize;
}

/// What a PAIR rule may ask of its product: how many files the scan examined.
///
/// `PAIR001` is evaluated in one pass over the walk, like the PATH and TIME rules.
pub trait PairHost {
    /// Files the PAIR pass examined for rule `id` on this run (0 when it examined none).
    fn pair_subjects_of(&self, id: &str) -> usize;
}
