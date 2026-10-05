//! [`Day`]: the one calendar-day type, UTC by contract.

use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::Stamp;

/// A calendar day (`YYYY-MM-DD`) in UTC, the unit of targets, cycle bounds and release dates.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Day(jiff::civil::Date);

impl fmt::Display for Day {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl Day {
    /// The UTC calendar day containing `at`.
    pub fn of(at: Stamp) -> Self {
        Self(at.timestamp().to_zoned(jiff::tz::TimeZone::UTC).date())
    }

    /// The UTC calendar day of Unix time `secs`; the epoch day when out of range.
    pub fn from_unix(secs: i64) -> Self {
        Self::of(Stamp::from_unix(secs))
    }

    /// This day shifted by `days` (negative goes back); `Err` when the result leaves the calendar.
    ///
    /// # Errors
    ///
    /// A message when the shifted date is out of range.
    pub fn plus_days(self, days: i64) -> Result<Self, String> {
        self.0
            .checked_add(jiff::Span::new().days(days))
            .map(Self)
            .map_err(|e| format!("{self} plus {days} days is out of range: {e}"))
    }
}

impl FromStr for Day {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, String> {
        s.parse::<jiff::civil::Date>()
            .map(Self)
            .map_err(|e| format!("`{s}` is not a YYYY-MM-DD date: {e}"))
    }
}

impl Serialize for Day {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.collect_str(self)
    }
}

impl<'de> Deserialize<'de> for Day {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        String::deserialize(d)?
            .parse()
            .map_err(serde::de::Error::custom)
    }
}
