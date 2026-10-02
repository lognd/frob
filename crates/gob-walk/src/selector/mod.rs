//! Selector expressions (grmb-spec 6): parser, canonical printer and the shared evaluator.
//!
//! A [`Selector`] is a typed tree with byte spans. Evaluation is generic over [`Leaves`]:
//! the file layer ([`crate::select_files`]) and the unit layer (gob-ir) supply the truth of
//! each leaf and the combinators here produce [`Row`]s (specificity plus truth), so both
//! layers and the owner function share one set of semantics.

mod glob;
mod lex;
mod parse;
mod print;

use std::fmt;

pub use glob::{Glob, GlobError, wildcard_match};
pub use parse::{Span, SyntaxError};

use crate::specificity::Specificity;

/// Kleene three-valued truth of a membership question.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub enum Tri {
    /// Definitely not a member (ordered lowest, so `min` is conjunction).
    No,
    /// Not decided by the available facts.
    Unknown,
    /// Definitely a member.
    Yes,
}

impl Tri {
    /// Lifts a boolean.
    pub const fn from_bool(b: bool) -> Self {
        if b { Self::Yes } else { Self::No }
    }
}

impl std::ops::Not for Tri {
    type Output = Self;
    fn not(self) -> Self {
        match self {
            Self::Yes => Self::No,
            Self::No => Self::Yes,
            Self::Unknown => Self::Unknown,
        }
    }
}

/// A comparison operator of an `attr` predicate.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum Cmp {
    /// `=`
    Eq,
    /// `!=`
    Ne,
    /// `~` (glob match on the string value)
    Match,
    /// `<=` (quantity comparison)
    Le,
}

impl Cmp {
    /// The operator as spelled in a selector.
    pub const fn symbol(self) -> &'static str {
        match self {
            Self::Eq => "=",
            Self::Ne => "!=",
            Self::Match => "~",
            Self::Le => "<=",
        }
    }
}

/// The right-hand side of an `attr` comparison.
#[derive(Clone, PartialEq, Eq, Hash, Debug)]
pub enum Value {
    /// A quoted string.
    Str(String),
    /// A number, as written.
    Number(String),
    /// A number with a unit from the closed table of grmb-spec 2.2.
    Quantity {
        /// The number, as written.
        number: String,
        /// The unit, for example `s`, `KiB` or `req/s`.
        unit: String,
    },
    /// A bare identifier such as `pub`.
    Ident(String),
}

/// An `attr(name [cmp value])` predicate.
#[derive(Clone, PartialEq, Eq, Hash, Debug)]
pub struct AttrPred {
    /// The attribute name.
    pub name: String,
    /// The comparison, absent for a bare presence test.
    pub test: Option<(Cmp, Value)>,
}

/// A selector expression node without its span.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Expr {
    /// A quoted glob string.
    Glob(Glob),
    /// `lang(L)`
    Lang(String),
    /// `kind(k1, k2)`
    Kind(Vec<String>),
    /// `attr(...)`
    Attr(AttrPred),
    /// `!e`
    Not(Box<Node>),
    /// `a & b & ...` (at least two operands)
    And(Vec<Node>),
    /// `a | b | ...` (at least two operands)
    Or(Vec<Node>),
}

/// An expression with the byte span it was parsed from; equality ignores the span.
#[derive(Clone, Debug)]
pub struct Node {
    /// The expression.
    pub expr: Expr,
    /// Where it came from in the source text (offset-corrected by the caller's base).
    pub span: Span,
}

impl PartialEq for Node {
    fn eq(&self, other: &Self) -> bool {
        self.expr == other.expr
    }
}

impl Eq for Node {}

/// A parsed selector.
///
/// ```
/// use gob_walk::Selector;
/// let s = Selector::parse(r#""crates/*/src/**" & lang(rust) & !kind(module)"#).unwrap();
/// assert_eq!(s.to_string(), r#""crates/*/src/**" & lang(rust) & !kind(module)"#);
/// ```
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Selector {
    root: Node,
}

/// One way a selector can match an item: its specificity and how certain the match is.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub struct Row {
    /// Specificity of the matching branch (grmb-spec 6.5).
    pub spec: Specificity,
    /// Certainty of the match, never [`Tri::No`].
    pub truth: Tri,
}

