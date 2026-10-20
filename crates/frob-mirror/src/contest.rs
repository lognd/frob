//! Revert backoff and contested fields (mirror.md 3.4, MIR-AUD-06; MIR002 is Advisory).
//!
//! A repository-owned field changed again by a non-mirror actor is not reverted at once every run.
//! The `n`-th re-application by the same actor is reverted only after `2^n` runs saw it (1, 2, 4)
//! and at most once a day. The third re-application makes the field contested for that item: no
//! further revert, and one pending proposal holds the latest value. A ledger event on the field,
//! an accept or a decline clears the contested state ([`ContestBook::clear`]). Everything here is
//! pure state: the caller persists the [`ContestBook`] and performs the revert or the proposal.

// frob:ticket 01M4052TG0DWTW9KA7A1CH4ED3

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use tracing::{debug, info};

/// The advisory diagnostic code under which contested fields are listed in mirror status.
pub const CODE: &str = "MIR002";

/// Re-applications by one actor after which the field becomes contested.
pub const CONTEST_AFTER: u32 = 3;

/// Seconds that must pass between two reverts of the same field.
pub const REVERT_SPACING_SECS: i64 = 86_400;

/// What one run saw for a repository-owned field of one item.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Observed {
    /// The tracker value matches the projection.
    Clean,
    /// A non-mirror actor holds a different value.
    Diverged {
        /// Tracker user id (or automation id) holding the value.
        actor_id: String,
        /// The full divergent value.
        value: String,
    },
}

/// What to do about the field this run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Decision {
    /// Nothing to write or record this run.
    Quiet,
    /// Backing off: the divergence has not yet been seen for enough runs or a day has not passed.
    Wait,
    /// Revert the field to the projection now.
    Revert,
    /// The field is contested; record or update the one pending proposal with this value.
    Propose {
        /// The latest value the actor holds.
        value: String,
    },
}

/// Per (item, field) backoff and contest state.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FieldState {
    /// The actor whose re-applications are counted.
    pub actor_id: String,
    /// Times this actor re-applied the value after a mirror revert.
    pub reapplications: u32,
    /// Runs that saw the current divergence.
    pub runs_seen: u32,
    /// Unix seconds of the last revert, for the once-a-day cap.
    pub last_revert: Option<i64>,
    /// Whether the last run saw the field diverged.
    pub diverged: bool,
    /// The latest divergent value.
    pub latest_value: String,
    /// Whether the mirror stopped reverting (MIR002).
    pub contested: bool,
}

/// A contested field, the shape mirror status lists.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ContestedField {
    /// The tracker item (issue) the field belongs to.
    pub item: String,
    /// The contested field.
    pub field: String,
    /// The actor that keeps re-applying it.
    pub actor_id: String,
    /// The latest value, held by the pending proposal.
    pub latest_value: String,
}

/// Why a contested state ends.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClearCause {
    /// A new ledger event touched the field.
    LedgerEvent,
    /// The pending proposal was accepted.
    Accept,
    /// The pending proposal was declined.
    Decline,
}

/// All backoff and contest state, persisted by the caller (serde).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContestBook {
    /// State per (item, field).
    states: BTreeMap<String, BTreeMap<String, FieldState>>,
}

/// Runs the `reapplications`-th revert waits for: 1, 2, 4.
fn wait_runs(reapplications: u32) -> u32 {
    1u32 << reapplications.min(CONTEST_AFTER)
}

