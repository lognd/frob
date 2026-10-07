//! The vocabulary of the binding relation: roles, statuses, sources, rows and findings
//! (binding.md 1.2, 1.3 and 2).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use gob_rules::{Finding, RuleId, Severity, UnresolvedReason};
use gob_text::{FileInterner, Span, TextRange, TextSize};
use serde_json::{Value, json};

/// How an entity binds to code (binding.md 1.2).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum Role {
    /// A node owns identities (a function: each identity has at most one owner).
    Owns,
    /// A flow's producer end.
    Producer,
    /// A flow's consumer end.
    Consumer,
    /// The one identity a contract is the shape of.
    Shape,
    /// The one test unit of a vmodel.
    Runnable,
    /// The one unit or document anchor a vmodel refers to.
    Ref,
    /// The units that evidence a claim.
    Evidence,
}

impl Role {
    /// The role as the sibling document spells it.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Owns => "owns",
            Self::Producer => "producer",
            Self::Consumer => "consumer",
            Self::Shape => "shape",
            Self::Runnable => "runnable",
            Self::Ref => "ref",
            Self::Evidence => "evidence",
        }
    }

    /// The role a `role=` directive attribute spells.
    pub fn parse(text: &str) -> Option<Self> {
        Some(match text {
            "owns" => Self::Owns,
            "producer" => Self::Producer,
            "consumer" => Self::Consumer,
            "shape" => Self::Shape,
            "runnable" => Self::Runnable,
            "ref" => Self::Ref,
            "evidence" => Self::Evidence,
            _ => return None,
        })
    }
}

/// The one status vocabulary of the design set, ordered `Unknown < May < Must`.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum Status {
    /// Nothing is claimed (the hidden remainder).
    Unknown,
    /// Possibly bound.
    May,
    /// Bound on Must facts only.
    Must,
}

impl Status {
    /// The status as the sibling document spells it.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Unknown => "unknown",
            Self::May => "may",
            Self::Must => "must",
        }
    }
}

/// The ranked source of a fact (binding.md 2); a lower rank is stronger.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum Source {
    /// An explicit `grimble:binds` directive.
    Directive = 1,
    /// A model selector clause.
    Selector = 2,
    /// Pack inference (a stub until packs load).
    Inference = 3,
    /// Nothing: the residual of an unseen remainder.
    Residual = 4,
}

impl Source {
    /// The numeric rank, 1 to 4.
    pub const fn rank(self) -> u8 {
        self as u8
    }
}

/// One row of B with its provenance (binding.md 1.3).
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Row {
    /// Anchor of the entity (`node/cli`).
    pub entity: String,
    /// The role.
    pub role: Role,
    /// Symref of the bound identity; `None` for the hidden remainder (rank 4).
    pub identity: Option<String>,
    /// The unit kind of the identity (`function`, `module`, ...), when known.
    pub unit_kind: Option<String>,
    /// The status of the row.
    pub status: Status,
    /// The rank that produced it.
    pub source: Source,
    /// The clause anchor (`node/cli/owns[0]`) or the directive site (`path@offset`).
    pub anchor: Option<String>,
    /// The residual reason of a rank 4 row.
    pub reason: Option<String>,
    /// The specificity vector of a rank 2 `owns` row (grmb-spec 6.5).
    pub specificity: Option<[i32; 6]>,
    /// True when a stronger fact decided the owner differently; the row stays as provenance.
    pub overridden: bool,
}

impl Row {
    /// The row as an item of the sibling document's `bindings` array.
    pub fn to_json(&self) -> Value {
        json!({
            "entity": self.entity,
            "role": self.role.as_str(),
            "identity": self.identity,
            "status": self.status.as_str(),
            "rank": self.source.rank(),
            "anchor": self.anchor,
            "reason": self.reason,
        })
    }
}

/// Why a finding is Unresolved (binding.md 2.4): the `sys-unresolved/<reason>` family.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Reason {
    /// A matched artifact holds opaque, hole, phase or an unreadable file.
    UnseenRemainder,
    /// The owner or row is May only.
    MayOnlyOwner,
    /// The language is F0 or F1 for a facet the rule needs.
    Fidelity,
    /// A requested inference rule could not run.
    InferenceUnavailable,
    /// Zero subjects over a scope that was not wholly not-applicable.
    Vacuous,
    /// `grimble.lock` exists but cannot be read or parsed.
    LockUnreadable,
    /// An import or call edge is May or has no known target, so no owner pair can be claimed.
    UnresolvedEdge,
}

impl Reason {
    /// The reason code (`unseen-remainder`).
    pub const fn code(self) -> &'static str {
        match self {
            Self::UnseenRemainder => "unseen-remainder",
            Self::MayOnlyOwner => "may-only-owner",
            Self::Fidelity => "fidelity",
            Self::InferenceUnavailable => "inference-unavailable",
            Self::Vacuous => "vacuous",
            Self::LockUnreadable => "lock-unreadable",
            Self::UnresolvedEdge => "unresolved-edge",
        }
    }
}

