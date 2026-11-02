//! Severity, fix kind, applicability and polarity: the small enums findings and rules share.

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// How serious a finding is; ordered `Unresolved < Error`; `Warn` and `Advisory` were retired (rules.md 6.1.1), so a rule is on (Error), off, or Unresolved for a site it cannot decide.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum Severity {
    /// Could not be decided (missing tool, unreadable input).
    Unresolved,
    /// Fails the gate.
    Error,
}

/// How a finding of this rule can be repaired.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FixKind {
    /// A human must fix it.
    Manual,
    /// A deterministic edit is attached.
    Deterministic,
    /// A fix verified by a command, then committed.
    VerifyCommit,
    /// An editor fix-it suggestion.
    FixIt,
}

// frob:ticket 01M3ZX7E968R74N08V8DW4RJVG

impl FixKind {
    /// The applicability a fix of this kind carries unless its author states a weaker one.
    ///
    /// `Manual` maps to [`Applicability::Manual`], `Deterministic` to
    /// [`Applicability::Machine`], `VerifyCommit` to [`Applicability::MaybeIncorrect`]
    /// (applied only once its command passes) and `FixIt` to
    /// [`Applicability::HasPlaceholders`] (an editor suggestion to complete).
    #[must_use]
    pub const fn applicability(self) -> Applicability {
        match self {
            Self::Manual => Applicability::Manual,
            Self::Deterministic => Applicability::Machine,
            Self::VerifyCommit => Applicability::MaybeIncorrect,
            Self::FixIt => Applicability::HasPlaceholders,
        }
    }
}

/// How far a fix can be trusted to apply without a human (`docs/design/shared/cli-contract.md` section 3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "kebab-case")]
pub enum Applicability {
    /// Safe to apply mechanically.
    Machine,
    /// Probably right, but a human should review it.
    MaybeIncorrect,
    /// Contains placeholders the human must fill in.
    HasPlaceholders,
    /// No edit is attached; a human does the work.
    Manual,
}

impl Applicability {
    /// Lowercase kebab-case label used in JSON and rendered output.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Machine => "machine",
            Self::MaybeIncorrect => "maybe-incorrect",
            Self::HasPlaceholders => "has-placeholders",
            Self::Manual => "manual",
        }
    }
}

/// Which bound of a three-valued answer a rule may fire on and certify clean on.
///
/// The authoritative table is `universal-model.md` 4.2; the evaluator in
/// `gob-ir` applies it. Declared per rule with `polarity = Pplus | Pminus |
/// P0 | Pn | Pc` in `#[derive(Rule)]`; the default is [`Polarity::Pplus`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Polarity {
    /// P+, presence: fires on `lo`, clean when `hi` is empty.
    Pplus,
    /// P-, absence: fires when `hi` holds no good thing, clean when `lo` does.
    Pminus,
    /// P0, equality: both sides must be `Exact`.
    P0,
    /// Pn, threshold: max-type fires on `lo > N`, min-type on `hi < N`.
    Pn,
    /// Pc, closure: fires on a path inside `lo` edges, clean without one inside `hi`.
    Pc,
}

impl Polarity {
    /// The design spelling (`P+`, `P-`, `P0`, `Pn`, `Pc`) used on rule pages.
    pub const fn symbol(self) -> &'static str {
        match self {
            Self::Pplus => "P+",
            Self::Pminus => "P-",
            Self::P0 => "P0",
            Self::Pn => "Pn",
            Self::Pc => "Pc",
        }
    }
}
