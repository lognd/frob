//! The `const_value` capability: the bounded static value of an expression
//! (language-engines.md section 2, universal-model.md 4.4 and 5.1, query Q50).
//!
//! The evaluator reads the universal forms an adapter lowers constants to and
//! never executes code. Every node visited costs one step of the [`Budget`];
//! when the budget runs out, or a form is not understood, the answer is
//! [`ConstValue::Unknown`] for that subterm, never a guess.
//!
//! # Lowered forms
//!
//! | Source | Term |
//! |---|---|
//! | string, integer, boolean, null literal | `lit(kind = str / int / bool / null, lexeme)`; a `str` lexeme is the decoded text, not the quoted source |
//! | name of a constant | `ref(name)` resolving to a `unit(kind = const)` whose first non-attachment child is its value |
//! | `a + b + ...` | `apply(op)` with head `lit(op, "+")` and the operands as arguments |
//! | template literal | `apply(op)` head `lit(op, "template")`; arguments are `lit(str)` quasis and expressions in order |
//! | `c ? a : b` | `apply(op)` head `lit(op, "?:")`, arguments `c`, `a`, `b` |
//! | array literal | `apply(op)` head `lit(op, "array")`, arguments are the elements |
//! | object literal | `apply(op)` head `lit(op, "object")`, arguments are `apply(op)` head `lit(op, "prop")` with the key `lit(str)` then the value |
//!
//! Anything else (calls, unresolved names, spreads) is `Unknown`.

use std::collections::{BTreeMap, BTreeSet};

use tracing::{debug, trace};

use crate::operator::{Operator, Universal};
use crate::query::Model;
use crate::scope::Resolution;
use crate::term::NodeId;

/// Head kind of the operator forms in the module table.
pub const OP: &str = "op";
/// Operator lexeme of string concatenation and integer addition.
pub const OP_ADD: &str = "+";
/// Operator lexeme of the conditional expression.
pub const OP_COND: &str = "?:";
/// Operator lexeme of a template literal.
pub const OP_TEMPLATE: &str = "template";
/// Operator lexeme of an array literal.
pub const OP_ARRAY: &str = "array";
/// Operator lexeme of an object literal.
pub const OP_OBJECT: &str = "object";
/// Operator lexeme of one object entry.
pub const OP_PROP: &str = "prop";
/// Operator lexeme of the logical and (`cond && value`).
pub const OP_AND: &str = "&&";
/// Unit kind of a named constant.
pub const CONST_KIND: &str = "const";

/// The default number of steps one evaluation may take.
pub const DEFAULT_STEPS: u32 = 256;
/// The largest `OneOf` set kept; a bigger one collapses to `Unknown`.
pub const MAX_ONE_OF: usize = 64;

/// A fully known constant.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum Value {
    /// A string.
    Str(String),
    /// An integer.
    Int(i64),
    /// A boolean.
    Bool(bool),
    /// `null` / `None` / `undefined`.
    Null,
    /// An array of known values.
    Array(Vec<Value>),
    /// An object with known keys and values.
    Object(BTreeMap<String, Value>),
}

/// One piece of a partially known string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Fragment {
    /// Text that is certainly there.
    Known(String),
    /// A dynamic part of unknown content.
    Unknown,
}

/// The bounded static value of an expression.
///
/// ```
/// use gob_ir::const_value::ConstValue;
/// assert!(ConstValue::Unknown.known().is_none());
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConstValue {
    /// Exactly this value.
    Known(Value),
    /// One of these values (a conditional or a may-resolution); sorted, deduplicated.
    OneOf(Vec<Value>),
    /// A string made of known text and unknown parts, in order; never adjacent knowns.
    Fragments(Vec<Fragment>),
    /// Nothing can be claimed.
    Unknown,
}

impl ConstValue {
    /// The value when it is `Known`.
    pub fn known(&self) -> Option<&Value> {
        match self {
            Self::Known(v) => Some(v),
            _ => None,
        }
    }

    /// The string when it is a `Known` string.
    pub fn known_str(&self) -> Option<&str> {
        match self {
            Self::Known(Value::Str(s)) => Some(s),
            _ => None,
        }
    }

    fn one_of(values: BTreeSet<Value>) -> Self {
        match values.len() {
            0 => Self::Unknown,
            1 => Self::Known(values.into_iter().next().unwrap_or(Value::Null)),
            n if n > MAX_ONE_OF => Self::Unknown,
            _ => Self::OneOf(values.into_iter().collect()),
        }
    }

