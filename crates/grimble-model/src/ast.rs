//! The typed AST of a .grmb file (grmb-spec 3 and 4): one variant per entity and clause.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use gob_walk::Selector;
use gob_walk::selector::SyntaxError;

use crate::lex::Comment;
use crate::span::{Diagnostic, Span};

/// An identifier with its span.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Ident {
    /// The identifier text.
    pub text: String,
    /// Where it is.
    pub span: Span,
}

/// A dotted reference `[::] a.b.c` (grmb-spec 2.7).
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct RefPath {
    /// True when written with a leading `::` (anchored at the model root).
    pub rooted: bool,
    /// The dotted segments.
    pub segments: Vec<String>,
    /// Where it is.
    pub span: Span,
}

impl RefPath {
    /// The path as written without the root anchor: `a.b.c`.
    pub fn dotted(&self) -> String {
        self.segments.join(".")
    }

    /// The path as written, including a leading `::`.
    pub fn written(&self) -> String {
        if self.rooted {
            format!("::{}", self.dotted())
        } else {
            self.dotted()
        }
    }
}

/// A capability atom `[pack::]a.b` (grmb-spec 2.7).
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Atom {
    /// The pack qualifier, if any.
    pub pack: Option<String>,
    /// The dotted atom name.
    pub name: String,
    /// Where it is.
    pub span: Span,
}

impl Atom {
    /// The atom as written: `pack::a.b` or `a.b`.
    pub fn written(&self) -> String {
        match &self.pack {
            Some(p) => format!("{p}::{}", self.name),
            None => self.name.clone(),
        }
    }
}

/// A quantity: a number and a unit lexeme (the unit is checked by MDL009).
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Quantity {
    /// The number as written.
    pub number: String,
    /// The unit as written.
    pub unit: String,
    /// Where it is.
    pub span: Span,
}

/// A value: the right-hand side of `attr`, of `key=value` pairs and of `versioning`.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Value {
    /// A string (adjacent strings already joined).
    Str(String),
    /// A number as written.
    Number(String),
    /// A quantity.
    Quantity(Quantity),
    /// A date lexeme.
    Date(String),
    /// An identifier.
    Ident(String),
    /// A bracketed list.
    List(Vec<Value>),
}

/// A value with its span.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Spanned<T> {
    /// The payload.
    pub value: T,
    /// Where it is.
    pub span: Span,
}

/// A `key=value` pair.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct KeyVal {
    /// The key.
    pub key: Ident,
    /// The value.
    pub value: Spanned<Value>,
}

/// A selector slice of the file, parsed by gob-walk.
#[derive(Clone, Debug)]
pub struct Sel {
    /// The selector text exactly as written.
    pub text: String,
    /// Where the text is in the file.
    pub span: Span,
    /// The parse result; errors keep their file-coordinate spans.
    pub parsed: Result<Selector, Vec<SyntaxError>>,
}

impl PartialEq for Sel {
    fn eq(&self, other: &Self) -> bool {
        self.text == other.text
    }
}

impl Eq for Sel {}

/// A selector of `may ... at SEL`.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct May {
    /// The granted atom.
    pub atom: Atom,
    /// Constraining string arguments.
    pub args: Vec<Spanned<String>>,
    /// The `at` selector, if any.
    pub at: Option<Sel>,
}

/// An `excuses ATOM because="..."` clause.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Excuses {
    /// The excused atom.
    pub atom: Atom,
    /// The `because` pairs (`because` is required).
    pub attrs: Vec<KeyVal>,
}

/// The three exception clause kinds (grmb-spec 7).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub enum ExcKind {
    /// `accept`
    Accept,
    /// `defer`
    Defer,
    /// `hotfix`
    Hotfix,
}

impl ExcKind {
    /// The keyword.
    pub const fn keyword(self) -> &'static str {
        match self {
            Self::Accept => "accept",
            Self::Defer => "defer",
            Self::Hotfix => "hotfix",
        }
    }
}

/// An exception clause or top-level exception.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Exception {
    /// accept, defer or hotfix.
    pub kind: ExcKind,
    /// The rule id token.
    pub rule: Ident,
    /// `on REF`, if written.
    pub on: Option<RefPath>,
    /// The `key=value` attributes.
    pub attrs: Vec<KeyVal>,
}

