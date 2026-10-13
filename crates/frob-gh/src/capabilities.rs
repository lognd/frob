//! Live-measured GitHub behaviours (audit U1-U16): the capabilities record, with fixtures under `tests/fixtures/live`.

// frob:ticket 01M4059ZDWQRK47QXG5K0KYHP2

/// The capabilities record as JSON (facts U1-U16 plus the nudge permission finding).
pub const RECORD_JSON: &str = include_str!("../capabilities.json");

/// One measured fact: verdict, finding, and the recorded request/response summary.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct Fact {
    /// `U1`..`U16`.
    pub id: String,
    /// `verified`, `partial` or `unmeasurable`.
    pub verdict: String,
    /// What the code may rely on.
    pub finding: String,
    /// Request summary.
    pub request: String,
    /// Response summary.
    pub response: String,
    /// Fixture path relative to `tests/fixtures`.
    pub fixture: String,
}

#[derive(serde::Deserialize)]
struct Record {
    facts: Vec<Fact>,
}

/// Parse the embedded record; a malformed record is a programmer bug and panics.
pub fn facts() -> Vec<Fact> {
    serde_json::from_str::<Record>(RECORD_JSON)
        .expect("capabilities.json is valid")
        .facts
}
