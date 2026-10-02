//! Milestone-1 directives of the `frob` namespace (code-model section 4, exceptions.md).

use gob_macros::Directive;
use gob_rules::RuleId;
use gob_symbols::{Symref, Target};

use crate::args::{ArgKind, FromArg, Token};

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