/// `versioning k=v ...`.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Versioning {
    /// The pairs.
    pub attrs: Vec<KeyVal>,
}

/// What a claim proposes.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum ClaimWhat {
    /// `noflow A -> B;`
    Noflow(RefPath, RefPath),
    /// `reach A -> B;`
    Reach(RefPath, RefPath),
    /// `bound METRIC TARGET <= Q;`
    Bound {
        /// The metric name.
        metric: Ident,
        /// The node or flow the bound applies to.
        target: RefPath,
        /// The bound.
        limit: Quantity,
    },
}

/// `evidence tests SEL;` or `evidence ref "S";`.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Evidence {
    /// Test units.
    Tests(Sel),
    /// A document anchor or code unit symref.
    Ref(Spanned<String>),
}

/// The vmodel link keywords (grmb-spec 4.5).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub enum LinkKind {
    /// `satisfies`
    Satisfies,
    /// `verifies`
    Verifies,
    /// `refines`
    Refines,
    /// `allocates`
    Allocates,
    /// `decides`
    Decides,
    /// `supersedes`
    Supersedes,
    /// `blocked_by`
    BlockedBy,
}

impl LinkKind {
    /// Every link kind.
    pub const ALL: [Self; 7] = [
        Self::Satisfies,
        Self::Verifies,
        Self::Refines,
        Self::Allocates,
        Self::Decides,
        Self::Supersedes,
        Self::BlockedBy,
    ];

    /// The keyword.
    pub const fn keyword(self) -> &'static str {
        match self {
            Self::Satisfies => "satisfies",
            Self::Verifies => "verifies",
            Self::Refines => "refines",
            Self::Allocates => "allocates",
            Self::Decides => "decides",
            Self::Supersedes => "supersedes",
            Self::BlockedBy => "blocked_by",
        }
    }
}

/// A vmodel link clause.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Link {
    /// Which link.
    pub kind: LinkKind,
    /// The target vmodel.
    pub target: RefPath,
    /// `because="..."` (required for `supersedes`).
    pub because: Option<Spanned<String>>,
}

/// The keys of a scalar quantity clause.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub enum QuantKey {
    /// `rate`
    Rate,
    /// `age`
    Age,
    /// `size`
    Size,
}

impl QuantKey {
    /// The keyword.
    pub const fn keyword(self) -> &'static str {
        match self {
            Self::Rate => "rate",
            Self::Age => "age",
            Self::Size => "size",
        }
    }
}

/// Every clause kind of every entity (the parser is entity-agnostic; MDL000 checks fit).
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum ClauseKind {
    /// `alias NAME;`
    Alias(Ident),
    /// `renamed_from NAME;`
    RenamedFrom(Ident),
    /// `attr KEY [= VALUE];`
    Attr {
        /// The key.
        key: Ident,
        /// The value, if any.
        value: Option<Spanned<Value>>,
    },
    /// accept, defer, hotfix.
    Exception(Exception),
    /// `kind K;`
    Kind(Ident),
    /// `clearance L;`
    Clearance(Ident),
    /// `owns SEL;`
    Owns(Sel),
    /// `surface SEL;`
    Surface(Sel),
    /// `may ...;`
    May(May),
    /// `excuses ...;`
    Excuses(Excuses),
    /// `label L;`
    Label(Ident),
    /// `rate|age|size Q;`
    Quantity(QuantKey, Quantity),
    /// `fanout N;`
    Fanout(Spanned<String>),
    /// `growth Q;`
    Growth(Quantity),
    /// `transport ATOM, ATOM;`
    Transport(Vec<Atom>),
    /// `condition on_ok;`
    Condition(Ident),
    /// `producer SEL;`
    Producer(Sel),
    /// `consumer SEL;`
    Consumer(Sel),
    /// `contract NAME;` inside a flow.
    Contract(RefPath),
    /// `shape SEL;`
    Shape(Sel),
    /// `versioning k=v ...;`
    Versioning(Versioning),
    /// `noflow|reach|bound ...;`
    What(ClaimWhat),
    /// `proof L;`
    Proof(Ident),
    /// `assumed owner=.. review=.. because=..;`
    Assumed(Vec<KeyVal>),
    /// `evidence ...;`
    Evidence(Evidence),
    /// `level L;`
    Level(Ident),
    /// `ref "S";`
    Ref(Spanned<String>),
    /// `runnable SEL;`
    Runnable(Sel),
    /// A vmodel link.
    Link(Link),
    /// `version "X.Y.Z";` of a pack.
    Version(Spanned<String>),
    /// `digest "blake3:..";` of a pack.
    Digest(Spanned<String>),
    /// A syntax error that resynchronized at `;` or `}`.
    Hole(String),
}

