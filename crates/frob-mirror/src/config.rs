//! `[mirror.<tracker>]` mapping configuration (mirror.md 2): the raw, versioned, serde shape.
//!
//! Validation against the projection and the tracker's capabilities lives in `mapping`.

// frob:ticket 01M3ZX83E71BKE3PHY83G2NT7K

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::debug;

/// The mapping schema version this build understands.
pub const MAPPING_VERSION: u32 = 1;

/// Where one projection field goes on the tracker.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "to", rename_all = "snake_case")]
pub enum Route {
    /// A label `<prefix><value>`.
    Label {
        /// Text put before the value (may be empty).
        #[serde(default)]
        prefix: String,
    },
    /// A named custom field (needs the `custom_fields` capability).
    Field {
        /// The tracker-side field name.
        name: String,
    },
    /// The tracker's issue type (only for the ticket type).
    IssueType,
    /// The open/closed state or a workflow transition (only for category and outcome).
    State,
    /// Explicitly not mirrored.
    Drop,
}

/// The raw mapping table: a version and one route per projection field.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MappingConfig {
    /// Schema version; must equal [`MAPPING_VERSION`].
    pub version: u32,
    /// Projection field name (`snake_case`) to route.
    pub fields: BTreeMap<String, Route>,
}

/// Why a mapping failed to load.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum ConfigError {
    /// The text is not a valid mapping document.
    #[error("mapping is malformed: {0}")]
    Malformed(String),
    /// The version is not one this build reads.
    #[error("mapping version {found} is unsupported (expected {MAPPING_VERSION})")]
    Version {
        /// The version found.
        found: u32,
    },
    /// A projection field is neither routed nor dropped.
    #[error("projection field `{0}` is neither routed nor dropped")]
    Unrouted(String),
    /// The mapping names a field the projection does not have.
    #[error("mapping names unknown projection field `{0}`")]
    UnknownField(String),
    /// The route cannot carry that field, or the tracker lacks a capability.
    #[error("field `{field}` cannot be routed: {reason}")]
    Unsupported {
        /// The projection field.
        field: String,
        /// Why not.
        reason: String,
    },
}

/// Parse a JSON mapping document (shape only; see `mapping::Mapping::load` for validation).
///
/// # Errors
/// [`ConfigError::Malformed`] when the text is not a mapping document.
pub fn parse(text: &str) -> Result<MappingConfig, ConfigError> {
    let cfg: MappingConfig =
        serde_json::from_str(text).map_err(|e| ConfigError::Malformed(e.to_string()))?;
    debug!(
        version = cfg.version,
        fields = cfg.fields.len(),
        "mapping parsed"
    );
    Ok(cfg)
}
