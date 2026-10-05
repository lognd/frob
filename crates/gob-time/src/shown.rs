//! [`Shown`]: render-only local time; the only conversion to the user's zone.

use std::fmt;

use crate::Stamp;

/// A [`Stamp`] displayed in a local zone; it only produces text and never converts back to data.
#[derive(Debug, Clone, Copy)]
pub struct Shown {
    at: Stamp,
    /// A fixed offset in seconds east of UTC, or `None` for the machine's zone.
    offset: Option<i32>,
}

impl Shown {
    /// `at` in the machine's local zone, for the rendering layer only.
    pub fn local(at: Stamp) -> Self {
        Self { at, offset: None }
    }

    /// `at` at a fixed offset east of UTC in seconds; deterministic, for tests and fixed-zone output.
    pub fn at_offset(at: Stamp, seconds_east: i32) -> Self {
        Self {
            at,
            offset: Some(seconds_east),
        }
    }
}

impl fmt::Display for Shown {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let tz = match self.offset {
            Some(secs) => match jiff::tz::Offset::from_seconds(secs) {
                Ok(o) => jiff::tz::TimeZone::fixed(o),
                Err(_) => jiff::tz::TimeZone::UTC,
            },
            None => crate::wall::local_zone(),
        };
        let zoned = self.at.timestamp().to_zoned(tz);
        write!(f, "{}", zoned.strftime("%Y-%m-%d %H:%M:%S %:z"))
    }
}