/// A clause with its identity for comment attachment.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Clause {
    /// Unique id within the file (see [`Attachments`]).
    pub id: usize,
    /// The clause.
    pub kind: ClauseKind,
    /// The whole clause including `;`.
    pub span: Span,
}

/// The seven entity kinds (grmb-spec 4).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum EntityKind {
    /// `node`
    Node,
    /// `flow`
    Flow,
    /// `contract`
    Contract,
    /// `claim`
    Claim,
    /// `vmodel`
    Vmodel,
    /// `boundary`
    Boundary,
    /// `pack`
    Pack,
}

impl EntityKind {
    /// Every kind in canonical order (grmb-spec 9.3: node, flow, contract, claim, vmodel, boundary; pack first in files).
    pub const ALL: [Self; 7] = [
        Self::Node,
        Self::Flow,
        Self::Contract,
        Self::Claim,
        Self::Vmodel,
        Self::Boundary,
        Self::Pack,
    ];

    /// The keyword and the U unit kind.
    pub const fn keyword(self) -> &'static str {
        match self {
            Self::Node => "node",
            Self::Flow => "flow",
            Self::Contract => "contract",
            Self::Claim => "claim",
            Self::Vmodel => "vmodel",
            Self::Boundary => "boundary",
            Self::Pack => "pack",
        }
    }

    /// The kind spelled by `kw`.
    pub fn from_keyword(kw: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|k| k.keyword() == kw)
    }
}

/// The direction of a boundary.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Direction {
    /// `endorse` (trust lattice).
    Endorse,
    /// `declassify` (label lattice).
    Declassify,
}

impl Direction {
    /// The keyword.
    pub const fn keyword(self) -> &'static str {
        match self {
            Self::Endorse => "endorse",
            Self::Declassify => "declassify",
        }
    }
}

/// The header of an entity beyond its name.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Header {
    /// `: TRUST` of a node (absent is MDL008).
    Node {
        /// The trust level.
        trust: Option<Ident>,
    },
    /// `: A -> B` of a flow.
    Flow {
        /// Source node reference.
        from: RefPath,
        /// Target node reference.
        to: RefPath,
    },
    /// `endorse|declassify FLOW : A -> B [when "T"]` of a boundary.
    Boundary {
        /// The direction.
        direction: Direction,
        /// The flow acted on.
        flow: RefPath,
        /// From element.
        from: Ident,
        /// To element.
        to: Ident,
        /// The opaque predicate.
        when: Option<Spanned<String>>,
    },
    /// No header.
    None,
}

/// A declared entity or an `extend` part of one.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Entity {
    /// Unique id within the file.
    pub id: usize,
    /// The kind.
    pub kind: EntityKind,
    /// True for `extend`.
    pub extension: bool,
    /// The declared name (a reference path for `extend`).
    pub name: Ident,
    /// The `extend` target path (equals `name` for declarations).
    pub target: RefPath,
    /// The header.
    pub header: Header,
    /// The body clauses.
    pub clauses: Vec<Clause>,
    /// Whole item span.
    pub span: Span,
}

/// An `include` item.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Include {
    /// Unique id within the file.
    pub id: usize,
    /// The path as written (unescaped).
    pub path: Spanned<String>,
    /// The `as` mount prefix, if any.
    pub mount: Option<RefPath>,
    /// True when the include carries the `outside` marker (it may climb out of the directory).
    pub outside: bool,
    /// Whole item span.
    pub span: Span,
}

/// A `namespace` item.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Namespace {
    /// Unique id within the file.
    pub id: usize,
    /// The namespace name.
    pub name: Ident,
    /// The contained items.
    pub items: Vec<Item>,
    /// Whole item span.
    pub span: Span,
}

