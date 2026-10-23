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
    /// A type-dependent answer at a site typed `Any`, `dynamic`, unannotated or reflective (`dynamic-site`).
    DynamicSite,
    /// An annotation and local inference disagree: a likely bug (`conflict:annotation-vs-inference`).
    ConflictAnnotationInference,
    /// A type fact exists but is not trusted: an annotation without checker closure (`untrusted-type`).
    UntrustedType,
    /// The type checker was not run (`not-run`).
    NotRun,
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
    /// The evaluation budget (steps or rows) ran out before the answer was decided (`budget`).
    Budget,
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
            Self::DynamicSite => "dynamic-site",
            Self::ConflictAnnotationInference => "conflict:annotation-vs-inference",
            Self::UntrustedType => "untrusted-type",
            Self::NotRun => "not-run",
            Self::Hole => "hole",
            Self::EdgeMay => "edge:may",
            Self::EdgeUnknown => "edge:unknown",
            Self::Vacuous => "vacuous",
            Self::Fidelity => "fidelity",
            Self::ParseFailed => "parse-failed",
            Self::Partial => "partial",
            Self::Budget => "budget",
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
            "dynamic-site" => Self::DynamicSite,
            "conflict:annotation-vs-inference" => Self::ConflictAnnotationInference,
            "untrusted-type" => Self::UntrustedType,
            "not-run" => Self::NotRun,
            "hole" => Self::Hole,
            "edge:may" => Self::EdgeMay,
            "edge:unknown" | "unknown" => Self::EdgeUnknown,
            "vacuous" => Self::Vacuous,
            "fidelity" => Self::Fidelity,
            "parse-failed" => Self::ParseFailed,
            "partial" => Self::Partial,
            "budget" => Self::Budget,
            other => Self::Opaque(other.to_owned()),
        }
    }

    /// The reason class (`cohesion.md` 2.3), so a user can tell "frob could not" from "nobody could".
    pub fn class(&self) -> UnknownClass {
        match self {
            Self::NotRun => UnknownClass::NotRun,
            Self::UntrustedType | Self::ConflictAnnotationInference => UnknownClass::UntrustedType,
            Self::DynamicSite | Self::DynamicUnresolvable | Self::DynamicStringCode => {
                UnknownClass::DynamicSite
            }
            Self::ExpansionBudget
            | Self::Budget
            | Self::NormalizationUnverified
            | Self::Fidelity => UnknownClass::AnalysisLimit,
            _ => UnknownClass::Undecidable,
        }
    }

    /// The cheapest remedy for this reason, where one is known.
    pub fn remedy(&self) -> Option<&'static str> {
        match self {
            Self::DynamicSite => Some(
                "annotate the receiver with a concrete type, or state the effect with a frob: directive",
            ),
            Self::ConflictAnnotationInference => {
                Some("fix the annotation or the code it disagrees with; this is a likely bug")
            }
            Self::UntrustedType => Some(
                "run the type checker in its strictest configuration over every module reaching the site",
            ),
            Self::NotRun => Some("run the configured type checker"),
            _ => None,
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

/// The class of an Unknown answer (`cohesion.md` 2.3): where the missing precision comes from.
///
/// ```
/// use gob_rules::UnknownClass;
/// assert_eq!(UnknownClass::DynamicSite.code(), "dynamic-site");
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum UnknownClass {
    /// The type checker was not run.
    NotRun,
    /// A type fact exists but is not trusted.
    UntrustedType,
    /// The site is dynamic (`Any`, `dynamic`, reflection).
    DynamicSite,
    /// The analysis is weaker than a better one could be.
    AnalysisLimit,
    /// Nobody could decide it.
    Undecidable,
}

impl UnknownClass {
    /// The stable class code.
    pub const fn code(self) -> &'static str {
        match self {
            Self::NotRun => "not-run",
            Self::UntrustedType => "untrusted-type",
            Self::DynamicSite => "dynamic-site",
            Self::AnalysisLimit => "analysis-limit",
            Self::Undecidable => "undecidable",
        }
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
