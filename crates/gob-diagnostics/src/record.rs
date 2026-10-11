//! Serializable projection of a `gob_rules::Finding`.

use gob_rules::{Applicability, Finding, Fix, Registry, RequiredReason, UnresolvedReason};
use schemars::JsonSchema;
use serde::Serialize;

use crate::source::SourceProvider;
use crate::text::severity_label;

// frob:ticket 01M3ZX7E968R74N08V8DW4RJVG

/// One text edit of a fix, flattened for JSON.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct EditRecord {
    /// File path when the edited file is known.
    pub file: Option<String>,
    /// Byte offset where the replaced range starts.
    pub start: u32,
    /// Byte offset where the replaced range ends.
    pub end: u32,
    /// Replacement text.
    pub replacement: String,
}

/// A proposed fix flattened for JSON.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FixRecord {
    /// Short human title.
    pub title: String,
    /// How far the fix can be trusted to apply without a human.
    pub applicability: Applicability,
    /// The exact edits, in the order they were attached.
    pub edits: Vec<EditRecord>,
}

impl FixRecord {
    /// Project `fix`, resolving edit paths through `sources`.
    fn from_fix(fix: &Fix, sources: &dyn SourceProvider) -> Self {
        Self {
            title: fix.title.clone(),
            applicability: fix.applicability,
            edits: fix
                .edits
                .iter()
                .map(|e| EditRecord {
                    file: sources.path(e.file).map(str::to_owned),
                    start: u32::from(e.range.start()),
                    end: u32::from(e.range.end()),
                    replacement: e.replacement.clone(),
                })
                .collect(),
        }
    }
}

/// A finding flattened for JSON (gob-text types carry no serde).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FindingRecord {
    /// Rule id such as `COV006`.
    pub rule: String,
    /// Kebab-case slug when the registry knows the rule.
    pub slug: Option<String>,
    /// Lowercase severity label.
    pub severity: String,
    /// File path when the finding has a resolvable location.
    pub file: Option<String>,
    /// 1-based line of the span start.
    pub line: Option<u32>,
    /// 1-based column of the span start.
    pub column: Option<u32>,
    /// Human-readable message.
    pub message: String,
    /// Stable fingerprint, lowercase hex.
    pub fingerprint: String,
    /// Title of the attached fix, if any.
    pub fix: Option<String>,
    // frob:ticket 01M3ZX7E968R74N08V8DW4RJVG
    /// Fixes with their applicability and exact edits; empty when none is attached.
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub fixes: Vec<FixRecord>,
    /// Why this Unresolved finding fails the gate under `required`, if it does.
    pub required: Option<RequiredReason>,
    /// Typed reason an Unresolved finding could not decide (a code such as `vacuous`); absent otherwise.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<UnresolvedReason>,
}

impl FindingRecord {
    /// Project `finding`, resolving path and line/column through `sources`.
    pub fn from_finding(
        finding: &Finding,
        sources: &dyn SourceProvider,
        registry: &Registry,
    ) -> Self {
        let (file, line, column) = match finding.span {
            Some(span) => {
                let file = sources.path(span.file).map(str::to_owned);
                let lc = sources
                    .source(span.file)
                    .and_then(|s| s.line_col(span.range.start()));
                if lc.is_none() {
                    tracing::warn!(rule = %finding.rule, "span did not resolve to a line");
                }
                (file, lc.map(|l| l.line), lc.map(|l| l.col))
            }
            None => (None, None, None),
        };
        Self {
            rule: finding.rule.to_string(),
            slug: registry
                .by_id(finding.rule.as_str())
                .map(|m| m.slug.to_owned()),
            severity: severity_label(finding.severity).to_owned(),
            file,
            line,
            column,
            message: finding.message.clone(),
            fingerprint: finding.fingerprint.to_hex(),
            fix: finding.fix.as_ref().map(|f| f.title.clone()),
            // frob:ticket 01M3ZX7E968R74N08V8DW4RJVG
            fixes: finding
                .fix
                .iter()
                .map(|f| FixRecord::from_fix(f, sources))
                .collect(),
            required: finding.required.clone(),
            reason: finding.reason.clone(),
        }
    }
}
