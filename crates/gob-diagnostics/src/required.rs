//! The `required` mark on Unresolved findings and the gate policy (cli.md section 2).

use std::collections::HashMap;
use std::fmt;

use gob_rules::{Finding, Fingerprint};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Why an Unresolved finding is required, so the gate fails on it (exit 1).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum RequiredReason {
    /// A configured sibling product is absent or incompatible.
    SiblingMissing {
        /// The product or program that could not be used.
        product: String,
    },
    /// An opaque needs an `annotation-required` declaration.
    AnnotationRequired {
        /// The annotation code the declaration must carry.
        code: String,
        /// True when the opaque sits on the public surface.
        public_surface: bool,
    },
    /// A `must_measure` rule examined zero subjects.
    ZeroSubjects {
        /// The rule id that measured nothing.
        rule: String,
    },
}

impl fmt::Display for RequiredReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::SiblingMissing { product } => write!(f, "sibling-missing: {product}"),
            Self::AnnotationRequired {
                code,
                public_surface,
            } => write!(
                f,
                "annotation-required: {code}{}",
                if *public_surface { " (public)" } else { "" }
            ),
            Self::ZeroSubjects { rule } => write!(f, "zero-subjects: {rule}"),
        }
    }
}

/// Which Unresolved findings fail the gate (`[check] fail_on_unresolved`).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum UnresolvedPolicy {
    /// Only Unresolved findings carrying a required reason fail.
    #[default]
    Required,
    /// No Unresolved finding fails.
    Never,
    /// Every Unresolved finding fails.
    All,
}

impl UnresolvedPolicy {
    /// The config spelling (`required`, `never`, `all`).
    pub const fn name(self) -> &'static str {
        match self {
            Self::Required => "required",
            Self::Never => "never",
            Self::All => "all",
        }
    }
}

/// Required reasons keyed by finding fingerprint (gob-rules `Finding` has no mark yet).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RequiredMarks(HashMap<Fingerprint, RequiredReason>);

impl RequiredMarks {
    /// No marks.
    pub fn new() -> Self {
        Self::default()
    }

    /// Mark `finding` as required for `reason`.
    pub fn insert(&mut self, finding: &Finding, reason: RequiredReason) {
        tracing::debug!(rule = %finding.rule, %reason, "finding marked required");
        self.0.insert(finding.fingerprint, reason);
    }

    /// The reason `finding` is required, if marked.
    pub fn get(&self, finding: &Finding) -> Option<&RequiredReason> {
        self.0.get(&finding.fingerprint)
    }

    /// Number of marks.
    pub fn len(&self) -> usize {
        self.0.len()
    }

    /// True when nothing is marked.
    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }
}