impl ContestBook {
    /// Records what one run saw for `item.field` at unix time `now` and decides what to do.
    pub fn observe(&mut self, item: &str, field: &str, seen: Observed, now: i64) -> Decision {
        let fields = self.states.entry(item.to_owned()).or_default();
        let (actor_id, value) = match seen {
            Observed::Clean => {
                if let Some(st) = fields.get_mut(field) {
                    st.diverged = false;
                    st.runs_seen = 0;
                    if st.last_revert.is_none() && !st.contested {
                        fields.remove(field);
                    }
                }
                self.prune(item);
                return Decision::Quiet;
            }
            Observed::Diverged { actor_id, value } => (actor_id, value),
        };
        let st = fields
            .entry(field.to_owned())
            .and_modify(|st| {
                if st.actor_id != actor_id {
                    debug!(item, field, "contest: new actor, counters restart");
                    st.actor_id.clone_from(&actor_id);
                    st.reapplications = 0;
                    st.runs_seen = 0;
                    st.diverged = false;
                    st.contested = false;
                }
            })
            .or_insert_with(|| FieldState {
                actor_id: actor_id.clone(),
                reapplications: 0,
                runs_seen: 0,
                last_revert: None,
                diverged: false,
                latest_value: value.clone(),
                contested: false,
            });
        if !st.diverged && st.last_revert.is_some() && !st.contested {
            st.reapplications += 1;
            info!(
                item,
                field,
                n = st.reapplications,
                "contest: actor re-applied the field"
            );
        }
        st.diverged = true;
        st.runs_seen += 1;
        let changed = st.latest_value != value;
        st.latest_value = value;
        if st.contested || st.reapplications >= CONTEST_AFTER {
            let newly = !st.contested;
            st.contested = true;
            if newly {
                info!(
                    item,
                    field,
                    code = CODE,
                    "contest: field contested, reverts stop"
                );
            }
            return if newly || changed {
                Decision::Propose {
                    value: st.latest_value.clone(),
                }
            } else {
                Decision::Quiet
            };
        }
        let spaced = st
            .last_revert
            .is_none_or(|t| now.saturating_sub(t) >= REVERT_SPACING_SECS);
        if st.runs_seen >= wait_runs(st.reapplications) && spaced {
            st.last_revert = Some(now);
            info!(item, field, "contest: revert due");
            Decision::Revert
        } else {
            debug!(item, field, runs = st.runs_seen, "contest: backing off");
            Decision::Wait
        }
    }

    /// Clears the contested state (and the counters) of `item.field`; true when one existed.
    pub fn clear(&mut self, item: &str, field: &str, cause: ClearCause) -> bool {
        let removed = self
            .states
            .get_mut(item)
            .is_some_and(|f| f.remove(field).is_some());
        if removed {
            info!(item, field, ?cause, "contest: cleared");
            self.prune(item);
        }
        removed
    }

    /// The contested fields, sorted, ready to feed mirror status.
    pub fn contested(&self) -> Vec<ContestedField> {
        let mut out: Vec<ContestedField> = self
            .states
            .iter()
            .flat_map(|(item, fields)| {
                fields
                    .iter()
                    .filter(|(_, st)| st.contested)
                    .map(move |(field, st)| ContestedField {
                        item: item.clone(),
                        field: field.clone(),
                        actor_id: st.actor_id.clone(),
                        latest_value: st.latest_value.clone(),
                    })
            })
            .collect();
        out.sort();
        out
    }

    /// Whether `item.field` is contested.
    pub fn is_contested(&self, item: &str, field: &str) -> bool {
        self.states
            .get(item)
            .and_then(|f| f.get(field))
            .is_some_and(|st| st.contested)
    }

