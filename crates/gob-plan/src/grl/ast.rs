//! The GRL syntax tree: the twenty constructs of grl-spec.md section 4.
//!
//! Every node carries a `gob-text` [`Span`]. The tree is purely syntactic:
//! kinds, verbs, fields and variables are kept as [`Word`]s exactly as
//! written, and name resolution, type checks and catalog lookups happen in a
//! later pass (GRL001 and friends), never in the parser.

use gob_text::Span;

use super::token::{Regex, Snippet};

/// A node paired with the source range it was read from.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Spanned<T> {
    /// The node.
    pub node: T,
    /// Its source range.
    pub span: Span,
}

/// A word as written: a name, kind, verb or field. Multi-word verbs are one word with single spaces (`resolves to`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Word {
    /// The text; hyphenated words are joined (`known-gap`), multi-word relations use one space.
    pub text: String,
    /// Where the word (all of its pieces) is.
    pub span: Span,
}

/// A plain string literal: no interpolation, escapes decoded.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StrLit {
    /// The decoded text.
    pub value: String,
    /// The string including its quotes.
    pub span: Span,
}

/// A triple-quoted block with its common indentation removed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BlockLit {
    /// The dedented text.
    pub value: String,
    /// The raw range between the triple quotes.
    pub body: Span,
    /// The block including its triple quotes.
    pub span: Span,
}

/// A dotted path of names such as `c.text` or `config.invariants.forbid_imports`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Path {
    /// The segments in order; never empty.
    pub segments: Vec<Word>,
    /// From the first segment to the last.
    pub span: Span,
}

/// One piece of a message string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MessagePart {
    /// Literal text with escapes decoded.
    Text {
        /// The decoded text.
        value: String,
        /// Where it was read from.
        span: Span,
    },
    /// A `{path}` interpolation: a field, knob or witness, never an expression.
    Interp {
        /// The named value.
        path: Path,
        /// The interpolation including its braces.
        span: Span,
    },
}

/// A message string of `report`, `note`, `fix manual` and `unresolved`: text with interpolations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Message {
    /// The pieces in order.
    pub parts: Vec<MessagePart>,
    /// The string including its quotes.
    pub span: Span,
}

/// A whole `.grl` file: any number of rules.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct File {
    /// The rules in source order (rules that failed to parse are left out).
    pub rules: Vec<Rule>,
}

/// `rule ID "slug" { ... }` (construct 1).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Rule {
    /// The rule id such as `TODO001`.
    pub id: Word,
    /// The slug string.
    pub slug: StrLit,
    /// Headers in source order.
    pub headers: Vec<Header>,
    /// Clauses in source order.
    pub clauses: Vec<Clause>,
    /// Examples in source order.
    pub examples: Vec<Example>,
    /// The explain block; `None` only when the file had a syntax error there.
    pub explain: Option<Explain>,
    /// From `rule` to the closing brace.
    pub span: Span,
}

/// A header line (construct 2) or knob (construct 17).
pub type Header = Spanned<HeaderKind>;

/// The header forms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HeaderKind {
    /// `lang ...`
    Lang(LangSet),
    /// `polarity P+`
    Polarity(Polarity),
    /// `severity error`
    Severity(Severity),
    /// `scope repo`
    Scope(Scope),
    /// `must_measure`
    MustMeasure,
    /// `needs diff, lease`
    Needs(Vec<Word>),
    /// `rollup directory`
    Rollup(Rollup),
    /// `knob depth: int = 12 "doc"`
    Knob(Knob),
}

/// The languages a rule applies to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LangSet {
    /// `*` (universal); `quoted` is true for the accepted but deprecated `"*"`.
    Any {
        /// Written as a quoted string.
        quoted: bool,
    },
    /// `-`: the rule reads side relations only.
    Nothing,
    /// One language id.
    One(Word),
    /// `[rust, python]`
    List(Vec<Word>),
}

/// A rule polarity (grl-spec.md 7.2): the one enum of `gob-rules`, not a second copy.
pub use gob_rules::Polarity;

/// A rule severity.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    /// `error`
    Error,
    /// `warn`
    Warn,
    /// `advisory`
    Advisory,
}

/// A rule scope.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Scope {
    /// `file`
    File,
    /// `repo`
    Repo,
}

/// A rollup granularity.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Rollup {
    /// `file`
    File,
    /// `directory`
    Directory,
    /// `unit`
    Unit,
}

/// `knob NAME: TYPE = LITERAL "doc"`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Knob {
    /// The knob name.
    pub name: Word,
    /// Its declared type.
    pub ty: TypeRef,
    /// Its default value.
    pub default: Literal,
    /// Its documentation string.
    pub doc: StrLit,
}

