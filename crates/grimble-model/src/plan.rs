//! The planning AST (grmb-planning 3): systems, actors, goals, steps, scenarios, impls and pages.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use crate::ast::{Clause, Ident, RefPath, Sel, Spanned};
use crate::span::Span;

/// The seven planning item heads, in the order `grimble fmt` prints them (grmb-planning 8.3).
pub const PLAN_HEADS: [&str; 7] = [
    "system", "actor", "goal", "step", "scenario", "impl", "page",
];

/// A planning item (grmb-planning 3 `plan_item`).
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum PlanItem {
    /// `system NAME { ... }`
    System(System),
    /// `actor NAME : KIND ...`
    Actor(Actor),
    /// `goal PATH [as KEY] { variants }`
    Goal(GoalBlock),
    /// `step OWNER.NAME [-> { outcome }] ...`
    Step(Step),
    /// `scenario NAME ... { chain }`
    Scenario(Scenario),
    /// `impl STEP for TARGET { ... }`
    Impl(Impl),
    /// `page NAME ...`
    Page(Page),
}

impl PlanItem {
    /// The item's whole span.
    pub fn span(&self) -> Span {
        match self {
            Self::System(x) => x.span,
            Self::Actor(x) => x.span,
            Self::Goal(x) => x.span,
            Self::Step(x) => x.span,
            Self::Scenario(x) => x.span,
            Self::Impl(x) => x.span,
            Self::Page(x) => x.span,
        }
    }

    /// The comment-attachment id.
    pub fn id(&self) -> usize {
        match self {
            Self::System(x) => x.id,
            Self::Actor(x) => x.id,
            Self::Goal(x) => x.id,
            Self::Step(x) => x.id,
            Self::Scenario(x) => x.id,
            Self::Impl(x) => x.id,
            Self::Page(x) => x.id,
        }
    }

    /// The leading keyword (one of [`PLAN_HEADS`]).
    pub fn keyword(&self) -> &'static str {
        match self {
            Self::System(_) => "system",
            Self::Actor(_) => "actor",
            Self::Goal(_) => "goal",
            Self::Step(_) => "step",
            Self::Scenario(_) => "scenario",
            Self::Impl(_) => "impl",
            Self::Page(_) => "page",
        }
    }
}

/// `verified_by SEL [for STEP.VARIANT];`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Verified {
    /// The acceptance-test selector.
    pub sel: Sel,
    /// The `for step.variant` pair, if any.
    pub pair: Option<RefPath>,
}

/// `KIND [NAME] = SELECTOR;`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Realization {
    /// The realization kind (a pack vocabulary word).
    pub kind: Ident,
    /// The optional realization name.
    pub name: Option<Ident>,
    /// The code selector.
    pub sel: Sel,
}

/// What a planning body clause says.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum PClauseKind {
    /// `title "...";`
    Title(Spanned<String>),
    /// `verified_by SEL [for P];`
    Verified(Verified),
    /// `alias`, `renamed_from`, `attr` or an exception clause.
    Common(Clause),
    /// `node REF;` (actor).
    Node(RefPath),
    /// `entry;` (page).
    Entry,
    /// `from REF, ...;` (page).
    From(Vec<RefPath>),
    /// `KIND [NAME] = SEL;` (impl, page).
    Realization(Realization),
    /// `requires page REF;` (impl).
    RequiresPage(RefPath),
    /// `in node REF;` (impl).
    InNode(RefPath),
    /// A clause that did not parse (MDL000 already reported).
    Hole(String),
}

/// One planning body clause.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct PClause {
    /// Unique id within the file.
    pub id: usize,
    /// The clause.
    pub kind: PClauseKind,
    /// Whole clause span.
    pub span: Span,
}

/// `system NAME { ... }`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct System {
    /// Unique id within the file.
    pub id: usize,
    /// The name.
    pub name: Ident,
    /// True when written with a body (`{ }`), false for `;`.
    pub braced: bool,
    /// Items inside the interior.
    pub items: Vec<crate::ast::Item>,
    /// Clauses of the system itself.
    pub clauses: Vec<PClause>,
    /// Whole item span.
    pub span: Span,
}

/// `actor NAME : KIND [{ ... }]`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Actor {
    /// Unique id within the file.
    pub id: usize,
    /// The name.
    pub name: Ident,
    /// The actor kind word.
    pub kind: Ident,
    /// True when written with a body.
    pub braced: bool,
    /// The clauses.
    pub clauses: Vec<PClause>,
    /// Whole item span.
    pub span: Span,
}

/// One goal variant.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Variant {
    /// Unique id within the file.
    pub id: usize,
    /// The variant name.
    pub name: Ident,
    /// `requires` preconditions.
    pub requires: Vec<RefPath>,
    /// True when written with a body.
    pub braced: bool,
    /// The clauses.
    pub clauses: Vec<PClause>,
    /// Whole variant span.
    pub span: Span,
}

/// `goal PATH [as KEY] { variants }`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct GoalBlock {
    /// Unique id within the file.
    pub id: usize,
    /// The actor or goal path the variants hang off.
    pub path: RefPath,
    /// The dimension key.
    pub key: Option<Ident>,
    /// The variants.
    pub variants: Vec<Variant>,
    /// Whole item span.
    pub span: Span,
}

/// One outcome variant of a step.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Outcome {
    /// The variant name.
    pub name: Ident,
    /// The payload contract, if any.
    pub payload: Option<RefPath>,
}

