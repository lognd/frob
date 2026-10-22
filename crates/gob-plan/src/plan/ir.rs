//! The plan IR: an arena of ops, referenced by index, that the executor runs.
//!
//! A plan is a conjunction of `clauses` (in planner order) and a list of `reports`.
//! Ops live in one arena; an op may only refer to ops with a smaller index and
//! every op has exactly one referrer, so a plan is a tree and cannot cycle.
//! Names (kinds, fields, verbs, patterns, messages) are indexes into the string pool.

pub use gob_rules::Polarity;

/// Index of an op in the arena.
pub type OpId = u32;
/// Index of a string in the pool.
pub type StrId = u32;
/// A variable slot, bound by exactly one find or quantifier.
pub type VarId = u16;

/// Where a plan's rule comes from (security.md 2.2: provenance is carried, not inferred).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Provenance {
    /// Compiled into the binary.
    Std,
    /// Shipped by the named pack.
    Pack(String),
}

/// A side relation a rule may read (grl-spec.md section 6); declared in `reads`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Read {
    /// `config.<table>`.
    Config,
    /// `diff.changed`, `diff.added`.
    Diff,
    /// `lease.globs`, `lease.ticket`.
    Lease,
    /// `model.nodes`, `model.selectors`.
    Model,
}

impl Read {
    /// Every need, in bit order.
    pub const ALL: [Read; 4] = [Read::Config, Read::Diff, Read::Lease, Read::Model];

    /// The relation's GRL name.
    pub fn name(self) -> &'static str {
        match self {
            Read::Config => "config",
            Read::Diff => "diff",
            Read::Lease => "lease",
            Read::Model => "model",
        }
    }

    pub(super) fn bit(self) -> u8 {
        1 << (self as u8)
    }
}

/// The set of side relations a plan declares, as a bitset (canonical by construction).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct ReadSet(pub(super) u8);

impl ReadSet {
    /// A set holding exactly `reads`.
    pub fn of(reads: &[Read]) -> Self {
        ReadSet(reads.iter().fold(0, |acc, n| acc | n.bit()))
    }

    /// Whether `need` is declared.
    pub fn contains(self, need: Read) -> bool {
        self.0 & need.bit() != 0
    }

    /// The declared reads in bit order.
    pub fn iter(self) -> impl Iterator<Item = Read> {
        Read::ALL.into_iter().filter(move |n| self.contains(*n))
    }

    /// Raw bits (only the low four are ever valid).
    pub(super) fn valid(self) -> bool {
        self.0 >> Read::ALL.len() == 0
    }
}

/// Which languages a plan applies to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Langs {
    /// `lang *`: universal.
    Any,
    /// `lang -`: reads only side relations.
    Nothing,
    /// Named languages (string ids, strictly ascending).
    Only(Vec<StrId>),
}

/// How much work one run costs (grl-spec.md 7.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CostClass {
    /// Bounded by one file.
    PerFile,
    /// Bounded by the repository.
    PerRepo,
    /// Follows call edges to the given depth.
    Closure(u16),
}

/// The default, `certainly` or `possibly` choice of edge set (universal-model.md 4.2).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Certainty {
    /// Polarity decides.
    Default,
    /// Must edges only.
    Certainly,
    /// May edges too.
    Possibly,
}

/// A comparison operator.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CmpOp {
    /// `==`.
    Eq,
    /// `!=`.
    Ne,
    /// `<`.
    Lt,
    /// `<=`.
    Le,
    /// `>`.
    Gt,
    /// `>=`.
    Ge,
}

/// Source order of two nodes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Position {
    /// `a before b`.
    Before,
    /// `a after b`.
    After,
    /// `a adjoins b`.
    Adjoins,
}

/// A quantifier over a bound variable.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Quant {
    /// `some`.
    Some,
    /// `no`.
    No,
}