/// A knob type with its span.
pub type TypeRef = Spanned<TypeKind>;

/// The knob types.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TypeKind {
    /// `int`
    Int,
    /// `float`
    Float,
    /// `string`
    String,
    /// `bool`
    Bool,
    /// `glob`
    Glob,
    /// `regex`
    Regex,
    /// `vocab`
    Vocab,
    /// `list<T>`
    List(Box<TypeRef>),
}

/// A literal value.
pub type Literal = Spanned<LiteralKind>;

/// The literal forms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LiteralKind {
    /// A whole number (negative allowed).
    Int(i128),
    /// A decimal as written, with its sign (`0.75`, `-1.5`).
    Decimal(String),
    /// A plain string (no interpolation).
    Str(String),
    /// A regex literal.
    Regex(Regex),
    /// `true` or `false`.
    Bool(bool),
    /// `[a, b]`
    List(Vec<Literal>),
    /// `vocab("clock", "rng")`: a built-in constructor applied to literals.
    Call {
        /// The constructor name.
        name: Word,
        /// Its arguments.
        args: Vec<Literal>,
    },
}

/// A clause of a rule body.
pub type Clause = Spanned<ClauseKind>;

/// The clause forms (constructs 5, 6, 8, 16, 18, 19, 20).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ClauseKind {
    /// `find NAME: SOURCE ...`
    Find(Binding),
    /// `where COND`
    Where(Cond),
    /// `some NAME: ...` or `no NAME: ...` written as a clause.
    Quant {
        /// Exists or absent.
        quant: Quant,
        /// What it ranges over.
        binding: Binding,
    },
    /// `def NAME(params) = COND`
    Def(Def),
    /// `report NAME "message" [when COND]`
    Report(Report),
    /// `note NAME "message"`
    Note(Note),
    /// `fix ...`
    Fix(Fix),
    /// `unresolved when COND because "reason"`
    Unresolved(Unresolved),
}

/// Existential or negated quantifier.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Quant {
    /// `some`
    Some,
    /// `no`
    No,
}

/// What `find`, `some`, `no` and `count` share: a variable, its source, relations and a filter.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Binding {
    /// The variable being bound.
    pub name: Word,
    /// What it ranges over.
    pub source: Source,
    /// Relations written directly after the source.
    pub rels: Vec<Rel>,
    /// The `where` filter, if any.
    pub filter: Option<Cond>,
    /// From the variable to the end of the filter.
    pub span: Span,
}

/// What a variable ranges over.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Source {
    /// A shape: kind, snippet or alternatives.
    Shape(Shape),
    /// A side relation such as `diff.changed`.
    Side(Path),
}

impl Source {
    /// The source range of the source.
    pub fn span(&self) -> Span {
        match self {
            Self::Shape(s) => s.span,
            Self::Side(p) => p.span,
        }
    }
}

/// A shape: a kind, a snippet or alternatives (construct 3).
pub type Shape = Spanned<ShapeKind>;

/// The shape forms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ShapeKind {
    /// `KIND`, `KIND(field = value, ...)` or `KIND "arg"` (such as `directive "todo"`).
    Kind {
        /// The kind word, unchecked.
        kind: Word,
        /// Field equalities in the parentheses.
        fields: Vec<FieldEq>,
        /// A string argument written after the kind.
        arg: Option<StrLit>,
    },
    /// A code snippet, optionally cast with `as`.
    Snippet {
        /// The snippet as lexed (language tag, text, metavariables).
        snippet: Snippet,
        /// `as KIND` or `as roles`.
        cast: Option<Cast>,
    },
    /// `(a | b)`: alternative shapes.
    Alt(Vec<Shape>),
}

/// `as KIND` or `as roles` after a snippet.
pub type Cast = Spanned<CastKind>;

/// The cast forms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CastKind {
    /// Select the node of this kind.
    Kind(Word),
    /// Lift the snippet to universal roles.
    Roles,
}

/// `name = literal` inside a shape's parentheses.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FieldEq {
    /// The field word, unchecked.
    pub name: Word,
    /// The required value.
    pub value: Literal,
    /// From the name to the value.
    pub span: Span,
}

/// `def NAME(params) = COND` (construct 16).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Def {
    /// The predicate name.
    pub name: Word,
    /// Parameter names.
    pub params: Vec<Word>,
    /// The body.
    pub body: Cond,
}

/// `report NAME "message" [when COND]`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Report {
    /// The variable whose span is the finding.
    pub target: Word,
    /// The message.
    pub message: Message,
    /// The `when` guard, if any.
    pub when: Option<Cond>,
}

/// `note NAME "message"`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Note {
    /// The variable whose span is the secondary span.
    pub target: Word,
    /// The message.
    pub message: Message,
}