/// `step OWNER.NAME [-> { outcome }] [{ ... }]`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Step {
    /// Unique id within the file.
    pub id: usize,
    /// The `owner.name` path as written.
    pub target: RefPath,
    /// The declared outcome set, if written.
    pub outcome: Option<Vec<Outcome>>,
    /// True when written with a body.
    pub braced: bool,
    /// The clauses.
    pub clauses: Vec<PClause>,
    /// Whole item span.
    pub span: Span,
}

impl Step {
    /// The step's own name (the last segment).
    pub fn name(&self) -> &str {
        self.target.segments.last().map_or("", String::as_str)
    }

    /// True for a reaction step (`system.NAME`).
    pub fn is_system(&self) -> bool {
        self.target.segments.len() == 2 && self.target.segments[0] == "system"
    }

    /// The owner path as written (`system` or an actor reference).
    pub fn owner(&self) -> RefPath {
        let n = self.target.segments.len().saturating_sub(1);
        RefPath {
            rooted: self.target.rooted,
            segments: self.target.segments[..n].to_vec(),
            span: self.target.span,
        }
    }
}

/// The link between two chain elements.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Hop {
    /// `->`
    Seq,
    /// `-!>`
    Try,
}

impl Hop {
    /// The token text.
    pub fn text(self) -> &'static str {
        match self {
            Self::Seq => "->",
            Self::Try => "-!>",
        }
    }
}

/// A chain element.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Elem {
    /// A step use.
    Step(RefPath),
    /// `include SCENARIO`
    Include(RefPath),
}

impl Elem {
    /// The referenced path.
    pub fn path(&self) -> &RefPath {
        match self {
            Self::Step(p) | Self::Include(p) => p,
        }
    }
}

/// The end of a chain.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Tail {
    /// `elem => { arms }`
    Match {
        /// The matched element.
        elem: Elem,
        /// The arms.
        arms: Vec<Arm>,
    },
    /// A chain that stops on an element with no terminal (reported as MDL026).
    Open(Elem),
    /// `end ok`
    EndOk(Span),
    /// `end err(v)`
    EndErr(Ident),
    /// `retry STEP [max N] [else chain]`
    Retry {
        /// The step retried.
        step: RefPath,
        /// The bound, as written (absent is MDL027).
        max: Option<Spanned<String>>,
        /// The `else` chain.
        otherwise: Option<Box<Chain>>,
        /// Whole tail span.
        span: Span,
    },
}

/// A chain: `{ elem link } tail`.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Chain {
    /// The leading elements with the link that follows each.
    pub links: Vec<(Elem, Hop)>,
    /// The tail.
    pub tail: Tail,
    /// Whole chain span.
    pub span: Span,
}

impl Chain {
    /// True when the last token of the chain is a closing brace (no `;` is written).
    pub fn ends_with_brace(&self) -> bool {
        match &self.tail {
            Tail::Match { .. } => true,
            Tail::Retry { otherwise, .. } => {
                otherwise.as_ref().is_some_and(|c| c.ends_with_brace())
            }
            _ => false,
        }
    }
}

/// An arm pattern.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Pattern {
    /// `_`
    Wild(Span),
    /// `variant` or `step.variant`.
    Path(RefPath),
}

impl Pattern {
    /// The pattern as printed.
    pub fn written(&self) -> String {
        match self {
            Self::Wild(_) => "_".to_owned(),
            Self::Path(p) => p.written(),
        }
    }
}

/// `pattern -> chain`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Arm {
    /// Unique id within the file.
    pub id: usize,
    /// The pattern.
    pub pattern: Pattern,
    /// The arm chain.
    pub chain: Chain,
    /// Whole arm span.
    pub span: Span,
}

/// `handle { arms }`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Handle {
    /// Unique id within the file.
    pub id: usize,
    /// The arms.
    pub arms: Vec<Arm>,
    /// Whole span.
    pub span: Span,
}

/// A member of a scenario body.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum ScMember {
    /// A chain statement, with its comment-attachment id.
    Chain(usize, Chain),
    /// `handle { arms }`
    Handle(Handle),
    /// A body clause.
    Clause(PClause),
}

/// `scenario NAME [realizes G, ...] [fails with { v, ... }] { ... }`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Scenario {
    /// Unique id within the file.
    pub id: usize,
    /// The name.
    pub name: Ident,
    /// Goals realized.
    pub realizes: Vec<RefPath>,
    /// The declared error set.
    pub fails: Option<Vec<Ident>>,
    /// The body.
    pub members: Vec<ScMember>,
    /// Whole item span.
    pub span: Span,
}

/// The target of an impl.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum ImplTarget {
    /// `for SCENARIO`
    Scenario(RefPath),
    /// `for *`
    Any(Span),
}

/// `impl STEP for TARGET { ... }`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Impl {
    /// Unique id within the file.
    pub id: usize,
    /// The step realized.
    pub step: RefPath,
    /// The target scenario or `*`.
    pub target: ImplTarget,
    /// The clauses.
    pub clauses: Vec<PClause>,
    /// Whole item span.
    pub span: Span,
}

/// `page NAME [{ ... }]`
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Page {
    /// Unique id within the file.
    pub id: usize,
    /// The name.
    pub name: Ident,
    /// True when written with a body.
    pub braced: bool,
    /// The clauses.
    pub clauses: Vec<PClause>,
    /// Whole item span.
    pub span: Span,
}
