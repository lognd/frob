//! [`Stamp`]: the one instant type.

use std::fmt;
use std::str::FromStr;
use std::time::{Duration, SystemTime};

use jiff::Timestamp;
use schemars::JsonSchema;
use serde::{Deserialize, Deserializer, Serialize, Serializer};

/// An RFC 3339 instant in UTC (`Z`), held at the precision the clock returned (nanoseconds on most systems).
///
/// `Display`, serde and `FromStr` are the whole-second text of ledger, lease and evidence files
/// (`FromStr` keeps any fraction it is given); [`Stamp::precise`] is the sub-second text of
/// `frob.lock` acks and telemetry. No persisted format changed when the type moved here.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Stamp(Timestamp);

impl Stamp {
    /// An instant from Unix seconds (clamped into jiff's range).
    pub fn from_unix(secs: i64) -> Self {
        Self(Timestamp::from_second(secs).unwrap_or(Timestamp::UNIX_EPOCH))
    }

    /// This instant truncated to whole seconds, the precision of ledger, lease and evidence files.
    #[must_use]
    pub fn seconds(self) -> Self {
        Self::from_unix(self.unix())
    }

    /// RFC 3339 text with the sub-second fraction when there is one (`...:28.931959538Z`), as `frob.lock` acks write it.
    pub fn precise(self) -> String {
        self.0.to_string()
    }

    /// Unix seconds.
    pub fn unix(self) -> i64 {
        self.0.as_second()
    }

    /// The same instant as a [`SystemTime`], for comparing with file times.
    pub fn to_system_time(self) -> SystemTime {
        let secs = self.unix();
        match u64::try_from(secs) {
            Ok(s) => SystemTime::UNIX_EPOCH + Duration::from_secs(s),
            Err(_) => SystemTime::UNIX_EPOCH - Duration::from_secs(secs.unsigned_abs()),
        }
    }

    /// The instant `secs` seconds later (earlier when negative), saturating at jiff's range.
    #[must_use]
    pub fn plus_seconds(self, secs: i64) -> Self {
        Self::from_unix(self.unix().saturating_add(secs))
    }

    pub(crate) fn from_timestamp(t: Timestamp) -> Self {
        Self(t)
    }

    pub(crate) fn timestamp(self) -> Timestamp {
        self.0
    }
}

impl fmt::Display for Stamp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0.strftime("%Y-%m-%dT%H:%M:%SZ"))
    }
}

impl FromStr for Stamp {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        s.parse::<Timestamp>()
            .map(Self)
            .map_err(|e| format!("`{s}` is not an RFC 3339 timestamp: {e}"))
    }
}

impl Serialize for Stamp {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.collect_str(self)
    }
}

impl<'de> Deserialize<'de> for Stamp {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        String::deserialize(d)?
            .parse()
            .map_err(serde::de::Error::custom)
    }
}

impl JsonSchema for Stamp {
    fn schema_name() -> std::borrow::Cow<'static, str> {
        "Stamp".into()
    }

    fn json_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
        schemars::json_schema!({ "type": "string", "format": "date-time" })
    }
}
