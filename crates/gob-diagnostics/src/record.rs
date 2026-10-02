//! Serializable projection of a `gob_rules::Finding`.

use gob_rules::{Finding, Registry};
use schemars::JsonSchema;
use serde::Serialize;

use crate::required::RequiredReason;
use crate::source::SourceProvider;
use crate::text::severity_label;

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
    /// Why this Unresolved finding fails the gate under `required`, if it does.
    pub required: Option<RequiredReason>,
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
            required: None,
        }
    }

    /// This record carrying `required` as its mark.
    #[must_use]
    pub fn with_required(mut self, required: Option<RequiredReason>) -> Self {
        self.required = required;
        self
    }
}
