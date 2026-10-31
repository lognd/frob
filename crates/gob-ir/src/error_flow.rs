//! Error-flow facts (D121, grmb-r2-faults.md): what a unit can raise or return as an error.
//!
//! The facts are symbolic: adapters resolve the error position to a type or a callee and hand
//! this module that resolved shape, never source text. The answer is an [`Answer`] over an
//! [`ErrorSet`]: Rust `Result<T, E>` with a concrete closed enum `E` is Exact (one member per
//! variant); a Python body is Bounds (explicit `raise` is `lo`, callee raises are May and only
//! widen `hi`); TypeScript `throw` is Unknown because thrown values are untyped. Panics are the
//! ambient defect class and are never part of the set ([`ErrorCollector::panic`]).
//!
//! A set that is not Exact is a gap, and it surfaces through the existing Unresolved path
//! ([`ErrorFacts::resolution`], [`ErrorFacts::status`]) with no new severity. An outcome-map
//! declaration on the waypoint ([`OutcomeMapClaim`]) is the claim that resolves the gap
//! conditionally: the set is computed as if the claim held and the premise travels with it
//! (`assumed:<claim>`). The claim is judged by [`error_claim_status`] and stays Unverified when
//! the body cannot be analysed, as with a C++ `noexcept` ([`noexcept_claim`]).

// frob:ticket 01M4GM5FT3F4VZP4A76589WNWE

use std::collections::BTreeSet;

use tracing::{debug, trace};

use crate::answer::Answer;
use crate::scope::Status;

/// A set of error members (`PaymentError::Declined`, `PaymentDeclined`); `open` means "and maybe more".
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ErrorSet {
    /// The named error members.
    pub members: BTreeSet<String>,
    /// The set may contain members not named here (an unresolved callee, a foreign open enum).
    pub open: bool,
}

impl ErrorSet {
    /// True when every member of `self` is in `claim` and `self` is closed.
    pub fn within(&self, claim: &BTreeSet<String>) -> bool {
        !self.open && self.members.is_subset(claim)
    }
}

/// The resolved shape of the error position of a Rust unit (`E` in `Result<T, E>`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RustErrorType {
    /// A concrete closed enum; every variant is a member.
    ClosedEnum {
        /// The enum's name.
        name: String,
        /// Its variants.
        variants: Vec<String>,
    },
    /// A foreign `#[non_exhaustive]` enum: the listed variants are known, more may exist.
    NonExhaustive {
        /// The enum's name.
        name: String,
        /// The variants visible today.
        variants: Vec<String>,
    },
    /// `Box<dyn Error>`, `anyhow::Error` and similar erased types.
    Erased {
        /// The erased type as written.
        name: String,
    },
    /// The error type did not resolve.
    Unresolved,
}

/// Why and how surely a unit can fail: the answer, a reason per contribution and any premises.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ErrorFacts {
    /// Exact, Bounds (`lo` must, `hi` may) or Unknown.
    pub errors: Answer<ErrorSet>,
    /// One reason per contribution (`rust:closed-enum:PaymentError`, `py:raise:PaymentDeclined`).
    pub reasons: Vec<String>,
    /// Outcome-map claims this answer is conditional on, sorted.
    pub assumed: Vec<String>,
}

/// How the consumer (grimble) sees an error set.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ErrorResolution {
    /// The set is Exact and unconditional.
    Closed,
    /// The set is Exact only assuming the listed outcome-map claims.
    Conditional(Vec<String>),
    /// The set is not known: the existing opaque-cone Unresolved path, with the reasons.
    Unresolved(Vec<String>),
}

impl ErrorFacts {
    /// Facts for a Rust `Result<T, E>` error position: only concrete closed enums are Exact.
    pub fn rust(ty: &RustErrorType) -> Self {
        let facts = match ty {
            RustErrorType::ClosedEnum { name, variants } => Self {
                errors: Answer::Exact(ErrorSet {
                    members: qualified(name, variants),
                    open: false,
                }),
                reasons: vec![format!("rust:closed-enum:{name}")],
                assumed: Vec::new(),
            },
            RustErrorType::NonExhaustive { name, variants } => {
                let members = qualified(name, variants);
                Self {
                    errors: Answer::Bounds {
                        lo: ErrorSet {
                            members: members.clone(),
                            open: false,
                        },
                        hi: ErrorSet {
                            members,
                            open: true,
                        },
                    },
                    reasons: vec![format!("rust:non-exhaustive:{name}")],
                    assumed: Vec::new(),
                }
            }
            RustErrorType::Erased { name } => Self::unknown(format!("rust:erased:{name}")),
            RustErrorType::Unresolved => Self::unknown("rust:unresolved-error-type".to_owned()),
        };
        debug!(reasons = ?facts.reasons, "rust error facts");
        facts
    }