    /// The alternatives of a value: one for `Known`, several for `OneOf`, none otherwise.
    fn alternatives(&self) -> Option<Vec<Value>> {
        match self {
            Self::Known(v) => Some(vec![v.clone()]),
            Self::OneOf(vs) => Some(vs.clone()),
            Self::Fragments(_) | Self::Unknown => None,
        }
    }

    /// The fragments of a string-like value (known strings become one known fragment).
    fn fragments(&self) -> Vec<Fragment> {
        match self {
            Self::Known(Value::Str(s)) => vec![Fragment::Known(s.clone())],
            Self::Known(Value::Int(i)) => vec![Fragment::Known(i.to_string())],
            Self::Known(Value::Bool(b)) => vec![Fragment::Known(b.to_string())],
            Self::Fragments(f) => f.clone(),
            _ => vec![Fragment::Unknown],
        }
    }
}

/// How many nodes one evaluation may visit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Budget(pub u32);

impl Default for Budget {
    fn default() -> Self {
        Self(DEFAULT_STEPS)
    }
}

/// The bounded evaluator; one instance per query so the budget is shared by the whole expression.
#[derive(Debug)]
pub struct ConstEval<'m> {
    model: &'m Model,
    left: u32,
    exhausted: bool,
}

/// The bounded value of the expression at `node` within the default [`Budget`].
///
/// ```
/// use gob_ir::{Location, Model, NodeSpec, Operator, TermBuilder};
/// use gob_ir::const_value::{ConstValue, Value, const_value};
/// use gob_text::FileInterner;
///
/// let mut files = FileInterner::new();
/// let f = files.intern("a.ts");
/// let mut b = TermBuilder::new("a.ts", "ts");
/// let s = b.node(NodeSpec::new(Operator::lit("str", "btn"), Location::text(f, 0, 3)), &[]).unwrap();
/// let m = Model::lexical(b.finish(s).unwrap());
/// assert_eq!(const_value(&m, s), ConstValue::Known(Value::Str("btn".into())));
/// ```
pub fn const_value(model: &Model, node: NodeId) -> ConstValue {
    ConstEval::new(model, Budget::default()).eval(node)
}

impl<'m> ConstEval<'m> {
    /// An evaluator over `model` with `budget` steps.
    pub fn new(model: &'m Model, budget: Budget) -> Self {
        Self {
            model,
            left: budget.0,
            exhausted: false,
        }
    }

    /// Whether the budget ran out during any evaluation so far.
    pub fn exhausted(&self) -> bool {
        self.exhausted
    }

    /// Evaluate the expression at `node`.
    pub fn eval(&mut self, node: NodeId) -> ConstValue {
        if self.left == 0 {
            if !self.exhausted {
                debug!(%node, "const_value step budget exhausted");
            }
            self.exhausted = true;
            return ConstValue::Unknown;
        }
        self.left -= 1;
        let term = self.model.term();
        let n = term.node(node);
        trace!(%node, op = %n.op, "const_value step");
        match &n.op {
            Operator::Universal(Universal::Lit { kind, lexeme }) => lit(kind, lexeme),
            Operator::Universal(Universal::Ref { .. }) => self.eval_ref(node),
            Operator::Universal(Universal::Apply { .. }) => self.eval_apply(node),
            _ => ConstValue::Unknown,
        }
    }

    fn eval_ref(&mut self, node: NodeId) -> ConstValue {
        let decls: Vec<_> = match self.model.resolve_node(node) {
            Resolution::Must(d) => vec![d],
            Resolution::May(ds) => ds.into_iter().collect(),
            Resolution::Unknown => return ConstValue::Unknown,
        };
        let mut all = BTreeSet::new();
        for d in decls {
            let decl = self.model.scopes().decl(d);
            let Some(value) = decl.nodes.iter().find_map(|&u| self.const_init(u)) else {
                return ConstValue::Unknown;
            };
            match self.eval(value).alternatives() {
                Some(alts) => all.extend(alts),
                None => return ConstValue::Unknown,
            }
        }
        ConstValue::one_of(all)
    }

    /// The value child of a `unit(kind = const)`.
    fn const_init(&self, unit: NodeId) -> Option<NodeId> {
        let term = self.model.term();
        let n = term.node(unit);
        match &n.op {
            Operator::Universal(Universal::Unit { kind, .. }) if kind == CONST_KIND => n
                .children
                .iter()
                .copied()
                .find(|&c| !term.node(c).op.is_attachment()),
            _ => None,
        }
    }