/// A fix (construct 19).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Fix {
    /// What the fix does.
    pub kind: FixKind,
    /// The bracketed applicability; `None` when missing (GRL015 reports it later) or for `fix manual`.
    pub applicability: Option<Applicability>,
}

/// The fix forms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FixKind {
    /// `fix [before|after] NAME -> SNIPPET`
    Replace {
        /// Insert before or after instead of replacing.
        placement: Option<Placement>,
        /// The variable to replace or insert beside.
        target: Word,
        /// The replacement snippet.
        with: Snippet,
        /// Span of the snippet.
        with_span: Span,
    },
    /// `fix delete NAME`
    Delete {
        /// The variable to remove.
        target: Word,
    },
    /// `fix host NAME(args)` (std only).
    Host {
        /// The host fix name.
        name: Word,
        /// Its arguments.
        args: Vec<Term>,
    },
    /// `fix manual "steps"`
    Manual {
        /// The help text.
        message: Message,
    },
}

/// Where an inserting fix goes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Placement {
    /// `before`
    Before,
    /// `after`
    After,
}

/// A bracketed fix applicability with its span.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Applicability {
    /// Which applicability.
    pub kind: ApplicabilityKind,
    /// The word (inside the brackets).
    pub span: Span,
}

/// The fix applicabilities.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ApplicabilityKind {
    /// `machine`
    Machine,
    /// `maybe-incorrect`
    MaybeIncorrect,
    /// `has-placeholders`
    HasPlaceholders,
}

/// `unresolved when COND because "reason"`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Unresolved {
    /// The doubt condition.
    pub when: Cond,
    /// Why it is doubtful.
    pub because: Message,
}

/// A condition (constructs 6 to 15).
pub type Cond = Spanned<CondKind>;

/// The condition forms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CondKind {
    /// `a or b or ...` (two or more).
    Or(Vec<Cond>),
    /// `a and b and ...` (two or more).
    And(Vec<Cond>),
    /// `not c`
    Not(Box<Cond>),
    /// `any { a, b }`
    Any(Vec<Cond>),
    /// `some x: ...` or `no x: ...`
    Quant {
        /// Exists or absent.
        quant: Quant,
        /// What it ranges over.
        binding: Box<Binding>,
    },
    /// `term rel`
    Rel {
        /// The left side.
        subject: Term,
        /// The relation and its object.
        rel: Box<Rel>,
    },
    /// `term CMP term`
    Cmp {
        /// The operator.
        op: CmpOp,
        /// Left side.
        lhs: Term,
        /// Right side.
        rhs: Term,
    },
    /// `term ~ REGEX-or-term`
    RegexMatch {
        /// The text.
        lhs: Term,
        /// The pattern: a regex literal or a term.
        rhs: Term,
    },
    /// `term matches term`
    GlobMatch {
        /// The text.
        lhs: Term,
        /// The glob or list of globs.
        rhs: Term,
    },
    /// `term in term` (ranges allowed)
    In {
        /// The member.
        lhs: Term,
        /// The collection.
        rhs: Term,
    },
    /// `term is KIND-or-WORD`
    Is {
        /// The tested value.
        subject: Term,
        /// The kind or boolean field word, unchecked.
        test: Word,
    },
    /// `term is SNIPPET [as roles]`
    IsSnippet {
        /// The tested value.
        subject: Term,
        /// The snippet.
        snippet: Snippet,
        /// Whether `as roles` follows.
        roles: bool,
    },
    /// `term has attr "k"`
    HasAttr {
        /// The tested value.
        subject: Term,
        /// The attribute name.
        attr: StrLit,
    },
    /// `NAME(args)`: a call of a def.
    DefCall(Call),
    /// `exists term`
    Exists(Term),
    /// A bare term used as a condition (a boolean field such as `c.observed`).
    Flag(Term),
}

/// A comparison operator.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CmpOp {
    /// `==`
    Eq,
    /// `!=`
    Ne,
    /// `<`
    Lt,
    /// `<=`
    Le,
    /// `>`
    Gt,
    /// `>=`
    Ge,
}

/// An arithmetic operator.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArithOp {
    /// `+`
    Add,
    /// `-`
    Sub,
    /// `*`
    Mul,
}

/// A relation of a subject to an object (constructs 9 to 12).
pub type Rel = Spanned<RelKind>;