    /// Facts for a TypeScript unit: thrown values are untyped, so always Unknown.
    pub fn typescript(throw_sites: &[&str]) -> Self {
        let site = throw_sites.first().copied().unwrap_or("no throw site");
        let facts = Self::unknown(format!("ts:throw:{site}:thrown values are untyped"));
        debug!(sites = throw_sites.len(), "typescript error facts");
        facts
    }

    fn unknown(reason: String) -> Self {
        Self {
            errors: Answer::Unknown,
            reasons: vec![reason],
            assumed: Vec::new(),
        }
    }

    /// The consumer-facing resolution: Closed, Conditional on claims, or Unresolved with reasons.
    pub fn resolution(&self) -> ErrorResolution {
        match (&self.errors, self.assumed.is_empty()) {
            (Answer::Exact(_), true) => ErrorResolution::Closed,
            (Answer::Exact(_), false) => ErrorResolution::Conditional(self.assumed.clone()),
            _ => ErrorResolution::Unresolved(self.reasons.clone()),
        }
    }

    /// The edge status for the relation layer: Exact is Must, Bounds May, otherwise Unknown.
    pub fn status(&self) -> Status {
        match self.errors {
            Answer::Exact(_) => Status::Must,
            Answer::Bounds { .. } => Status::May,
            Answer::Unknown | Answer::NotApplicable => Status::Unknown,
        }
    }

    /// Resolve a non-Exact set conditionally with an outcome-map `claim`; Exact facts are kept.
    #[must_use]
    pub fn with_outcome_map(self, claim: &OutcomeMapClaim) -> Self {
        if self.errors.is_exact() {
            trace!(claim = %claim.label, "error set already exact; claim not needed");
            return self;
        }
        debug!(claim = %claim.label, "error set resolved conditionally by outcome map");
        let mut reasons = self.reasons;
        reasons.push(format!("assumed:{}", claim.label));
        let mut assumed = self.assumed;
        assumed.push(claim.label.clone());
        assumed.sort();
        assumed.dedup();
        Self {
            errors: Answer::Exact(ErrorSet {
                members: claim.errors.clone(),
                open: false,
            }),
            reasons,
            assumed,
        }
    }
}

fn qualified(name: &str, variants: &[String]) -> BTreeSet<String> {
    variants.iter().map(|v| format!("{name}::{v}")).collect()
}

/// An outcome-map declaration (or `noexcept`) on a waypoint: the error set it claims.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutcomeMapClaim {
    /// Where the claim was made and what it says.
    pub label: String,
    /// The error members the claim allows.
    pub errors: BTreeSet<String>,
}

/// A C++ `noexcept` is a claim of the empty error set, never a proof (D121).
pub fn noexcept_claim(label: &str) -> OutcomeMapClaim {
    OutcomeMapClaim {
        label: label.to_owned(),
        errors: BTreeSet::new(),
    }
}