    fn eval_apply(&mut self, node: NodeId) -> ConstValue {
        let Some((op, args)) = op_form(self.model, node) else {
            return ConstValue::Unknown;
        };
        match op.as_str() {
            OP_ADD => self.concat(&args, true),
            OP_TEMPLATE => self.concat(&args, false),
            OP_COND => self.cond(&args),
            OP_ARRAY => self.array(&args),
            OP_OBJECT => self.object(&args),
            _ => ConstValue::Unknown,
        }
    }

    fn concat(&mut self, args: &[NodeId], add: bool) -> ConstValue {
        let parts: Vec<ConstValue> = args.iter().map(|&a| self.eval(a)).collect();
        if let Some(sum) = int_sum(&parts).filter(|_| add) {
            return ConstValue::Known(Value::Int(sum));
        }
        let mut frags: Vec<Fragment> = Vec::new();
        for part in &parts {
            for f in part.fragments() {
                match (frags.last_mut(), f) {
                    (Some(Fragment::Known(a)), Fragment::Known(b)) => a.push_str(&b),
                    (Some(Fragment::Unknown), Fragment::Unknown) => {}
                    (_, f) => frags.push(f),
                }
            }
        }
        match frags.as_slice() {
            [] => ConstValue::Known(Value::Str(String::new())),
            [Fragment::Known(s)] => ConstValue::Known(Value::Str(s.clone())),
            [Fragment::Unknown] => ConstValue::Unknown,
            _ => ConstValue::Fragments(frags),
        }
    }

    fn cond(&mut self, args: &[NodeId]) -> ConstValue {
        let [test, then, other] = *args else {
            return ConstValue::Unknown;
        };
        match self.eval(test).known() {
            Some(Value::Bool(true)) => return self.eval(then),
            Some(Value::Bool(false)) => return self.eval(other),
            _ => {}
        }
        let (yes, no) = (self.eval(then), self.eval(other));
        match (yes.alternatives(), no.alternatives()) {
            (Some(mut left), Some(right)) => {
                left.extend(right);
                ConstValue::one_of(left.into_iter().collect())
            }
            _ => ConstValue::Unknown,
        }
    }

    fn array(&mut self, args: &[NodeId]) -> ConstValue {
        let mut out = Vec::with_capacity(args.len());
        for &a in args {
            match self.eval(a) {
                ConstValue::Known(v) => out.push(v),
                _ => return ConstValue::Unknown,
            }
        }
        ConstValue::Known(Value::Array(out))
    }

    fn object(&mut self, args: &[NodeId]) -> ConstValue {
        let mut out = BTreeMap::new();
        for &a in args {
            let Some((op, kv)) = op_form(self.model, a) else {
                return ConstValue::Unknown;
            };
            let [k, v] = kv.as_slice() else {
                return ConstValue::Unknown;
            };
            if op != OP_PROP {
                return ConstValue::Unknown;
            }
            let (ConstValue::Known(Value::Str(key)), ConstValue::Known(val)) =
                (self.eval(*k), self.eval(*v))
            else {
                return ConstValue::Unknown;
            };
            out.insert(key, val);
        }
        ConstValue::Known(Value::Object(out))
    }
}

/// The operator lexeme and arguments of an `apply(op)` node, if it is one.
pub(crate) fn op_form(model: &Model, node: NodeId) -> Option<(String, Vec<NodeId>)> {
    let term = model.term();
    let n = term.node(node);
    if !matches!(&n.op, Operator::Universal(Universal::Apply { kind }) if kind == OP) {
        return None;
    }
    let (&head, args) = n.children.split_first()?;
    match &term.node(head).op {
        Operator::Universal(Universal::Lit { kind, lexeme }) if kind == OP => {
            Some((lexeme.clone(), args.to_vec()))
        }
        _ => None,
    }
}

fn lit(kind: &str, lexeme: &str) -> ConstValue {
    match kind {
        "str" => ConstValue::Known(Value::Str(lexeme.to_owned())),
        "int" => lexeme
            .parse()
            .map_or(ConstValue::Unknown, |i| ConstValue::Known(Value::Int(i))),
        "bool" => match lexeme {
            "true" => ConstValue::Known(Value::Bool(true)),
            "false" => ConstValue::Known(Value::Bool(false)),
            _ => ConstValue::Unknown,
        },
        "null" => ConstValue::Known(Value::Null),
        _ => ConstValue::Unknown,
    }
}

/// The sum when every part is a known integer (so `1 + 2` is `3`, not `"12"`).
fn int_sum(parts: &[ConstValue]) -> Option<i64> {
    if parts.is_empty() {
        return None;
    }
    parts.iter().try_fold(0i64, |acc, p| match p {
        ConstValue::Known(Value::Int(i)) => acc.checked_add(*i),
        _ => None,
    })
}
