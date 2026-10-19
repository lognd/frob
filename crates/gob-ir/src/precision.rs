//! Type precision of a type-dependent answer: provenance, status and Unknown reason (`cohesion.md` 2.1, 2.3).

use std::fmt;

use gob_rules::{UnknownClass, UnresolvedReason};
use tracing::debug;

use crate::scope::Status;

/// Where a type fact came from; a set that composes by union along a dispatch chain.
///
/// ```
/// use gob_ir::TypeProvenance;
/// let p = TypeProvenance::CHECKER.union(TypeProvenance::ANNOTATION);
/// assert!(p.contains(TypeProvenance::CHECKER));
/// assert_eq!(p.to_string(), "checker,annotation");
/// assert_eq!(TypeProvenance::NONE.to_string(), "none");
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct TypeProvenance(u8);

impl TypeProvenance {
    /// No type information (`Any`, `dynamic`, unannotated, reflection).
    pub const NONE: Self = Self(0);
    /// A bound type checker reported the type.
    pub const CHECKER: Self = Self(1);
    /// A written annotation claims the type.
    pub const ANNOTATION: Self = Self(2);
    /// The adapter inferred it locally (literal, constructor call, narrowing).
    pub const LOCAL_INFERENCE: Self = Self(4);

    /// The union of two provenance sets.
    #[must_use]
    pub const fn union(self, other: Self) -> Self {
        Self(self.0 | other.0)
    }

    /// True when every source in `other` is present.
    pub const fn contains(self, other: Self) -> bool {
        self.0 & other.0 == other.0
    }

    /// True when there is no source at all.
    pub const fn is_none(self) -> bool {
        self.0 == 0
    }
}

impl fmt::Display for TypeProvenance {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.is_none() {
            return f.write_str("none");
        }
        let names = [
            (Self::CHECKER, "checker"),
            (Self::ANNOTATION, "annotation"),
            (Self::LOCAL_INFERENCE, "local-inference"),
        ];
        let parts: Vec<&str> = names
            .iter()
            .filter(|(p, _)| self.contains(*p))
            .map(|(_, n)| *n)
            .collect();
        f.write_str(&parts.join(","))
    }
}

/// How precise a type-dependent answer is, strongest first.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum TypePrecision {
    /// No type at the site (`Any`, `dynamic`).
    Dynamic,
    /// An annotation nobody verified.
    Claimed,
    /// The adapter's own local inference.
    Inferred,
    /// The checker proved it under whole-program closure.
    Exact,
}

impl TypePrecision {
    /// The stable lowercase name.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Dynamic => "dynamic",
            Self::Claimed => "claimed",
            Self::Inferred => "inferred",
            Self::Exact => "exact",
        }
    }
}

/// The `[types] trust` setting (`cohesion.md` 2.2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub enum TypeTrust {
    /// Only checker-exact facts count; annotations are claims (default).
    #[default]
    Checked,
    /// Annotations count as `May`, explicitly unsound.
    Annotated,
    /// Annotations are hints only.
    Hints,
}

/// What is known about one dispatch or type-dependent site.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
#[allow(
    clippy::struct_excessive_bools,
    reason = "one independent flag per policy-table condition"
)]
pub struct SiteFacts {
    /// Which sources provided a type.
    pub provenance: TypeProvenance,
    /// The trust setting in force.
    pub trust: TypeTrust,
    /// Whether the checker ran at all.
    pub checker_ran: bool,
    /// Whole-program closure holds for the site (every reaching module checked clean).
    pub closed: bool,
    /// The type is concrete rather than an open interface.
    pub concrete: bool,
    /// The program writes the class attribute or prototype (`setattr`, prototype assignment).
    pub class_mutated: bool,
    /// An opaque `eval` is in reach.
    pub opaque_eval: bool,
    /// Annotation and local inference disagree.
    pub conflict: bool,
}