    /// Drops an item's map when it has no fields left.
    fn prune(&mut self, item: &str) {
        if self.states.get(item).is_some_and(BTreeMap::is_empty) {
            self.states.remove(item);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const DAY: i64 = REVERT_SPACING_SECS;

    fn div(actor: &str, v: &str) -> Observed {
        Observed::Diverged {
            actor_id: actor.into(),
            value: v.into(),
        }
    }

    // frob:tests ContestBook::observe
    #[test]
    fn reverts_after_one_two_and_four_runs_at_most_daily() {
        let mut b = ContestBook::default();
        let mut t = 0;
        // First divergence: revert on the first run.
        assert_eq!(b.observe("7", "title", div("5", "a"), t), Decision::Revert);
        assert_eq!(b.observe("7", "title", Observed::Clean, t), Decision::Quiet);
        // Re-application 1: wait 2 runs.
        t += DAY;
        assert_eq!(b.observe("7", "title", div("5", "b"), t), Decision::Wait);
        t += DAY;
        assert_eq!(b.observe("7", "title", div("5", "b"), t), Decision::Revert);
        assert_eq!(b.observe("7", "title", Observed::Clean, t), Decision::Quiet);
        // Re-application 2: wait 4 runs; runs inside one day never revert.
        for _ in 0..3 {
            t += DAY;
            assert_eq!(b.observe("7", "title", div("5", "c"), t), Decision::Wait);
        }
        t += DAY;
        assert_eq!(b.observe("7", "title", div("5", "c"), t), Decision::Revert);
    }

    // frob:tests ContestBook::observe
    #[test]
    fn at_most_one_revert_per_day() {
        let mut b = ContestBook::default();
        assert_eq!(b.observe("7", "title", div("5", "a"), 0), Decision::Revert);
        b.observe("7", "title", Observed::Clean, 10);
        assert_eq!(b.observe("7", "title", div("5", "b"), 20), Decision::Wait);
        // Two runs seen but under a day since the revert: still waiting.
        assert_eq!(b.observe("7", "title", div("5", "b"), 30), Decision::Wait);
        assert_eq!(
            b.observe("7", "title", div("5", "b"), DAY),
            Decision::Revert
        );
    }

    // frob:tests ContestBook::observe
    #[test]
    fn third_reapplication_contests_and_proposes_latest_value() {
        let mut b = ContestBook::default();
        let mut t = 0;
        let mut reverts = 0;
        for round in 0..3 {
            for _ in 0..8 {
                t += DAY;
                if b.observe("7", "title", div("5", &format!("v{round}")), t) == Decision::Revert {
                    reverts += 1;
                    break;
                }
            }
            b.observe("7", "title", Observed::Clean, t);
        }
        assert_eq!(reverts, 3);
        t += DAY;
        let d = b.observe("7", "title", div("5", "latest"), t);
        assert_eq!(
            d,
            Decision::Propose {
                value: "latest".into()
            }
        );
        assert!(b.is_contested("7", "title"));
        // No further revert, no repeated proposal for the same value.
        for _ in 0..10 {
            t += DAY;
            assert_eq!(
                b.observe("7", "title", div("5", "latest"), t),
                Decision::Quiet
            );
        }
        // A newer value updates the one pending proposal.
        t += DAY;
        assert_eq!(
            b.observe("7", "title", div("5", "newer"), t),
            Decision::Propose {
                value: "newer".into()
            }
        );
        let c = b.contested();
        assert_eq!(c.len(), 1);
        assert_eq!(c[0].latest_value, "newer");
        assert_eq!(c[0].item, "7");
    }

    fn contested_book() -> ContestBook {
        let mut b = ContestBook::default();
        let mut t = 0;
        for _ in 0..3 {
            for _ in 0..8 {
                t += DAY;
                if b.observe("7", "title", div("5", "x"), t) == Decision::Revert {
                    break;
                }
            }
            b.observe("7", "title", Observed::Clean, t);
        }
        t += DAY;
        b.observe("7", "title", div("5", "x"), t);
        assert!(b.is_contested("7", "title"));
        b
    }

    // frob:tests ContestBook::clear
    #[test]
    fn ledger_event_accept_or_decline_clears_contested() {
        for cause in [
            ClearCause::LedgerEvent,
            ClearCause::Accept,
            ClearCause::Decline,
        ] {
            let mut b = contested_book();
            assert!(b.clear("7", "title", cause));
            assert!(!b.is_contested("7", "title"));
            assert!(b.contested().is_empty());
            assert!(!b.clear("7", "title", cause));
            // Counters restart: the next divergence reverts at once.
            assert_eq!(
                b.observe("7", "title", div("5", "y"), 9 * DAY),
                Decision::Revert
            );
        }
    }

    // frob:tests ContestBook::observe
    #[test]
    fn a_different_actor_restarts_the_count_and_state_round_trips() {
        let mut b = ContestBook::default();
        assert_eq!(b.observe("7", "title", div("5", "a"), 0), Decision::Revert);
        b.observe("7", "title", Observed::Clean, 1);
        assert_eq!(b.observe("7", "title", div("6", "b"), 2), Decision::Wait);
        let json = serde_json::to_string(&b).unwrap();
        let back: ContestBook = serde_json::from_str(&json).unwrap();
        assert_eq!(back, b);
        assert_eq!(CODE, "MIR002");
    }
}