/// A top-level exception (`accept RULE on REF because="...";`).
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct TopException {
    /// Unique id within the file.
    pub id: usize,
    /// The exception.
    pub exception: Exception,
    /// Whole item span.
    pub span: Span,
}

/// A file-level item.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Item {
    /// `include "p" [as P] [outside];`
    Include(Include),
    /// `namespace N { ... }`
    Namespace(Namespace),
    /// A declared entity or an extension.
    Entity(Entity),
    /// A top-level exception.
    Exception(TopException),
    /// An item-level syntax error.
    Hole {
        /// Unique id within the file.
        id: usize,
        /// The message.
        message: String,
        /// The skipped span.
        span: Span,
    },
}

impl Item {
    /// The item's whole span.
    pub fn span(&self) -> Span {
        match self {
            Self::Include(i) => i.span,
            Self::Namespace(n) => n.span,
            Self::Entity(e) => e.span,
            Self::Exception(t) => t.span,
            Self::Hole { span, .. } => *span,
        }
    }

    /// The comment-attachment id.
    pub fn id(&self) -> usize {
        match self {
            Self::Include(i) => i.id,
            Self::Namespace(n) => n.id,
            Self::Entity(e) => e.id,
            Self::Exception(t) => t.id,
            Self::Hole { id, .. } => *id,
        }
    }
}

/// Which statement a module declaration is.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum ModuleKind {
    /// `module X;` (the root file).
    Module,
    /// `part of X;` (an included file).
    PartOf,
}

/// `module X;` or `part of X;`.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct ModuleDecl {
    /// Unique id within the file.
    pub id: usize,
    /// Which statement.
    pub kind: ModuleKind,
    /// The model name.
    pub name: Ident,
    /// Whole statement span.
    pub span: Span,
}

/// The version header `grimble = "2";`.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct VersionHeader {
    /// The value string.
    pub value: String,
    /// Whole statement span.
    pub span: Span,
}

/// Why a file is not a normal parse.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum FileStatus {
    /// Read normally (holes may exist).
    Parsed,
    /// `opaque(reason)`: nothing was read (not UTF-8, BOM, NUL, bare CR).
    Opaque(&'static str),
    /// Refused whole: missing or unsupported version header (MDL007).
    Refused(&'static str),
}

/// Comment ids attached to targets by the rules of grmb-spec 8.1.
#[derive(Clone, PartialEq, Eq, Debug, Default)]
pub struct Attachments {
    /// Comment indices bound to the file module unit.
    pub file: Vec<usize>,
    /// Comment indices per target id.
    pub by_target: std::collections::BTreeMap<usize, Vec<usize>>,
}

impl Attachments {
    /// The comments bound to target `id`, in source order.
    pub fn of(&self, id: usize) -> &[usize] {
        self.by_target.get(&id).map_or(&[], Vec::as_slice)
    }
}

/// A parsed .grmb file.
#[derive(Clone, Debug)]
pub struct ParsedFile {
    /// Repo-relative path.
    pub path: String,
    /// The source text (empty for an opaque file).
    pub text: String,
    /// The raw bytes of an opaque file (the `opaque` payload); empty otherwise.
    pub raw: Vec<u8>,
    /// Size of the file in bytes.
    pub size: usize,
    /// How the file was read.
    pub status: FileStatus,
    /// The version header, if present.
    pub version: Option<VersionHeader>,
    /// `module` or `part of`.
    pub module: Option<ModuleDecl>,
    /// The items in source order.
    pub items: Vec<Item>,
    /// Every comment in source order.
    pub comments: Vec<Comment>,
    /// Comment bindings.
    pub attachments: Attachments,
    /// Syntax and lexical diagnostics.
    pub diags: Vec<Diagnostic>,
    /// Number of `hole` nodes (syntax errors that were resynchronized, plus lexical errors).
    pub holes: usize,
    /// Spans of lexical errors, each a `hole` in the U term.
    pub lex_holes: Vec<Span>,
}

impl ParsedFile {
    /// True when the file holds a `hole` or is opaque or refused (fmt must not rewrite it).
    pub fn is_damaged(&self) -> bool {
        self.holes > 0 || self.status != FileStatus::Parsed
    }
}