/// The truth of each selector leaf for one item; supplied by the evaluation layer.
pub trait Leaves {
    /// Membership under a glob string (PATH and QUALNAME).
    fn glob(&self, glob: &Glob) -> Tri;
    /// Membership under `lang(L)`.
    fn lang(&self, lang: &str) -> Tri;
    /// Membership under `kind(...)`.
    fn kind(&self, kinds: &[String]) -> Tri;
    /// Membership under `attr(...)`.
    fn attr(&self, pred: &AttrPred) -> Tri;
}

impl Selector {
    /// Wraps an already-built root node.
    pub fn new(root: Node) -> Self {
        Self { root }
    }

    /// Parses selector text; spans are byte offsets into `text`.
    ///
    /// # Errors
    ///
    /// Returns the syntax errors, each with the exact span (MDL009 conditions included).
    pub fn parse(text: &str) -> Result<Self, Vec<SyntaxError>> {
        Self::parse_at(text, 0)
    }

    /// Parses selector text found at byte `base` of its file; spans include the offset.
    ///
    /// # Errors
    ///
    /// Returns the syntax errors, each with the exact span in file coordinates.
    pub fn parse_at(text: &str, base: usize) -> Result<Self, Vec<SyntaxError>> {
        parse::parse(text, base).map(Self::new)
    }

    /// The root node.
    pub fn root(&self) -> &Node {
        &self.root
    }

    /// The glob when the whole selector is one LITERAL glob (grmb-spec 6.4 item 5).
    pub fn literal(&self) -> Option<&Glob> {
        match &self.root.expr {
            Expr::Glob(g) if g.is_literal() => Some(g),
            _ => None,
        }
    }

    /// The ways this selector matches an item whose leaves are `leaves`.
    ///
    /// Empty means no match. The selector's truth is the best row's truth ([`truth_of`]).
    pub fn rows<L: Leaves + ?Sized>(&self, leaves: &L) -> Vec<Row> {
        rows_of(&self.root, leaves)
    }

    /// The Kleene truth of membership for an item whose leaves are `leaves`.
    pub fn truth<L: Leaves + ?Sized>(&self, leaves: &L) -> Tri {
        truth_of(&self.rows(leaves))
    }
}

impl fmt::Display for Selector {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        print::write_node(f, &self.root, 0)
    }
}

/// The truth of a row set: the best row, or [`Tri::No`] when empty.
pub fn truth_of(rows: &[Row]) -> Tri {
    rows.iter().map(|r| r.truth).max().unwrap_or(Tri::No)
}

/// Drops duplicate and dominated rows and sorts the rest.
fn prune(mut rows: Vec<Row>) -> Vec<Row> {
    rows.sort_unstable();
    rows.dedup();
    let all = rows.clone();
    rows.retain(|r| {
        !all.iter()
            .any(|o| o != r && o.spec >= r.spec && o.truth >= r.truth)
    });
    rows
}

fn leaf(t: Tri, spec: Specificity) -> Vec<Row> {
    if t == Tri::No {
        Vec::new()
    } else {
        vec![Row { spec, truth: t }]
    }
}

fn rows_of<L: Leaves + ?Sized>(node: &Node, l: &L) -> Vec<Row> {
    match &node.expr {
        Expr::Glob(g) => leaf(l.glob(g), g.specificity()),
        Expr::Lang(v) => leaf(l.lang(v), Specificity::predicate()),
        Expr::Kind(ks) => leaf(l.kind(ks), Specificity::predicate()),
        Expr::Attr(a) => leaf(l.attr(a), Specificity::predicate()),
        Expr::Not(inner) => {
            let t = !truth_of(&rows_of(inner, l));
            leaf(t, Specificity::BOTTOM)
        }
        Expr::And(ops) => {
            let mut acc = vec![Row {
                spec: Specificity::BOTTOM,
                truth: Tri::Yes,
            }];
            for op in ops {
                let rs = rows_of(op, l);
                acc = prune(
                    acc.iter()
                        .flat_map(|a| {
                            rs.iter().map(|b| Row {
                                spec: a.spec.and(b.spec),
                                truth: a.truth.min(b.truth),
                            })
                        })
                        .collect(),
                );
                if acc.is_empty() {
                    break;
                }
            }
            acc
        }
        Expr::Or(ops) => prune(ops.iter().flat_map(|o| rows_of(o, l)).collect()),
    }
}

#[cfg(test)]
mod tests;
