//! The host trait the SYS `#[rule]` declarations evaluate against.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

/// What a SYS rule may ask of its product: how many subjects binding examined for a rule.
///
/// Binding evaluates every SYS rule in one pass over B, so the declared rules are staged (never
/// run one by one); `subjects_of` is what the must-measure rules report from.
pub trait BindHost {
    /// Subjects binding examined for rule `id` on this run (0 when it examined none).
    fn subjects_of(&self, id: &str) -> usize;
}
