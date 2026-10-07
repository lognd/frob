//! The typed reason of an Unresolved finding and the per-rule report (D106, `testing.md`).

use std::fmt;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::finding::Finding;
use crate::id::RuleId;
use crate::meta::Severity;

/// Why a rule could not decide: the `universal-model.md` 4.6 table plus the structural causes.
///
/// The wire and display form is [`UnresolvedReason::code`]; [`UnresolvedReason::from_code`] is the one
/// place a code string becomes a variant (used where a producer holds a code, such as an `opaque`
/// node's reason), never a message.
///
/// ```
/// use gob_rules::UnresolvedReason;
/// let r = UnresolvedReason::from_code("annotation-required:signature");
/// assert_eq!(r, UnresolvedReason::AnnotationSignature);
/// assert_eq!(r.code(), "annotation-required:signature");
/// assert_eq!(UnresolvedReason::from_code("custom"), UnresolvedReason::Opaque("custom".into()));
/// ```
#[derive(
    Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize, JsonSchema,
)]
#[serde(from = "String", into = "String")]
#[schemars(with = "String")]
pub enum UnresolvedReason {
    /// A public signature needs a type annotation (`annotation-required:signature`).
    AnnotationSignature,
    /// A function needs an effect declaration (`annotation-required:effects`).
    AnnotationEffects,
    /// The target of dynamic dispatch or reflection is unknown (`dynamic:unresolvable`).
    DynamicUnresolvable,
    /// A region is code held as a string (`dynamic:string-code`).
    DynamicStringCode,
    /// Macro or template expansion exceeded its step budget (`expansion:budget`).
    ExpansionBudget,
    /// A dependent definition was not accepted by the termination checker (`normalization:unverified`).
    NormalizationUnverified,
    /// A notebook or sheet has no recorded execution order (`order:unrecorded`).
    OrderUnrecorded,
    /// Any other opaque region, with its own code.
    Opaque(String),
    /// A hole or parse-error node (`hole`).
    Hole,
    /// The deciding edge is `May` (`edge:may`).
    EdgeMay,
    /// The deciding edge or answer is `Unknown` (`edge:unknown`).
    EdgeUnknown,
    /// Zero subjects over a scope that was not wholly not applicable (`vacuous`).
    Vacuous,
    /// The language fidelity does not support what the rule needs (`fidelity`).
    Fidelity,
    /// A file could not be read or parsed at all (`parse-failed`).
    ParseFailed,
    /// A file parsed partially, with holes (`partial`).
    Partial,
}

impl UnresolvedReason {
    /// The stable code of this reason.
    pub fn code(&self) -> &str {
        match self {
            Self::AnnotationSignature => "annotation-required:signature",
            Self::AnnotationEffects => "annotation-required:effects",
            Self::DynamicUnresolvable => "dynamic:unresolvable",
            Self::DynamicStringCode => "dynamic:string-code",
            Self::ExpansionBudget => "expansion:budget",
            Self::NormalizationUnverified => "normalization:unverified",
            Self::OrderUnrecorded => "order:unrecorded",
            Self::Opaque(code) => code,
            Self::Hole => "hole",
            Self::EdgeMay => "edge:may",
            Self::EdgeUnknown => "edge:unknown",
            Self::Vacuous => "vacuous",
            Self::Fidelity => "fidelity",
            Self::ParseFailed => "parse-failed",
            Self::Partial => "partial",
        }
    }

    /// The reason a code names; an unlisted code is an [`UnresolvedReason::Opaque`] with that code.
    ///
    /// `unknown` (an `Unknown` answer with no poisoned atom) is [`UnresolvedReason::EdgeUnknown`].
    pub fn from_code(code: &str) -> Self {
        match code {
            "annotation-required:signature" => Self::AnnotationSignature,
            "annotation-required:effects" => Self::AnnotationEffects,
            "dynamic:unresolvable" => Self::DynamicUnresolvable,
            "dynamic:string-code" => Self::DynamicStringCode,
            "expansion:budget" => Self::ExpansionBudget,
            "normalization:unverified" => Self::NormalizationUnverified,
            "order:unrecorded" => Self::OrderUnrecorded,
            "hole" => Self::Hole,
            "edge:may" => Self::EdgeMay,
            "edge:unknown" | "unknown" => Self::EdgeUnknown,
            "vacuous" => Self::Vacuous,
            "fidelity" => Self::Fidelity,
            "parse-failed" => Self::ParseFailed,
            "partial" => Self::Partial,
            other => Self::Opaque(other.to_owned()),
        }
    }

    /// The `annotation-required` reasons: an absent declaration, so the remedy is to add one.
    pub fn is_annotation(&self) -> bool {
        matches!(self, Self::AnnotationSignature | Self::AnnotationEffects)
    }
}

impl fmt::Display for UnresolvedReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl From<String> for UnresolvedReason {
    fn from(code: String) -> Self {
        Self::from_code(&code)
    }
}

impl From<UnresolvedReason> for String {
    fn from(r: UnresolvedReason) -> Self {
        r.code().to_owned()
    }
}

/// What one rule did over one scope: subject accounting plus its findings (`universal-model.md` 4.2).
///
/// ```
/// use gob_rules::RuleReport;
/// let r = RuleReport::new("COV001".parse().unwrap(), 3, 3, None, Vec::new());
/// assert!(r.is_certified_clean());
/// assert!(!RuleReport::new("COV001".parse().unwrap(), 0, 0, None, Vec::new()).is_certified_clean());
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleReport {
    /// The rule.
    pub rule: RuleId,
    /// Subjects in the subject set (not-applicable subjects excluded).
    pub subjects_total: usize,
    /// Subjects whose answer was known at least as bounds.
    pub subjects_examined: usize,
    /// Why the rule cannot apply to this scope by construction; `None` when it applied.
    pub not_applicable: Option<String>,
    /// Findings of the rule, violations then Unresolved.
    pub findings: Vec<Finding>,
}

impl RuleReport {
    /// A report from its parts.
    pub fn new(
        rule: RuleId,
        subjects_total: usize,
        subjects_examined: usize,
        not_applicable: Option<String>,
        findings: Vec<Finding>,
    ) -> Self {
        Self {
            rule,
            subjects_total,
            subjects_examined,
            not_applicable,
            findings,
        }
    }

    /// True when the rule applied, examined at least one subject and reported nothing at any severity.
    pub fn is_certified_clean(&self) -> bool {
        self.not_applicable.is_none() && self.subjects_examined >= 1 && self.findings.is_empty()
    }

    /// The Unresolved findings of the report.
    pub fn unresolved(&self) -> impl Iterator<Item = &Finding> {
        self.findings
            .iter()
            .filter(|f| f.severity == Severity::Unresolved)
    }
}