impl Reason {
    /// The reason a code names, or `None` for a code no variant owns.
    pub fn from_code(code: &str) -> Option<Self> {
        [
            Self::UnseenRemainder,
            Self::MayOnlyOwner,
            Self::Fidelity,
            Self::InferenceUnavailable,
            Self::Vacuous,
            Self::LockUnreadable,
            Self::UnresolvedEdge,
        ]
        .into_iter()
        .find(|r| r.code() == code)
    }

    /// The typed reason [`gob_rules::Finding::reason`] carries for this binding reason.
    pub fn typed(self) -> UnresolvedReason {
        match self {
            Self::UnseenRemainder => UnresolvedReason::Opaque(self.code().to_owned()),
            Self::MayOnlyOwner => UnresolvedReason::EdgeMay,
            Self::Fidelity => UnresolvedReason::Fidelity,
            Self::InferenceUnavailable => UnresolvedReason::Partial,
            Self::Vacuous => UnresolvedReason::Vacuous,
            Self::LockUnreadable => UnresolvedReason::ParseFailed,
            Self::UnresolvedEdge => UnresolvedReason::EdgeUnknown,
        }
    }
}

/// The message prefix that carries a reason code on an Unresolved finding.
///
/// Kept only because `grimble-check`'s bind cache stores a `BindFinding` as its message and rebuilds
/// it with no reason field; [`BindFinding::into_finding`] lifts it into the typed `Finding::reason`.
pub const REASON_PREFIX: &str = "[sys-unresolved/";

/// The reason code an Unresolved message carries, if it was written by [`Reason`] tagging.
///
/// Used by [`BindFinding::into_finding`] and `grimble-check` only; consumers read `Finding::reason`.
pub fn reason_of_message(message: &str) -> Option<&str> {
    let rest = message.strip_prefix(REASON_PREFIX)?;
    rest.split_once(']').map(|(code, _)| code)
}

/// A finding before its span is interned: the rule, a path and a byte range.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct BindFinding {
    /// The rule id (`SYS003`).
    pub rule: &'static str,
    /// The severity.
    pub severity: Severity,
    /// Repo-relative file the finding points into.
    pub file: Option<String>,
    /// Byte range in that file.
    pub range: Option<(usize, usize)>,
    /// The message; Unresolved messages start with the reason tag.
    pub message: String,
    /// The anchor the fingerprint is computed from (an entity, clause or path).
    pub anchor: String,
}

impl BindFinding {
    /// An Unresolved finding whose message carries `reason`.
    pub fn unresolved(
        rule: &'static str,
        reason: Reason,
        message: &str,
        anchor: &str,
        site: Option<(&str, (usize, usize))>,
    ) -> Self {
        Self {
            rule,
            severity: Severity::Unresolved,
            file: site.map(|(f, _)| f.to_owned()),
            range: site.map(|(_, r)| r),
            message: format!("{REASON_PREFIX}{}] {message}", reason.code()),
            anchor: anchor.to_owned(),
        }
    }

    /// Intern the span and build the [`Finding`].
    pub fn into_finding(self, files: &mut FileInterner) -> Option<Finding> {
        let id: RuleId = match self.rule.parse() {
            Ok(id) => id,
            Err(err) => {
                tracing::error!(rule = self.rule, %err, "binding finding names an invalid rule id");
                return None;
            }
        };
        let span = match (&self.file, self.range) {
            (Some(file), Some((start, end))) => {
                let size = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
                Some(Span::new(
                    files.intern(file),
                    TextRange::new(size(start), size(end.max(start))),
                ))
            }
            _ => None,
        };
        let reason = reason_of_message(&self.message)
            .and_then(Reason::from_code)
            .map(Reason::typed);
        let finding = Finding::new(id, self.severity, span, self.message, &self.anchor);
        Some(match reason {
            Some(r) => finding.with_reason(r),
            None => finding,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-bind/src/types.rs::BindFinding::into_finding
    #[test]
    fn an_unresolved_bind_finding_lifts_its_reason_into_the_typed_field() {
        for (reason, typed) in [
            (Reason::MayOnlyOwner, UnresolvedReason::EdgeMay),
            (Reason::Vacuous, UnresolvedReason::Vacuous),
            (Reason::UnresolvedEdge, UnresolvedReason::EdgeUnknown),
            (Reason::LockUnreadable, UnresolvedReason::ParseFailed),
            (
                Reason::UnseenRemainder,
                UnresolvedReason::Opaque("unseen-remainder".into()),
            ),
        ] {
            let f = BindFinding::unresolved("SYS006", reason, "m", "a", None)
                .into_finding(&mut FileInterner::default())
                .expect("valid rule id");
            assert_eq!(f.reason, Some(typed));
        }
    }

    #[test]
    fn a_resolved_bind_finding_has_no_reason() {
        let mut b = BindFinding::unresolved("SYS006", Reason::Vacuous, "m", "a", None);
        b.severity = Severity::Error;
        b.message = "plain".to_owned();
        let f = b.into_finding(&mut FileInterner::default()).expect("id");
        assert_eq!(f.reason, None);
    }
}
