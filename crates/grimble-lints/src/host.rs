//! The host traits the PATH, TIME, PAIR, ERR and UNITY `#[rule]` declarations evaluate against.

// frob:ticket 01M59A2N1QCS2E5GPGD09V34R1
// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5
// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01
// frob:ticket 01M5HPSP14N3NCX5TNA9XDR1GY
// frob:ticket 01M4MBJ35HGM0P2MH4B7YMB3EQ

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

/// What an ERR rule may ask of its product: how many files the scan examined.
///
/// `ERR001`, `ERR002` and `ERR003` are evaluated in one pass over the walk, like the PAIR rules.
pub trait ErrHost {
    /// Files the ERR pass examined for rule `id` on this run (0 when it examined none).
    fn err_subjects_of(&self, id: &str) -> usize;
}

/// What a UNITY rule may ask of its product: how many files the scan examined.
///
/// `UNITY201` and `UNITY202` are evaluated in one pass over the walk, like the PATH rules.
pub trait UnityHost {
    /// Files the UNITY pass examined for rule `id` on this run (0 when it examined none).
    fn unity_subjects_of(&self, id: &str) -> usize;
}