/// The limit a count is compared against (grl-spec.md 7.0.2, 7.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Limit {
    /// A fixed number.
    Int(u64),
    /// A knob: the value in `[rules]` named by the string, else the default.
    Knob {
        /// The knob's name (string pool).
        name: StrId,
        /// The value when the repository does not override it.
        default: u64,
    },
}

/// A decimal factor `num / 10^places` applied to a count (`knob.ratio * count(...)`).
///
/// A negative or zero factor is legal: the scaled count is then at most zero.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Scale {
    /// The signed numerator.
    pub num: i64,
    /// The decimal places: the denominator is `10^places`.
    pub places: u8,
}

impl Scale {
    /// The factor one, which leaves a count unchanged.
    pub const ONE: Scale = Scale { num: 1, places: 0 };
}

/// One side of a count-to-count comparison: a count times a [`Scale`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CountSide {
    /// Scoped variable.
    pub var: VarId,
    /// Node kind iterated.
    pub kind: StrId,
    /// The condition each candidate is tested against.
    pub cond: OpId,
    /// The factor the count is multiplied by.
    pub scale: Scale,
}

/// A non-recursive def: a named condition over parameters, evaluated as a view (7.0.2).
///
/// The parameters are variable slots that are bound only inside the body; a body may call
/// only earlier defs, so views form strata in text order (GRL009).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Def {
    /// The parameter slots, in call order.
    pub params: Vec<VarId>,
    /// The body condition.
    pub body: OpId,
}

/// A call-free value: the argument of a builtin function operand.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Leaf {
    /// A bound variable itself.
    Var(VarId),
    /// A field of a bound variable (name in the string pool).
    Field(VarId, StrId),
    /// An integer literal.
    Int(i64),
    /// A string literal (string pool).
    Str(StrId),
    /// A boolean literal.
    Bool(bool),
}

impl Leaf {
    /// The plain operand with the same value.
    #[must_use]
    pub fn operand(self) -> Operand {
        match self {
            Leaf::Var(v) => Operand::Var(v),
            Leaf::Field(v, f) => Operand::Field(v, f),
            Leaf::Int(i) => Operand::Int(i),
            Leaf::Str(s) => Operand::Str(s),
            Leaf::Bool(b) => Operand::Bool(b),
        }
    }

    /// The leaf with the same value as a plain operand; None for a call operand.
    #[must_use]
    pub fn of(o: Operand) -> Option<Leaf> {
        match o {
            Operand::Var(v) => Some(Leaf::Var(v)),
            Operand::Field(v, f) => Some(Leaf::Field(v, f)),
            Operand::Int(i) => Some(Leaf::Int(i)),
            Operand::Str(s) => Some(Leaf::Str(s)),
            Operand::Bool(b) => Some(Leaf::Bool(b)),
            Operand::Slug(_) | Operand::Resolve(..) => None,
        }
    }
}

/// A value a condition compares.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Operand {
    /// A bound variable itself.
    Var(VarId),
    /// A field of a bound variable (name in the string pool).
    Field(VarId, StrId),
    /// An integer literal.
    Int(i64),
    /// A string literal (string pool).
    Str(StrId),
    /// A boolean literal.
    Bool(bool),
    /// `slug(s)`: the GitHub-style heading anchor of the text `s`.
    Slug(Leaf),
    /// `resolve(path, from)`: `path` resolved against the directory of `from`.
    Resolve(Leaf, Leaf),
}

