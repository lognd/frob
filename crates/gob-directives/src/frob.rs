//! Directives of the `frob` namespace: milestone-1 accounting verbs and the
//! milestone-2 claim verbs (code-model section 4, neatness.md section 3).
//!
//! The claim verbs are parsed and documented here; the NEAT rules evaluate them.

use gob_macros::Directive;
use gob_rules::RuleId;
use gob_symbols::{Symref, Target};

use crate::args::{ArgKind, FromArg, Token};
use crate::effects::EffectSet;

/// A markdown anchor address `path#slug` naming a documentation section.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocTarget(pub Symref);

impl FromArg for DocTarget {
    const KIND: ArgKind = ArgKind::Str;

    fn from_token(token: &Token) -> Result<Self, &'static str> {
        match Symref::parse(&token.value) {
            Ok(s) if matches!(s.target(), Target::Anchor(_)) => Ok(Self(s)),
            _ => Err("a `path#slug` anchor"),
        }
    }
}

/// A code symref `path::name` naming the symbol a doc section describes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CodeTarget(pub Symref);

impl FromArg for CodeTarget {
    const KIND: ArgKind = ArgKind::Str;

    fn from_token(token: &Token) -> Result<Self, &'static str> {
        match Symref::parse(&token.value) {
            Ok(s) if !matches!(s.target(), Target::Anchor(_)) => Ok(Self(s)),
            _ => Err("a `path::name` code symref"),
        }
    }
}

/// Bind this site to one ticket by its full ULID.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "ticket")]
pub struct Ticket {
    /// The ticket's full 26-char ULID.
    #[arg(positional, ticket_ref)]
    pub id: String,
}

/// Mark outstanding work owned by a ticket, with an optional free-text note.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "todo")]
pub struct Todo {
    /// The owning ticket's full 26-char ULID.
    #[arg(positional, ticket_ref)]
    pub id: String,
    /// The remaining words, kept as the note.
    #[arg(list)]
    pub note: Vec<String>,
}

/// Link this site to the documentation section that describes it.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "doc")]
pub struct Doc {
    /// The documentation anchor, `path#slug`.
    #[arg(positional)]
    pub target: DocTarget,
}

/// Doc-side half of the doc-code pair: this doc section describes a code symbol (pairs like `frob:doc`).
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "describes")]
pub struct Describes {
    /// The described code symbol, `path::name`.
    #[arg(positional)]
    pub symbol: CodeTarget,
}

/// Declare that this site tests a target (a test item names what it covers).
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "tests")]
pub struct Tests {
    /// The symref or test id covered.
    #[arg(positional)]
    pub target: String,
    /// The kind of test (`unit`, `integration`, ...).
    #[arg(key = "kind", optional)]
    pub kind: Option<String>,
}

/// Name an invariant that this site upholds.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "invariant")]
pub struct Invariant {
    /// The invariant's name.
    #[arg(positional)]
    pub name: String,
}

/// Accept one rule's finding at this site permanently, with a reason.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "accept")]
pub struct Accept {
    /// The rule being accepted.
    #[arg(positional)]
    pub rule: RuleId,
    /// An ADR, a style anchor or one sentence.
    #[arg(key = "because")]
    pub because: String,
    /// An optional date or metric after which the acceptance is revisited.
    #[arg(key = "until", optional)]
    pub until: Option<String>,
}

/// Park one rule's finding at this site until a ticket pays it.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "defer")]
pub struct Defer {
    /// The rule being deferred.
    #[arg(positional)]
    pub rule: RuleId,
    /// Why the finding is parked.
    #[arg(key = "because")]
    pub because: String,
    /// The ticket that will pay the debt (full ULID).
    #[arg(key = "ticket", ticket_ref)]
    pub ticket: String,
    /// An optional earlier date or metric target.
    #[arg(key = "until", optional)]
    pub until: Option<String>,
}

/// Claim this unit's effect set: `none`, `honest`, `io`, `any` or atoms, optionally `total`.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "effects")]
pub struct Effects {
    /// `none`, `honest`, `io`, `any`, or atoms (`reads(X)`, `writes(Y)`, `clock`, `rng`, `env`, `fs`, `net`, `stdio`, `exit`, `panic`, `diverge`) then optional `total`.
    #[arg(rest)]
    pub set: EffectSet,
}

/// Alias of `frob:effects none`: this unit has no effects.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "pure")]
pub struct Pure;

/// Alias of `frob:effects honest`: this unit's effects are what its signature admits.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "honest")]
pub struct Honest;

/// Mark this unit as functional core (pure decisions, no effects of its own).
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "core")]
pub struct Core;

/// Mark this unit as imperative shell (effects at the edge, thin logic).
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "shell")]
pub struct Shell;

/// Mark this unit as a framework entry point, subject to the thin-hook rule.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "hook")]
pub struct Hook {
    /// The framework's name for the hook kind, such as `route` or `command`.
    #[arg(positional, optional)]
    pub kind: Option<String>,
}

/// Mark this unit as an intentional dispatcher, opting out of the dispatcher rule.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "dispatcher")]
pub struct Dispatcher;

/// Claim this unit is idempotent; discharged only by a bound `idempotent` test.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "idempotent")]
pub struct Idempotent;

/// Own an unverified claim about this unit; it is never counted as verified.
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "trusted")]
pub struct Trusted {
    /// Why the owner vouches for the claim without proof.
    #[arg(key = "because")]
    pub because: String,
}

/// Declare the targets of the dynamic call at this site (May precision).
#[derive(Debug, Clone, PartialEq, Eq, Directive)]
#[directive(namespace = "frob", verb = "calls")]
pub struct Calls {
    /// The symrefs the call may reach.
    #[arg(list)]
    pub targets: Vec<Symref>,
}
