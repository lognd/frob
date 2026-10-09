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

/// A side relation a rule may read (grl-spec.md section 6); declared in `needs`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Need {
    /// `config.<table>`.
    Config,
    /// `diff.changed`, `diff.added`.
    Diff,
    /// `lease.globs`, `lease.ticket`.
    Lease,
    /// `model.nodes`, `model.selectors`.
    Model,
}

impl Need {
    /// Every need, in bit order.
    pub const ALL: [Need; 4] = [Need::Config, Need::Diff, Need::Lease, Need::Model];

    /// The relation's GRL name.
    pub fn name(self) -> &'static str {
        match self {
            Need::Config => "config",
            Need::Diff => "diff",
            Need::Lease => "lease",
            Need::Model => "model",
        }
    }

    pub(super) fn bit(self) -> u8 {
        1 << (self as u8)
    }
}

/// The set of side relations a plan declares, as a bitset (canonical by construction).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct NeedSet(pub(super) u8);

impl NeedSet {
    /// A set holding exactly `needs`.
    pub fn of(needs: &[Need]) -> Self {
        NeedSet(needs.iter().fold(0, |acc, n| acc | n.bit()))
    }

    /// Whether `need` is declared.
    pub fn contains(self, need: Need) -> bool {
        self.0 & need.bit() != 0
    }

    /// The declared needs in bit order.
    pub fn iter(self) -> impl Iterator<Item = Need> {
        Need::ALL.into_iter().filter(move |n| self.contains(*n))
    }

    /// Raw bits (only the low four are ever valid).
    pub(super) fn valid(self) -> bool {
        self.0 >> Need::ALL.len() == 0
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
        /// The relation, which must be in `needs`.
        need: Need,
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
    pub needs: NeedSet,
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
    /// Reports in text order.
    pub reports: Vec<Report>,
}
