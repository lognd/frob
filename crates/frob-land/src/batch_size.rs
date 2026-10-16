//! Adaptive batch size of the merge train (frob:ticket 01M4Z1MYJSZJ8CMH8NEA8K30K4).
//!
//! Additive increase on a green train, multiplicative decrease on a red one,
//! clamped to `[1, train_max]`. The controller is pure: it maps the previous
//! size and the last outcome to the next size, and its state serializes into
//! the train state file.

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// How the last train ended.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    /// The combined tree verified.
    Green,
    /// The combined tree was red and a bisect was needed.
    Red,
}

/// Next batch size from the previous one: +1 on green, halved on red, clamped to `[1, max]`.
// frob:ticket 01M4Z1MYJSZJ8CMH8NEA8K30K4
#[must_use]
pub fn next_size(prev: usize, outcome: Outcome, max: usize) -> usize {
    let max = max.max(1);
    let next = match outcome {
        Outcome::Green => prev.saturating_add(1),
        Outcome::Red => prev / 2,
    };
    let clamped = next.clamp(1, max);
    tracing::debug!(prev, ?outcome, max, next = clamped, "train batch size");
    clamped
}

/// Serializable controller state: the current size and its cap.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct BatchSize {
    /// The size the next train should take.
    pub size: usize,
    /// The cap (`[land] train_max`).
    pub max: usize,
}

impl BatchSize {
    /// A controller starting at size 1 under the cap `max`.
    #[must_use]
    pub fn new(max: usize) -> Self {
        Self {
            size: 1,
            max: max.max(1),
        }
    }

    /// Fold the last train's outcome into the size and return the new size.
    pub fn record(&mut self, outcome: Outcome) -> usize {
        self.size = next_size(self.size, outcome, self.max);
        self.size
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    // frob:tests crates/frob-land/src/batch_size.rs::next_size
    fn grows_by_one_up_to_the_cap() {
        let mut s = 1;
        let seen: Vec<usize> = (0..10)
            .map(|_| {
                s = next_size(s, Outcome::Green, 8);
                s
            })
            .collect();
        assert_eq!(seen, [2, 3, 4, 5, 6, 7, 8, 8, 8, 8]);
    }

    #[test]
    // frob:tests crates/frob-land/src/batch_size.rs::next_size
    fn halves_on_red_and_never_below_one() {
        assert_eq!(next_size(8, Outcome::Red, 8), 4);
        assert_eq!(next_size(5, Outcome::Red, 8), 2);
        assert_eq!(next_size(1, Outcome::Red, 8), 1);
        assert_eq!(next_size(0, Outcome::Red, 8), 1);
    }

    #[test]
    // frob:tests crates/frob-land/src/batch_size.rs::next_size
    fn never_exceeds_a_cap_of_three() {
        assert_eq!(next_size(3, Outcome::Green, 3), 3);
        assert_eq!(next_size(9, Outcome::Green, 3), 3);
        assert_eq!(next_size(2, Outcome::Green, 0), 1);
    }

    #[test]
    // frob:tests crates/frob-land/src/batch_size.rs::BatchSize.record
    fn state_round_trips_and_records() {
        let mut b = BatchSize::new(3);
        assert_eq!(b.record(Outcome::Green), 2);
        assert_eq!(b.record(Outcome::Green), 3);
        assert_eq!(b.record(Outcome::Green), 3);
        assert_eq!(b.record(Outcome::Red), 1);
        let json = serde_json::to_string(&b).unwrap();
        assert_eq!(serde_json::from_str::<BatchSize>(&json).unwrap(), b);
    }
}