/// How a call site's callee contributes to the caller's error set.
#[derive(Debug, Clone, Copy)]
pub enum ErrorCallee<'a> {
    /// The callee's error facts are known.
    Resolved(&'a ErrorFacts),
    /// A boundary inference cannot reach, carrying a claim.
    Claimed(&'a OutcomeMapClaim),
    /// An unresolved call or opaque body with no claim.
    Opaque,
}

/// Builds a Python-style error set: explicit raises are `lo`, callee raises only widen `hi`.
#[derive(Debug, Default)]
pub struct ErrorCollector {
    lo: BTreeSet<String>,
    hi: ErrorSet,
    reasons: Vec<String>,
    assumed: BTreeSet<String>,
}

impl ErrorCollector {
    /// A collector for a body that raises nothing so far.
    pub fn new() -> Self {
        Self::default()
    }

    /// The body explicitly raises `name`: a Must member.
    pub fn raise(&mut self, name: &str) {
        self.lo.insert(name.to_owned());
        self.hi.members.insert(name.to_owned());
        self.reasons.push(format!("py:raise:{name}"));
    }

    /// The body panics: the ambient defect class, never part of the error set.
    pub fn panic(&mut self, site: &str) {
        trace!(site, "panic is a defect, not an error-set member");
    }

    /// The body calls `callee` at `site`; whatever the callee raises is a May member.
    pub fn call(&mut self, site: &str, callee: ErrorCallee<'_>) {
        match callee {
            ErrorCallee::Resolved(facts) => match facts.errors.hi() {
                Some(set) => {
                    self.hi.members.extend(set.members.iter().cloned());
                    self.hi.open |= set.open;
                    self.reasons.push(format!("py:callee:{site}"));
                }
                None => self.widen(site),
            },
            ErrorCallee::Claimed(claim) => {
                debug!(site, claim = %claim.label, "callee errors set by an unverified claim");
                self.assumed.insert(claim.label.clone());
                self.hi.members.extend(claim.errors.iter().cloned());
                self.reasons.push(format!("assumed:{}", claim.label));
            }
            ErrorCallee::Opaque => self.widen(site),
        }
    }

    /// An unresolved call or dynamic site at `site` may raise anything.
    pub fn widen(&mut self, site: &str) {
        self.hi.open = true;
        self.reasons.push(format!("py:unresolved-call:{site}"));
    }

    /// The finished facts: Exact when `lo` and `hi` agree and `hi` is closed, else Bounds.
    pub fn finish(self) -> ErrorFacts {
        let lo = ErrorSet {
            members: self.lo,
            open: false,
        };
        let errors = if lo == self.hi {
            Answer::Exact(lo)
        } else {
            Answer::Bounds { lo, hi: self.hi }
        };
        let facts = ErrorFacts {
            errors,
            reasons: self.reasons,
            assumed: self.assumed.into_iter().collect(),
        };
        debug!(status = ?facts.status(), assumed = facts.assumed.len(), "collected error facts");
        facts
    }
}

/// The verdict on an outcome-map claim against the body's own error facts.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorClaimStatus {
    /// The body is analysed and its `hi` is within the claim.
    Verified,
    /// The body provably raises something the claim does not allow.
    Contradicted,
    /// The body is opaque, open or only possibly outside the claim. Never clean.
    Unverified,
}

/// Judge `claim` against the body's own answer; a body inference cannot reach is Unverified.
pub fn error_claim_status(claim: &OutcomeMapClaim, body: &Answer<ErrorSet>) -> ErrorClaimStatus {
    let status = match (body.lo(), body.hi()) {
        (Some(lo), Some(hi)) => {
            if !lo.members.is_subset(&claim.errors) {
                ErrorClaimStatus::Contradicted
            } else if hi.within(&claim.errors) {
                ErrorClaimStatus::Verified
            } else {
                ErrorClaimStatus::Unverified
            }
        }
        _ => ErrorClaimStatus::Unverified,
    };
    debug!(claim = %claim.label, ?status, "judged error claim");
    status
}

#[cfg(test)]
mod tests {
    use super::*;

    fn names(v: &[&str]) -> Vec<String> {
        v.iter().map(|s| (*s).to_owned()).collect()
    }