/// The relation forms; multi-word verbs are single nodes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RelKind {
    /// `[directly] inside OBJ` or `[directly] has OBJ`.
    Containment {
        /// One structural level only.
        directly: bool,
        /// Ancestor or descendant.
        dir: Containment,
        /// The other side.
        object: Object,
    },
    /// `in unit OBJ`
    InUnit {
        /// The unit.
        object: Object,
    },
    /// `under TERM`
    Under {
        /// The module or path prefix.
        term: Term,
    },
    /// `before`, `after` or `adjoins`.
    Position {
        /// Which one.
        position: Position,
        /// The other side.
        object: Object,
    },
    /// A graph edge verb such as `calls` or `resolves to`.
    Verb {
        /// `certainly` or `possibly` written before the verb.
        certainty: Option<Certainty>,
        /// The verb word (`resolves to` is one word), unchecked.
        verb: Word,
        /// The target.
        object: Object,
    },
    /// `reaches OBJ via VERBS [within TERM]`
    Reaches {
        /// The target.
        target: Object,
        /// The verbs followed.
        via: Vec<Word>,
        /// The bound on the closure; `None` is reported later as GRL010.
        within: Option<Term>,
    },
}

/// Containment direction.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Containment {
    /// `inside`: the subject is within the object.
    Inside,
    /// `has`: the subject contains the object.
    Has,
}

/// Order and adjacency words.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Position {
    /// `before`
    Before,
    /// `after`
    After,
    /// `adjoins`
    Adjoins,
}

/// An override of the Must/May edge choice.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Certainty {
    /// `certainly`
    Certainly,
    /// `possibly`
    Possibly,
}

/// The object of a relation: a term (a bound variable is a one-segment path) or an anonymous shape.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Object {
    /// A term; a bare word may be a variable or a kind, which resolution decides.
    Term(Term),
    /// An anonymous shape.
    Shape(Shape),
}

impl Object {
    /// The source range of the object.
    pub fn span(&self) -> Span {
        match self {
            Self::Term(t) => t.span,
            Self::Shape(s) => s.span,
        }
    }
}

/// A term (construct 14).
pub type Term = Spanned<TermKind>;

/// The term forms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TermKind {
    /// `x`, `x.name`, `config.lease.shared_files`.
    Path(Path),
    /// A literal.
    Literal(Literal),
    /// `knob.NAME`
    Knob(Word),
    /// `count(x: source ...)`
    Count(Box<Binding>),
    /// `NAME(args)`: a built-in function or def call.
    Call(Call),
    /// `a + b`, `a - b`, `a * b`.
    Binary {
        /// The operator.
        op: ArithOp,
        /// Left operand.
        lhs: Box<Term>,
        /// Right operand.
        rhs: Box<Term>,
    },
    /// `a..b` (only on the right of `in`).
    Range {
        /// Lower end.
        lo: Box<Term>,
        /// Upper end.
        hi: Box<Term>,
    },
}

/// A call `NAME(args)`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Call {
    /// The function or def name.
    pub name: Word,
    /// Arguments.
    pub args: Vec<Term>,
    /// From the name to the closing parenthesis.
    pub span: Span,
}

/// `example EXPECT [LANG] ["name"] ...` (construct 20).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Example {
    /// What the example must produce.
    pub expect: Expect,
    /// The language, when written.
    pub lang: Option<Word>,
    /// The example's name string, when written.
    pub name: Option<StrLit>,
    /// The source or sub-blocks.
    pub body: ExampleBody,
    /// From `example` to the end of the body.
    pub span: Span,
}

/// An example's expected outcome with its span.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Expect {
    /// Which outcome.
    pub kind: ExpectKind,
    /// The word (hyphenated words included).
    pub span: Span,
}

/// The expected outcomes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExpectKind {
    /// `fire`
    Fire,
    /// `clean`
    Clean,
    /// `unresolved`
    Unresolved,
    /// `notapplicable`
    NotApplicable,
    /// `known-gap`
    KnownGap,
}

/// The body of an example.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExampleBody {
    /// A triple-quoted source block.
    Source(BlockLit),
    /// `{ file ..., config ..., ... }`
    Inputs(Vec<Input>),
}

/// An input sub-block of an example.
pub type Input = Spanned<InputKind>;

/// The input forms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InputKind {
    /// `file "path" """..."""`
    File {
        /// The repository-relative path.
        path: StrLit,
        /// The file text.
        text: BlockLit,
    },
    /// `config """toml"""`
    Config(BlockLit),
    /// `model """grmb"""`
    Model(BlockLit),
    /// `diff ["path", ...]`
    Diff(Vec<StrLit>),
    /// `lease ["glob", ...]`
    Lease(Vec<StrLit>),
    /// `expect "line 3: warn"`
    Expect(StrLit),
    /// `fixed """..."""`
    Fixed(BlockLit),
}

/// `explain """..."""`: the rule page, markdown.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Explain {
    /// The markdown block.
    pub text: BlockLit,
    /// From `explain` to the closing quotes.
    pub span: Span,
}