/// One node of the plan arena.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Op {
    /// Clause: bind `var` to every node of `kind`.
    Find {
        /// Variable bound.
        var: VarId,
        /// Node kind name.
        kind: StrId,
    },
    /// Clause: bind `var` to every row of a side relation table.
    FindSide {
        /// Variable bound.
        var: VarId,
        /// The relation, which must be in `reads`.
        need: Read,
        /// Table or column name.
        table: StrId,
    },
    /// Condition: all hold (empty is true).
    And(Vec<OpId>),
    /// Condition: any holds (empty is false).
    Or(Vec<OpId>),
    /// Condition: the operand does not hold.
    Not(OpId),
    /// Condition: `some`/`no` over a scoped variable.
    Quant {
        /// Some or no.
        quant: Quant,
        /// Scoped variable.
        var: VarId,
        /// Node kind iterated.
        kind: StrId,
        /// The condition each candidate is tested against.
        cond: OpId,
    },
    /// Condition: `sub inside sup`.
    Inside {
        /// Inner node.
        sub: VarId,
        /// Outer node.
        sup: VarId,
        /// `directly inside`.
        direct: bool,
    },
    /// Condition: source order of two nodes.
    Order {
        /// Left node.
        a: VarId,
        /// Right node.
        b: VarId,
        /// The relation.
        pos: Position,
    },
    /// Condition: a named verb edge (`calls`, `resolves to`, ...).
    Verb {
        /// Edge source.
        subject: VarId,
        /// Edge target.
        object: VarId,
        /// Verb name.
        verb: StrId,
        /// Edge-set choice.
        certainty: Certainty,
    },
    /// Condition: `from reaches to via edge within N`.
    Reaches {
        /// Start.
        from: VarId,
        /// End.
        to: VarId,
        /// Edge family name.
        via: StrId,
        /// Maximum edges followed, at least 1.
        within: u16,
        /// Edge-set choice.
        certainty: Certainty,
    },
    /// Condition: `count(var: kind where cond) op limit`, an interval comparison (7.0.2).
    CountCmp {
        /// Scoped variable.
        var: VarId,
        /// Node kind iterated.
        kind: StrId,
        /// The condition each candidate is tested against.
        cond: OpId,
        /// Comparison of the count with the limit.
        op: CmpOp,
        /// What the count is compared with.
        limit: Limit,
    },
    /// Condition: `lhs op rhs` over two scaled counts, an interval comparison (7.0.2).
    CountPair {
        /// The left count and its factor.
        lhs: CountSide,
        /// Comparison of the two scaled counts.
        op: CmpOp,
        /// The right count and its factor.
        rhs: CountSide,
    },
    /// Condition: `d(a1, ..., ak)`, a call of def `def` with variables as arguments.
    Call {
        /// Index into [`PlanParts::defs`].
        def: u16,
        /// The argument variables, as many as the def has parameters.
        args: Vec<VarId>,
    },
    /// Condition: compare two operands.
    Cmp {
        /// Left.
        lhs: Operand,
        /// Operator.
        op: CmpOp,
        /// Right.
        rhs: Operand,
    },
    /// Condition: the operand matches a regex (pattern in the string pool).
    MatchRegex {
        /// Value tested.
        subject: Operand,
        /// Regex source.
        pattern: StrId,
    },
    /// Condition: the operand matches a glob (pattern in the string pool).
    MatchGlob {
        /// Value tested.
        subject: Operand,
        /// Glob source.
        pattern: StrId,
    },
    /// Condition: the operand matches any glob held in one column of a side relation
    /// (`p matches lease.globs`); an empty table matches nothing.
    MatchGlobSet {
        /// Value tested.
        subject: Operand,
        /// The side relation family that must be declared in `reads`.
        need: Read,
        /// The relation's dotted name in the string pool.
        table: StrId,
        /// The column holding the globs, in the string pool.
        column: StrId,
    },
    /// Condition: the subject matches a glob read at run time from another operand
    /// (`i.file.path matches row.from`); an unreadable or invalid glob is unknown.
    MatchGlobOperand {
        /// Value tested.
        subject: Operand,
        /// The operand holding the glob source.
        pattern: Operand,
    },
    /// Condition: the variable's node name is a callee name registered for its language under
    /// one of the vocabulary classes (`v in knob.sources`). A language with no vocabulary for
    /// a class contributes nothing; a class with no registry entry at all is the empty set.
    InVocab {
        /// The node whose name is tested.
        var: VarId,
        /// The vocabulary classes (string pool ids) whose names are unioned.
        classes: Vec<StrId>,
    },
    /// Condition: `x is WORD`. A kind word tests membership of a variable; any other word reads
    /// the boolean field of that name (`is public`), or for a field operand a string predicate
    /// (`is relative`, `is valid_glob`, `is integer`) or the dotted field `field.WORD`.
    Is {
        /// The value tested.
        subject: Operand,
        /// The word, in the string pool.
        test: StrId,
    },
    /// Condition: `exists x.f`: the operand has a value (Absent is No, Unknown stays Unknown).
    Exists {
        /// The operand that must have a value.
        subject: Operand,
    },
    /// Condition: `x has attr "k"`: the node carries attribute `k`.
    HasAttr {
        /// The node variable.
        var: VarId,
        /// The attribute name, in the string pool.
        attr: StrId,
    },
    /// Condition: `x is` a snippet: the node's span is exactly a match of the grammar
    /// pattern (metavariables allowed) found by parsing the file's text; Unknown without text.
    MatchSnippet {
        /// The node variable tested.
        var: VarId,
        /// The pattern's language tag, in the string pool.
        lang: StrId,
        /// The pattern text, in the string pool.
        pattern: StrId,
        /// `as KIND` cast: the node need only lie inside a match (the binder's kind selects
        /// the node) instead of being exactly a match.
        within: bool,
    },
    /// Condition: `x under p`: the segment-wise path or module prefix test (`a.b` is under `a`,
    /// `ab` is not).
    Under {
        /// The value tested.
        subject: Operand,
        /// The prefix.
        prefix: Operand,
    },
    /// Condition: `x in unit u`: `u` is the nearest enclosing canonical unit of `x`.
    InUnit {
        /// The contained node.
        sub: VarId,
        /// The unit.
        unit: VarId,
    },
}