/// A type-dependent answer: precision, provenance, status and, when Unknown, its reason.
///
/// ```
/// use gob_ir::{SiteFacts, Status, TypePrecision, TypePrecision as P, resolve_site};
/// let a = resolve_site(SiteFacts::default());
/// assert_eq!(a.status, Status::Unknown);
/// assert_eq!(a.precision, P::Dynamic);
/// assert_eq!(a.reason.unwrap().code(), "dynamic-site");
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypeAnswer {
    /// How precise the answer is.
    pub precision: TypePrecision,
    /// The sources behind it.
    pub provenance: TypeProvenance,
    /// Must, May or Unknown.
    pub status: Status,
    /// Why it is Unknown, when it is.
    pub reason: Option<UnresolvedReason>,
}

impl TypeAnswer {
    /// The reason class, when Unknown.
    pub fn class(&self) -> Option<UnknownClass> {
        self.reason.as_ref().map(UnresolvedReason::class)
    }

    /// The cheapest remedy, when Unknown and one is known.
    pub fn remedy(&self) -> Option<&'static str> {
        self.reason.as_ref().and_then(UnresolvedReason::remedy)
    }

    /// Compose two hops of a dispatch chain: provenance unions, status meets, precision weakens.
    ///
    /// An Unknown hop keeps its reason; the chain is widened, never ended.
    #[must_use]
    pub fn compose(&self, next: &Self) -> Self {
        let status = self.status.meet(next.status);
        let reason = self
            .reason
            .clone()
            .filter(|_| self.status == Status::Unknown)
            .or_else(|| next.reason.clone());
        Self {
            precision: self.precision.min(next.precision),
            provenance: self.provenance.union(next.provenance),
            status,
            reason: if status == Status::Unknown {
                reason
            } else {
                None
            },
        }
    }

    fn unknown(precision: TypePrecision, f: SiteFacts, reason: UnresolvedReason) -> Self {
        debug!(reason = reason.code(), provenance = %f.provenance, "type answer is Unknown");
        Self {
            precision,
            provenance: f.provenance,
            status: Status::Unknown,
            reason: Some(reason),
        }
    }

    fn known(precision: TypePrecision, f: SiteFacts, status: Status) -> Self {
        Self {
            precision,
            provenance: f.provenance,
            status,
            reason: None,
        }
    }
}

/// Resolve one site's type-dependent answer by the `cohesion.md` 2.1 policy table.
pub fn resolve_site(f: SiteFacts) -> TypeAnswer {
    let has = |p| f.provenance.contains(p);
    if f.provenance.is_none() {
        return TypeAnswer::unknown(TypePrecision::Dynamic, f, UnresolvedReason::DynamicSite);
    }
    if has(TypeProvenance::ANNOTATION) && has(TypeProvenance::LOCAL_INFERENCE) && f.conflict {
        return TypeAnswer::unknown(
            TypePrecision::Claimed,
            f,
            UnresolvedReason::ConflictAnnotationInference,
        );
    }
    if has(TypeProvenance::CHECKER) && f.trust == TypeTrust::Checked && f.closed {
        let status = if f.concrete {
            Status::Must
        } else {
            Status::May
        };
        return TypeAnswer::known(TypePrecision::Exact, f, status);
    }
    if has(TypeProvenance::LOCAL_INFERENCE) {
        if f.opaque_eval {
            return TypeAnswer::unknown(
                TypePrecision::Inferred,
                f,
                UnresolvedReason::DynamicStringCode,
            );
        }
        let status = if f.class_mutated {
            Status::May
        } else {
            Status::Must
        };
        return TypeAnswer::known(TypePrecision::Inferred, f, status);
    }
    // A checker fact without closure counts as an annotation (2.2).
    match f.trust {
        TypeTrust::Annotated => TypeAnswer::known(TypePrecision::Claimed, f, Status::May),
        TypeTrust::Checked | TypeTrust::Hints => {
            let reason = if f.checker_ran {
                UnresolvedReason::UntrustedType
            } else {
                UnresolvedReason::NotRun
            };
            TypeAnswer::unknown(TypePrecision::Claimed, f, reason)
        }
    }
}