    fn payment() -> RustErrorType {
        RustErrorType::ClosedEnum {
            name: "PaymentError".into(),
            variants: names(&["Declined", "Timeout"]),
        }
    }

    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorFacts::rust
    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorFacts::typescript
    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorCollector::finish
    #[test]
    fn rust_exact_python_may_typescript_unknown_each_with_reason() {
        let rust = ErrorFacts::rust(&payment());
        let Answer::Exact(set) = &rust.errors else {
            panic!("rust closed enum must be exact");
        };
        assert_eq!(
            set.members,
            ["PaymentError::Declined", "PaymentError::Timeout"]
                .iter()
                .map(|s| (*s).to_owned())
                .collect()
        );
        assert_eq!(rust.reasons, ["rust:closed-enum:PaymentError"]);

        let mut py = ErrorCollector::new();
        py.raise("PaymentDeclined");
        let httpx = ErrorFacts {
            errors: Answer::Bounds {
                lo: ErrorSet::default(),
                hi: ErrorSet {
                    members: ["httpx.HTTPError".to_owned()].into(),
                    open: false,
                },
            },
            reasons: vec![],
            assumed: vec![],
        };
        py.call("httpx.get", ErrorCallee::Resolved(&httpx));
        let py = py.finish();
        let Answer::Bounds { lo, hi } = &py.errors else {
            panic!("python must be bounds");
        };
        assert_eq!(lo.members.len(), 1);
        assert!(hi.members.contains("httpx.HTTPError") && !hi.open);
        assert_eq!(py.status(), Status::May);
        assert_eq!(
            py.reasons,
            ["py:raise:PaymentDeclined", "py:callee:httpx.get"]
        );

        let ts = ErrorFacts::typescript(&["pay.ts:4"]);
        assert_eq!(ts.errors, Answer::Unknown);
        assert!(ts.reasons[0].starts_with("ts:throw:pay.ts:4"));
    }

    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorFacts::rust
    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorCollector::panic
    #[test]
    fn rust_only_closed_enums_are_exact_and_panics_are_excluded() {
        for name in ["Box<dyn Error>", "anyhow::Error"] {
            let f = ErrorFacts::rust(&RustErrorType::Erased { name: name.into() });
            assert_eq!(f.errors, Answer::Unknown);
            assert!(f.reasons[0].contains(name));
        }
        assert_eq!(
            ErrorFacts::rust(&RustErrorType::Unresolved).errors,
            Answer::Unknown
        );
        let open = ErrorFacts::rust(&RustErrorType::NonExhaustive {
            name: "io::ErrorKind".into(),
            variants: names(&["NotFound"]),
        });
        let Answer::Bounds { lo, hi } = &open.errors else {
            panic!("non_exhaustive must be bounds");
        };
        assert!(!lo.open && hi.open);

        let mut c = ErrorCollector::new();
        c.panic("unwrap at a.rs:1");
        let f = c.finish();
        assert_eq!(f.errors, Answer::Exact(ErrorSet::default()));
    }

    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorFacts::resolution
    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorFacts::with_outcome_map
    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorFacts::status
    #[test]
    fn non_exact_is_unresolved_and_an_outcome_map_resolves_it_conditionally() {
        let ts = ErrorFacts::typescript(&["a.ts:1"]);
        assert!(matches!(ts.resolution(), ErrorResolution::Unresolved(r) if r.len() == 1));
        assert_eq!(ts.status(), Status::Unknown);

        let claim = OutcomeMapClaim {
            label: "pay.ts:2 outcomes Declined".into(),
            errors: ["Declined".to_owned()].into(),
        };
        let resolved = ts.with_outcome_map(&claim);
        assert_eq!(
            resolved.resolution(),
            ErrorResolution::Conditional(vec![claim.label.clone()])
        );
        assert_eq!(resolved.status(), Status::Must);
        assert!(
            resolved
                .reasons
                .contains(&format!("assumed:{}", claim.label))
        );

        let closed = ErrorFacts::rust(&payment()).with_outcome_map(&claim);
        assert_eq!(closed.resolution(), ErrorResolution::Closed);
    }

    // frob:tests crates/gob-ir/src/error_flow.rs::error_claim_status
    // frob:tests crates/gob-ir/src/error_flow.rs::noexcept_claim
    // frob:tests crates/gob-ir/src/error_flow.rs::ErrorCollector::call
    #[test]
    fn noexcept_is_an_unverified_claim_unless_the_body_is_analysable() {
        let claim = noexcept_claim("f.cpp:1 noexcept");
        assert_eq!(
            error_claim_status(&claim, &Answer::Unknown),
            ErrorClaimStatus::Unverified
        );
        let raises = Answer::Exact(ErrorSet {
            members: ["E".to_owned()].into(),
            open: false,
        });
        assert_eq!(
            error_claim_status(&claim, &raises),
            ErrorClaimStatus::Contradicted
        );
        let none = Answer::Exact(ErrorSet::default());
        assert_eq!(
            error_claim_status(&claim, &none),
            ErrorClaimStatus::Verified
        );

        let mut c = ErrorCollector::new();
        c.call("ffi()", ErrorCallee::Claimed(&claim));
        c.call("dyn()", ErrorCallee::Opaque);
        let f = c.finish();
        assert_eq!(f.assumed, std::slice::from_ref(&claim.label));
        assert!(matches!(f.errors, Answer::Bounds { ref hi, .. } if hi.open));
        assert!(matches!(f.resolution(), ErrorResolution::Unresolved(_)));
    }
}