/// An `unresolved when COND because "reason"` clause: a binding for which the condition is Yes
/// or Unknown is Unresolved with the reason, replacing fire or clean (grl-spec.md 7.0.5).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Unresolved {
    /// The condition, over the `find` variables.
    pub when: OpId,
    /// The reason text (string pool).
    pub reason: StrId,
}

/// A `report` clause: the first whose `when` holds produces the finding.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Report {
    /// Guard condition, or none for an unconditional report.
    pub when: Option<OpId>,
    /// Variable the primary span is taken from.
    pub subject: VarId,
    /// Message template (string pool).
    pub message: StrId,
}

/// The unvalidated fields of a plan; hand them to [`Plan::new`] to get a runnable plan.
///
/// [`Plan::new`]: super::Plan::new
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlanParts {
    /// Rule id, for example `TODO001`.
    pub rule: String,
    /// Where the rule came from.
    pub provenance: Provenance,
    /// Rule polarity.
    pub polarity: Polarity,
    /// Languages it applies to.
    pub langs: Langs,
    /// Declared side relations.
    pub reads: ReadSet,
    /// Node kinds a file must contain (any of) for the plan to run; strictly ascending.
    pub prefilter: Vec<StrId>,
    /// Declared cost class.
    pub cost: CostClass,
    /// Number of variable slots.
    pub vars: u16,
    /// String pool.
    pub strings: Vec<String>,
    /// Op arena.
    pub ops: Vec<Op>,
    /// Defs in text order; a def body calls only earlier defs.
    pub defs: Vec<Def>,
    /// Top-level clauses in planner order.
    pub clauses: Vec<OpId>,
    /// P- only: how many leading clauses select the rule's subjects (the `find`s and their
    /// `where`); the rest describe the good thing, whose absence fires (7.0.5). Zero otherwise.
    pub subjects: u16,
    /// `unresolved when` clauses in text order.
    pub unresolved: Vec<Unresolved>,
    /// Reports in text order.
    pub reports: Vec<Report>,
}

/// The kind word a lowered snippet binder ranges over: every node (no GRL kind word spells it,
/// so the GRL words `node` and `cell` stay free for the model's row kinds).
///
/// frob:ticket 01M5ETB7SWJPH7EVK97WHEVEHY
pub const ANY_NODES: &str = "<any node>";
