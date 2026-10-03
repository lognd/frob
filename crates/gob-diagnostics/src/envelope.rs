//! The JSON envelope every verb emits, its error body and its schema.

use schemars::JsonSchema;
use serde::Serialize;

use crate::record::FindingRecord;

/// Version of the envelope layout; bump on any breaking change.
pub const SCHEMA_VERSION: u32 = 1;

/// Error body of a failed envelope.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct EnvelopeError {
    /// Stable code such as `E-LEASE-HELD`.
    pub code: String,
    /// Human-readable explanation.
    pub message: String,
    /// The exact corrected command, when one exists.
    pub remedy: Option<String>,
    /// True when the same argv may succeed later with no caller action.
    pub retryable: bool,
    /// True when `remedy` is prose for a person, never a command an agent may run (security.md 2.3).
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub requires_human: bool,
}

/// The envelope wrapping every result; field order is the wire order.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Envelope<T> {
    /// True when the verb did what was asked.
    pub ok: bool,
    /// Verb-specific payload.
    pub data: Option<T>,
    /// Findings produced by the verb.
    pub findings: Vec<FindingRecord>,
    /// Non-fatal notices.
    pub warnings: Vec<String>,
    /// Error body when `ok` is false.
    pub error: Option<EnvelopeError>,
    /// Envelope layout version.
    pub schema_version: u32,
}

impl<T> Envelope<T> {
    /// A successful envelope carrying `data` and `findings`.
    pub fn success(data: T, findings: Vec<FindingRecord>) -> Self {
        Self {
            ok: true,
            data: Some(data),
            findings,
            warnings: Vec::new(),
            error: None,
            schema_version: SCHEMA_VERSION,
        }
    }

    /// A failed envelope carrying `error`.
    pub fn failure(error: EnvelopeError) -> Self {
        tracing::debug!(code = %error.code, "failure envelope built");
        Self {
            ok: false,
            data: None,
            findings: Vec::new(),
            warnings: Vec::new(),
            error: Some(error),
            schema_version: SCHEMA_VERSION,
        }
    }
}

/// Render `envelope` as one compact JSON document plus a trailing newline.
///
/// # Panics
///
/// Never in practice: derived serialization of string-keyed data cannot fail
/// (a `T` with a failing `Serialize` impl is a programmer bug).
pub fn render_json<T: Serialize>(envelope: &Envelope<T>) -> String {
    // Serializing derived structs with string keys cannot fail.
    let mut out = serde_json::to_string(envelope).expect("envelope serialization is infallible");
    out.push('\n');
    out
}

/// JSON Schema of the envelope with an opaque `data` payload.
///
/// # Panics
///
/// Never in practice: schema values always convert to JSON.
pub fn envelope_schema() -> serde_json::Value {
    serde_json::to_value(schemars::schema_for!(Envelope<serde_json::Value>))
        .expect("schema serialization is infallible")
}
