//! The signature: sorts and the thirteen universal operators plus adapter
//! operators (universal-model.md 2.3).

use std::fmt;

/// The result sort of an operator.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Sort {
    /// A declaration (`unit`, `anon`, `attr`).
    Decl,
    /// A use of a name (`ref`).
    Use,
    /// An expression-like term.
    Exp,
    /// Trivia (`comment`).
    Trivia,
    /// Any sort (`hole`, `opaque`).
    Any,
}

impl Sort {
    /// Lowercase sort name.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Decl => "decl",
            Self::Use => "use",
            Self::Exp => "exp",
            Self::Trivia => "trivia",
            Self::Any => "any",
        }
    }
}

/// The ordering discipline of a `group` (universal-model.md 2.3).
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum GroupOrder {
    /// Evaluated in order.
    Sequence,
    /// No order.
    Unordered,
    /// Dependency (topological) order.
    Topological,
    /// Concurrent.
    Concurrent,
    /// Backtracking search order.
    Backtracking,
    /// Clocked.
    Clocked,
    /// User-driven history (notebooks).
    UserHistory,
    /// Not known.
    Unknown,
    /// An adapter-declared discipline.
    Other(String),
}

impl GroupOrder {
    /// Stable lowercase spelling (`user-history`).
    pub fn as_str(&self) -> &str {
        match self {
            Self::Sequence => "sequence",
            Self::Unordered => "unordered",
            Self::Topological => "topological",
            Self::Concurrent => "concurrent",
            Self::Backtracking => "backtracking",
            Self::Clocked => "clocked",
            Self::UserHistory => "user-history",
            Self::Unknown => "unknown",
            Self::Other(s) => s,
        }
    }
}

/// The thirteen universal operators with their parameters.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Universal {
    /// A nameable entity; `role` distinguishes parts of one identity.
    Unit {
        /// Module, function, type, cell, ...
        kind: String,
        /// Signature, equation, implementation, ...
        role: String,
    },
    /// An entity with no source name.
    Anon {
        /// Lambda, train, block, ...
        kind: String,
    },
    /// A use of a name; resolution lives in the scope graph.
    Ref {
        /// The spelled name.
        name: String,
    },
    /// Application in the widest sense; child 0 is the head.
    Apply {
        /// Call, send, instantiate, dataflow, ...
        kind: String,
    },
    /// A non-unit binder; child 0 is the scope, child 1 the optional rhs.
    Bind {
        /// Let, pattern, logic, loop, ...
        kind: String,
        /// Multiplicity or grade.
        mode: String,
    },
    /// A container with an ordering discipline.
    Group {
        /// The ordering discipline.
        order: GroupOrder,
    },
    /// A literal.
    Lit {
        /// Literal kind (`str`, `int`, ...).
        kind: String,
        /// The exact lexeme.
        lexeme: String,
    },
    /// An attribute attached to its parent (the target).
    Attr {
        /// Attribute name (`doc`, `derive`, ...).
        name: String,
    },
    /// A comment, attached to its parent.
    Comment {
        /// Comment text.
        text: String,
    },
    /// A boundary rules care about.
    Region {
        /// Unsafe, ffi, transaction, clocked, island, ...
        kind: String,
    },
    /// A metaprogramming site; the optional second child is the expansion.
    Phase {
        /// Macro, template, comptime, ...
        kind: String,
    },
    /// A typed hole or parse error.
    Hole {
        /// Hole kind.
        kind: String,
    },
    /// Everything else, with the raw payload bytes.
    Opaque {
        /// Reason code, for example `annotation-required:signature`.
        reason: String,
        /// Raw bytes, readable by lexical queries.
        payload: Vec<u8>,
    },
}

/// A language-specific operator extending the universal signature.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct AdapterOp {
    /// Language tag (`rust`, `prolog`).
    pub lang: String,
    /// Operator name (`impl`, `clause`).
    pub name: String,
    /// The universal sort through which universal rules see it.
    pub sort: Sort,
}

/// An operator of `Sigma_U` + `Sigma_L`.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Operator {
    /// One of the thirteen universal operators.
    Universal(Universal),
    /// A language operator.
    Adapter(AdapterOp),
}

