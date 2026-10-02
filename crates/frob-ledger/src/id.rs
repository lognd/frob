//! Ticket and event identifiers: Crockford ULIDs, plus the human handle.
//!
//! The full 26-character ULID is the only persisted form (decision D24).
//! The handle is the shortest unique suffix of the ULID's random part (its
//! last 16 characters), shown as `~xxxxxxx`, at least `min_len` characters
//! long, and never written to any file.

use std::fmt;
use std::str::FromStr;
use std::sync::{Mutex, OnceLock};

use schemars::JsonSchema;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use ulid::{Generator, Ulid};

/// Number of characters in a ULID.
pub const ULID_LEN: usize = 26;
/// Number of characters in the random part of a ULID (the handle alphabet).
pub const RANDOM_LEN: usize = 16;
/// Default minimum handle length (`[tickets] handle_min_len`).
pub const DEFAULT_HANDLE_MIN_LEN: usize = 7;

/// Why a string is not a ULID.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("`{input}` is not a 26-character Crockford ULID")]
pub struct ParseIdError {
    /// The rejected input.
    pub input: String,
}

macro_rules! ulid_newtype {
    ($(#[$meta:meta])* $name:ident) => {
        $(#[$meta])*
        #[derive(Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
        pub struct $name(Ulid);

        impl $name {
            /// Wrap an existing ULID.
            pub const fn from_ulid(ulid: Ulid) -> Self {
                Self(ulid)
            }

            /// The inner ULID.
            pub const fn ulid(&self) -> Ulid {
                self.0
            }

            /// Creation time encoded in the ULID, in milliseconds since the epoch.
            pub const fn timestamp_ms(&self) -> u64 {
                self.0.timestamp_ms()
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(&self.0.to_string())
            }
        }

        impl fmt::Debug for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                write!(f, "{}({})", stringify!($name), self.0)
            }
        }

        impl FromStr for $name {
            type Err = ParseIdError;

            fn from_str(s: &str) -> Result<Self, Self::Err> {
                if s.len() != ULID_LEN {
                    return Err(ParseIdError { input: s.to_owned() });
                }
                Ulid::from_string(&s.to_ascii_uppercase())
                    .map(Self)
                    .map_err(|_| ParseIdError { input: s.to_owned() })
            }
        }

        impl Serialize for $name {
            fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
                s.serialize_str(&self.0.to_string())
            }
        }

        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
                let text = String::deserialize(d)?;
                text.parse().map_err(serde::de::Error::custom)
            }
        }

        impl JsonSchema for $name {
            fn schema_name() -> std::borrow::Cow<'static, str> {
                stringify!($name).into()
            }

            fn json_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
                schemars::json_schema!({
                    "type": "string",
                    "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
                    "description": "26-character Crockford ULID"
                })
            }
        }
    };
}

ulid_newtype!(
    /// The id of a ticket: a ULID minted at creation, also its directory name.
    TicketId
);
ulid_newtype!(
    /// The id of an event: a ULID, also its file stem.
    EventId
);

/// One process-wide generator so ids minted in one run are strictly increasing.
fn generator() -> &'static Mutex<Generator> {
    static GEN: OnceLock<Mutex<Generator>> = OnceLock::new();
    GEN.get_or_init(|| Mutex::new(Generator::new()))
}

fn next_ulid() -> Ulid {
    let mut guard = generator()
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    // Overflow of the 80-bit random counter within one millisecond is not reachable.
    guard.generate().unwrap_or_else(|_| Ulid::new())
}

impl TicketId {
    /// Mint a fresh ticket id.
    pub fn mint() -> Self {
        let id = Self(next_ulid());
        tracing::debug!(ticket = %id, "ticket id minted");
        id
    }

    /// The random part: the last 16 characters, the alphabet of handles.
    pub fn random_part(&self) -> String {
        self.to_string().split_off(ULID_LEN - RANDOM_LEN)
    }
}

impl EventId {
    /// Mint a fresh event id.
    pub fn mint() -> Self {
        Self(next_ulid())
    }
}

/// A handle with its leading `~`, as shown to humans.
pub fn display_handle(suffix: &str) -> String {
    format!("~{suffix}")
}

/// Shortest-unique-suffix handles (without `~`) for every id, in input order.
///
/// Each handle is the shortest suffix of the random part that no other id
/// shares, never shorter than `min_len` (capped at 16).
pub fn compute_handles(ids: &[TicketId], min_len: usize) -> Vec<String> {
    let min_len = min_len.clamp(1, RANDOM_LEN);
    let randoms: Vec<String> = ids.iter().map(TicketId::random_part).collect();
    // Sort by reversed random part: neighbours share the longest suffixes.
    let mut order: Vec<usize> = (0..ids.len()).collect();
    let reversed: Vec<String> = randoms
        .iter()
        .map(|r| r.chars().rev().collect::<String>())
        .collect();
    order.sort_by(|&a, &b| reversed[a].cmp(&reversed[b]));
    let common = |a: &str, b: &str| a.chars().zip(b.chars()).take_while(|(x, y)| x == y).count();
    let mut out = vec![String::new(); ids.len()];
    for (pos, &i) in order.iter().enumerate() {
        let before = pos
            .checked_sub(1)
            .map_or(0, |p| common(&reversed[order[p]], &reversed[i]));
        let after = order
            .get(pos + 1)
            .map_or(0, |&n| common(&reversed[n], &reversed[i]));
        let need = (before.max(after) + 1).clamp(min_len, RANDOM_LEN);
        randoms[i][RANDOM_LEN - need..].clone_into(&mut out[i]);
    }
    out
}

#[cfg(test)]
#[allow(clippy::many_single_char_names)]
mod tests {
    use super::*;

    fn id(s: &str) -> TicketId {
        s.parse().expect("valid ulid")
    }

    #[test]
    fn parse_is_case_insensitive_and_canonical() {
        let a = id("01j9zk3m4n5p6q7r8s9t0v1w2x");
        assert_eq!(a.to_string(), "01J9ZK3M4N5P6Q7R8S9T0V1W2X");
        assert!("short".parse::<TicketId>().is_err());
        assert!("01J9ZK3M4N5P6Q7R8S9T0V1W2U".parse::<TicketId>().is_err());
    }

    #[test]
    fn minted_ids_increase() {
        let a = TicketId::mint();
        let b = TicketId::mint();
        assert!(a < b);
    }

    #[test]
    fn handles_lengthen_only_on_collision() {
        let a = id("01J9ZK3M4N0000000AAAAAAAAA");
        let b = id("01J9ZK3M4N0000000BBBBBBBBB");
        let c = id("01J9ZK3M4N0000000CCCCCCCCB");
        let h = compute_handles(&[a, b, c], 7);
        assert_eq!(h[0], "AAAAAAA");
        assert_eq!(h[0].len(), 7);
        // b and c differ in the last char, so 7 chars already disambiguate.
        assert_eq!(h[1].len(), 7);
        let d = id("01J9ZK3M4N0000000XXXXXXXXB");
        let e = id("01J9ZK3M4N0000000YYYYYYYXB");
        let h2 = compute_handles(&[d, e], 7);
        assert_eq!(h2[0].len(), 7, "{h2:?}");
        let f = id("01J9ZK3M4N0000000XXXXXXXXB");
        let g = id("01J9ZK3M4N0000001XXXXXXXXB");
        let h3 = compute_handles(&[f, g], 7);
        assert_eq!(h3[0].len(), 10, "{h3:?}");
        assert_ne!(h3[0], h3[1]);
    }
}
