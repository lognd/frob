//! The gallery manifest: versions 1 to 3 parsed (schema first) into one normalized shape.
//!
//! v1 approves a screen on a platform (no state: it matches every state); v2 is per-state with a
//! hashed render; v3 adds an attributed verdict that can expire. [`parse`] validates the document
//! against its version's shipped schema, reporting each violation with a JSON pointer, then maps
//! it onto [`Manifest`].

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH

use serde_json::Value;

use crate::schema::{self, Located};

/// Review state of a cell.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    /// Rendered, awaiting a decision.
    Pending,
    /// Accepted by a reviewer.
    Approved,
    /// Refused by a reviewer.
    Rejected,
}

/// A rendered image of a cell.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Render {
    /// Image path, relative to the manifest.
    pub path: String,
    /// Lowercase hex SHA-256 of the image (absent in v1).
    pub sha256: Option<String>,
}

/// A reviewer's decision on a cell.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Verdict {
    /// The decision.
    pub status: Status,
    /// Who decided (v3 only).
    pub reviewer: Option<String>,
    /// `YYYY-MM-DD` of the decision (v3 only).
    pub reviewed_at: Option<String>,
    /// `YYYY-MM-DD` after which the approval lapses (v3 only).
    pub expires_at: Option<String>,
}

/// One manifest row.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    /// Screen id.
    pub screen: String,
    /// State id; `None` (v1) matches every state of the screen.
    pub state: Option<String>,
    /// Platform id.
    pub platform: String,
    /// The render, if one exists.
    pub render: Option<Render>,
    /// The verdict, if one was given.
    pub verdict: Option<Verdict>,
}

/// A parsed manifest of any version.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Manifest {
    /// The version the document declared.
    pub version: u64,
    /// Its rows.
    pub entries: Vec<Entry>,
}

impl Manifest {
    /// The entry covering `(screen, state, platform)`; an exact state wins over a v1 wildcard.
    #[must_use]
    pub fn find(&self, screen: &str, state: &str, platform: &str) -> Option<&Entry> {
        let hit = |e: &&Entry| e.screen == screen && e.platform == platform;
        let mut rows = self.entries.iter().filter(hit);
        let exact = rows.clone().find(|e| e.state.as_deref() == Some(state));
        exact.or_else(|| rows.find(|e| e.state.is_none()))
    }
}

/// Why a manifest did not parse.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum ManifestError {
    /// The text is not JSON.
    #[error("manifest is not valid JSON: {0}")]
    Json(String),
    /// `version` is missing or not 1, 2 or 3.
    #[error("manifest `version` must be 1, 2 or 3")]
    Version,
    /// The document violates its version's schema.
    #[error("manifest violates the v{version} schema: {}", .errors.iter().map(|e| format!("{}: {}", if e.pointer.is_empty() { "/" } else { &e.pointer }, e.message)).collect::<Vec<_>>().join("; "))]
    Schema {
        /// The declared version.
        version: u64,
        /// Every violation, located.
        errors: Vec<Located>,
    },
}

fn text(v: &Value, key: &str) -> Option<String> {
    v.get(key).and_then(Value::as_str).map(str::to_owned)
}

fn status(s: Option<&str>) -> Option<Status> {
    match s? {
        "pending" => Some(Status::Pending),
        "approved" => Some(Status::Approved),
        "rejected" => Some(Status::Rejected),
        _ => None,
    }
}

fn entry(version: u64, v: &Value) -> Entry {
    let sha = text(v, "sha256");
    let (render, verdict) = if version == 3 {
        let render = v.get("render").filter(|r| r.is_object()).map(|r| Render {
            path: text(r, "path").unwrap_or_default(),
            sha256: text(r, "sha256"),
        });
        let verdict = v.get("verdict").filter(|d| d.is_object()).and_then(|d| {
            Some(Verdict {
                status: status(d.get("status").and_then(Value::as_str))?,
                reviewer: text(d, "reviewer"),
                reviewed_at: text(d, "reviewed_at"),
                expires_at: text(d, "expires_at"),
            })
        });
        (render, verdict)
    } else {
        let render = text(v, "image").map(|path| Render { path, sha256: sha });
        let verdict = status(v.get("status").and_then(Value::as_str)).map(|status| Verdict {
            status,
            reviewer: None,
            reviewed_at: None,
            expires_at: None,
        });
        (render, verdict)
    };
    Entry {
        screen: text(v, "screen").unwrap_or_default(),
        state: text(v, "state"),
        platform: text(v, "platform").unwrap_or_default(),
        render,
        verdict,
    }
}

/// Parse and schema-validate manifest `source` of any supported version.
///
/// # Errors
///
/// [`ManifestError`] when the text is not JSON, the version is unknown or the schema is violated.
pub fn parse(source: &str) -> Result<Manifest, ManifestError> {
    let doc: Value =
        serde_json::from_str(source).map_err(|e| ManifestError::Json(e.to_string()))?;
    let version = doc
        .get("version")
        .and_then(Value::as_u64)
        .ok_or(ManifestError::Version)?;
    let schema_text = schema::manifest_schema(version).ok_or(ManifestError::Version)?;
    let errors = schema::validate(schema_text, &doc);
    if !errors.is_empty() {
        tracing::warn!(
            version,
            violations = errors.len(),
            "gallery manifest rejected"
        );
        return Err(ManifestError::Schema { version, errors });
    }
    let key = if version == 1 { "entries" } else { "cells" };
    let entries: Vec<Entry> = doc
        .get(key)
        .and_then(Value::as_array)
        .map(|rows| rows.iter().map(|r| entry(version, r)).collect())
        .unwrap_or_default();
    tracing::debug!(version, entries = entries.len(), "gallery manifest parsed");
    Ok(Manifest { version, entries })
}
