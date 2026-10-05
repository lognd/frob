//! The wall-clock and local-zone reads of the whole workspace live in this file and nowhere else.

#![allow(
    clippy::disallowed_methods,
    reason = "gob-time is the one crate allowed to read the wall clock and the local zone (docs/design/time.md section 3); every other crate takes a Clock"
)]

/// Unix seconds now.
pub(crate) fn unix_seconds() -> i64 {
    jiff::Timestamp::now().as_second()
}

/// Unix nanoseconds now, zero before the epoch.
pub(crate) fn unix_nanos() -> u128 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos())
}

/// The machine's local zone.
pub(crate) fn local_zone() -> jiff::tz::TimeZone {
    jiff::tz::TimeZone::system()
}
