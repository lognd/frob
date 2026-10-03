//! The vocabulary of the binding relation: roles, statuses, sources, rows and findings
//! (binding.md 1.2, 1.3 and 2).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use gob_rules::{Finding, RuleId, Severity};
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
        }
    }
}

/// The message prefix that carries a reason code on an Unresolved finding.
pub const REASON_PREFIX: &str = "[sys-unresolved/";

/// The reason code an Unresolved message carries, if it was written by [`Reason`] tagging.
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
        Some(Finding::new(
            id,
            self.severity,
            span,
            self.message,
            &self.anchor,
        ))
    }
}