impl Operator {
    /// A `unit(kind, role)`.
    pub fn unit(kind: &str, role: &str) -> Self {
        Self::Universal(Universal::Unit {
            kind: kind.into(),
            role: role.into(),
        })
    }
    /// An `anon(kind)`.
    pub fn anon(kind: &str) -> Self {
        Self::Universal(Universal::Anon { kind: kind.into() })
    }
    /// A `ref(name)`.
    pub fn reference(name: &str) -> Self {
        Self::Universal(Universal::Ref { name: name.into() })
    }
    /// An `apply(kind)`.
    pub fn apply(kind: &str) -> Self {
        Self::Universal(Universal::Apply { kind: kind.into() })
    }
    /// A `bind(kind, mode)`.
    pub fn bind(kind: &str, mode: &str) -> Self {
        Self::Universal(Universal::Bind {
            kind: kind.into(),
            mode: mode.into(),
        })
    }
    /// A `group(order)`.
    pub fn group(order: GroupOrder) -> Self {
        Self::Universal(Universal::Group { order })
    }
    /// A `lit(kind, lexeme)`.
    pub fn lit(kind: &str, lexeme: &str) -> Self {
        Self::Universal(Universal::Lit {
            kind: kind.into(),
            lexeme: lexeme.into(),
        })
    }
    /// An `attr(name)`.
    pub fn attr(name: &str) -> Self {
        Self::Universal(Universal::Attr { name: name.into() })
    }
    /// A `comment(text)`.
    pub fn comment(text: &str) -> Self {
        Self::Universal(Universal::Comment { text: text.into() })
    }
    /// A `region(kind)`.
    pub fn region(kind: &str) -> Self {
        Self::Universal(Universal::Region { kind: kind.into() })
    }
    /// A `phase(kind)`.
    pub fn phase(kind: &str) -> Self {
        Self::Universal(Universal::Phase { kind: kind.into() })
    }
    /// A `hole(kind)`.
    pub fn hole(kind: &str) -> Self {
        Self::Universal(Universal::Hole { kind: kind.into() })
    }
    /// An `opaque(reason, payload)`.
    pub fn opaque(reason: &str, payload: &[u8]) -> Self {
        Self::Universal(Universal::Opaque {
            reason: reason.into(),
            payload: payload.to_vec(),
        })
    }
    /// An adapter operator seen as `sort` by universal rules.
    pub fn adapter(lang: &str, name: &str, sort: Sort) -> Self {
        Self::Adapter(AdapterOp {
            lang: lang.into(),
            name: name.into(),
            sort,
        })
    }

    /// The result sort of this operator.
    pub fn sort(&self) -> Sort {
        match self {
            Self::Universal(u) => match u {
                Universal::Unit { .. } | Universal::Anon { .. } | Universal::Attr { .. } => {
                    Sort::Decl
                }
                Universal::Ref { .. } => Sort::Use,
                Universal::Apply { .. }
                | Universal::Bind { .. }
                | Universal::Group { .. }
                | Universal::Lit { .. }
                | Universal::Region { .. }
                | Universal::Phase { .. } => Sort::Exp,
                Universal::Comment { .. } => Sort::Trivia,
                Universal::Hole { .. } | Universal::Opaque { .. } => Sort::Any,
            },
            Self::Adapter(a) => a.sort,
        }
    }

    /// The operator name without parameters (`unit`, `rust.impl`).
    pub fn tag(&self) -> String {
        match self {
            Self::Universal(u) => u.tag().to_owned(),
            Self::Adapter(a) => format!("{}.{}", a.lang, a.name),
        }
    }

    /// True for `opaque`.
    pub fn is_opaque(&self) -> bool {
        matches!(self, Self::Universal(Universal::Opaque { .. }))
    }

    /// True for `hole`.
    pub fn is_hole(&self) -> bool {
        matches!(self, Self::Universal(Universal::Hole { .. }))
    }

    /// True for `unit` or `anon`.
    pub fn is_unit_like(&self) -> bool {
        matches!(
            self,
            Self::Universal(Universal::Unit { .. } | Universal::Anon { .. })
        )
    }

    /// True for `attr` and `comment`, the attachment operators.
    pub fn is_attachment(&self) -> bool {
        matches!(
            self,
            Self::Universal(Universal::Attr { .. } | Universal::Comment { .. })
        )
    }

    /// Whether the abstractor of a node with this operator scopes over child `index`.
    pub(crate) fn binds_over(&self, index: usize) -> bool {
        match self {
            Self::Universal(Universal::Bind { .. }) => index == 0,
            _ => true,
        }
    }

    /// Whether nodes of this operator may carry abstractors.
    pub(crate) fn may_bind(&self) -> bool {
        matches!(
            self,
            Self::Adapter(_)
                | Self::Universal(
                    Universal::Unit { .. } | Universal::Anon { .. } | Universal::Bind { .. }
                )
        )
    }
}

impl Universal {
    /// The operator name without parameters.
    pub const fn tag(&self) -> &'static str {
        match self {
            Self::Unit { .. } => "unit",
            Self::Anon { .. } => "anon",
            Self::Ref { .. } => "ref",
            Self::Apply { .. } => "apply",
            Self::Bind { .. } => "bind",
            Self::Group { .. } => "group",
            Self::Lit { .. } => "lit",
            Self::Attr { .. } => "attr",
            Self::Comment { .. } => "comment",
            Self::Region { .. } => "region",
            Self::Phase { .. } => "phase",
            Self::Hole { .. } => "hole",
            Self::Opaque { .. } => "opaque",
        }
    }
}

impl fmt::Display for Operator {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.tag())
    }
}
