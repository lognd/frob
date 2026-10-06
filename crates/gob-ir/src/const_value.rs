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
//! | `a && b`, `a \|\| b` | `apply(op)` head `lit(op, "&&")` / `lit(op, "\|\|")`, arguments `a`, `b` (JavaScript truthiness; an unknown `a` keeps both outcomes) |
//! | `...x` in an array, object or call | `apply(op)` head `lit(op, "spread")`, one argument |
//! | `f(a, b)` | `apply(call)` (or `apply(op)` head `lit(op, "call")`), the callee then the arguments; only a callee an [`ExternalRefs`] hook classifies is read (a class-name joiner such as `clsx`) |
//!
//! Anything else (unclassified calls, unresolved names) is `Unknown`.
//!
//! A `unit(kind = const)` may also carry the value inside a body `group` (after a `sig` facet group), which
//! is how the TypeScript adapter lowers `const x = value`.
//!
//! # Beyond one term
//!
//! A reference the scope graph cannot resolve (an import) is offered to the [`ExternalRefs`] hook of the
//! evaluator, which answers with the value it found in another artifact and the steps it used; so the budget
//! covers the whole chain. A reference cycle yields `Unknown` and sets [`ConstEval::cyclic`].

// frob:ticket 01M43ARXVD5PXP6ZBVFC2F4ZMQ

use std::collections::{BTreeMap, BTreeSet};

use tracing::{debug, trace};

use crate::attrs::reserved;
use crate::operator::{Operator, Universal};
use crate::query::Model;
use crate::scope::{DeclId, Resolution};
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
/// Operator lexeme of the logical or (`value || fallback`).
pub const OP_OR: &str = "||";
/// Operator lexeme of a spread element (`...x`).
pub const OP_SPREAD: &str = "spread";
/// Operator lexeme of a call (`f(a, b)`): the callee, then the arguments.
pub const OP_CALL: &str = "call";
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

/// What a call whose callee an [`ExternalRefs`] hook recognises does with its arguments.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum CallKind {
    /// `clsx`, `classnames`, `cn`: the truthy arguments joined with single spaces (strings, arrays, and
    /// objects keyed by class name with a condition as value).
    ClassNames,
}

/// A value found outside the term being evaluated, with what finding it cost.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct External {
    /// The value of the referenced constant.
    pub value: ConstValue,
    /// Steps the lookup used; subtracted from the evaluator's budget.
    pub used: u32,
    /// Whether the lookup ran out of budget.
    pub exhausted: bool,
    /// Whether the lookup met a reference cycle.
    pub cyclic: bool,
}

/// The seam through which an evaluator reaches beyond its own term (imports, wrapper calls).
pub trait ExternalRefs {
    /// The constant a `ref` the scope graph could not resolve stands for, given `steps` left of the budget.
    fn resolve_ref(&self, model: &Model, node: NodeId, steps: u32) -> Option<External>;

    /// How a call whose callee is the `ref` node `callee` behaves, when it is a known one.
    fn call_kind(&self, model: &Model, callee: NodeId) -> Option<CallKind>;
}

/// The bounded evaluator; one instance per query so the budget is shared by the whole expression.
pub struct ConstEval<'m> {
    model: &'m Model,
    left: u32,
    exhausted: bool,
    cyclic: bool,
    ext: Option<&'m dyn ExternalRefs>,
    visiting: Vec<DeclId>,
    consulted: Vec<NodeId>,
}

impl std::fmt::Debug for ConstEval<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ConstEval")
            .field("left", &self.left)
            .field("exhausted", &self.exhausted)
            .field("cyclic", &self.cyclic)
            .finish_non_exhaustive()
    }
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
            cyclic: false,
            ext: None,
            visiting: Vec::new(),
            consulted: Vec::new(),
        }
    }

    /// The same evaluator reaching through `ext` for references and calls it cannot read itself.
    #[must_use]
    pub fn with_external(mut self, ext: &'m dyn ExternalRefs) -> Self {
        self.ext = Some(ext);
        self
    }

    /// Whether the budget ran out during any evaluation so far.
    pub fn exhausted(&self) -> bool {
        self.exhausted
    }

    /// Whether a reference cycle was met during any evaluation so far.
    pub fn cyclic(&self) -> bool {
        self.cyclic
    }

    /// Steps left of the budget.
    pub fn remaining(&self) -> u32 {
        self.left
    }

    /// The value nodes of the constants read through scope resolution, in the order they were consulted.
    pub fn consulted(&self) -> &[NodeId] {
        &self.consulted
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
            Resolution::Unknown => return self.external_ref(node),
        };
        let mut all = BTreeSet::new();
        for d in decls {
            if self.visiting.contains(&d) {
                debug!(%node, "const_value reference cycle");
                self.cyclic = true;
                return ConstValue::Unknown;
            }
            let decl = self.model.scopes().decl(d);
            let Some(value) = decl
                .nodes
                .iter()
                .find_map(|&u| const_value_node(self.model, u))
            else {
                return ConstValue::Unknown;
            };
            self.consulted.push(value);
            self.visiting.push(d);
            let got = self.eval(value);
            self.visiting.pop();
            match got.alternatives() {
                Some(alts) => all.extend(alts),
                None => return ConstValue::Unknown,
            }
        }
        ConstValue::one_of(all)
    }

    /// The value of a reference the scope graph left unresolved, through the hook.
    fn external_ref(&mut self, node: NodeId) -> ConstValue {
        let Some(ext) = self.ext else {
            return ConstValue::Unknown;
        };
        let Some(found) = ext.resolve_ref(self.model, node, self.left) else {
            return ConstValue::Unknown;
        };
        self.left = self.left.saturating_sub(found.used);
        self.exhausted |= found.exhausted;
        self.cyclic |= found.cyclic;
        found.value
    }

    fn eval_apply(&mut self, node: NodeId) -> ConstValue {
        // An adapter's own call form: the callee reference, then the arguments.
        if let Operator::Universal(Universal::Apply { kind }) = &self.model.term().node(node).op
            && kind == "call"
        {
            let kids = self.model.term().node(node).children.clone();
            return self.call(&kids);
        }
        let Some((op, args)) = op_form(self.model, node) else {
            return ConstValue::Unknown;
        };
        match op.as_str() {
            OP_ADD => self.concat(&args, true),
            OP_TEMPLATE => self.concat(&args, false),
            OP_COND => self.cond(&args),
            OP_AND => self.and(&args),
            OP_OR => self.or(&args),
            OP_CALL => self.call(&args),
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
        if let Some(all) = text_product(&parts, add) {
            return all;
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

    fn and(&mut self, args: &[NodeId]) -> ConstValue {
        let [left, right] = *args else {
            return ConstValue::Unknown;
        };
        let l = self.eval(left);
        if let Some(v) = l.known() {
            return if truthy(v) { self.eval(right) } else { l };
        }
        // An unknown condition keeps both outcomes: the right value or a falsy one.
        match self.eval(right).alternatives() {
            Some(mut alts) => {
                alts.push(Value::Bool(false));
                ConstValue::one_of(alts.into_iter().collect())
            }
            None => ConstValue::Unknown,
        }
    }

    fn or(&mut self, args: &[NodeId]) -> ConstValue {
        let [left, right] = *args else {
            return ConstValue::Unknown;
        };
        let l = self.eval(left);
        let Some(alts) = l.alternatives() else {
            return ConstValue::Unknown;
        };
        let (truthy_alts, falsy): (Vec<Value>, Vec<Value>) = alts.into_iter().partition(truthy);
        if falsy.is_empty() {
            return ConstValue::one_of(truthy_alts.into_iter().collect());
        }
        let Some(mut rest) = self.eval(right).alternatives() else {
            return ConstValue::Unknown;
        };
        rest.extend(truthy_alts);
        ConstValue::one_of(rest.into_iter().collect())
    }

    /// The items of an array literal; a spread of a known array splices in its items.
    fn array(&mut self, args: &[NodeId]) -> ConstValue {
        let mut out = Vec::with_capacity(args.len());
        for &a in args {
            if let Some(inner) = spread_arg(self.model, a) {
                match self.eval(inner) {
                    ConstValue::Known(Value::Array(items)) => out.extend(items),
                    _ => return ConstValue::Unknown,
                }
                continue;
            }
            match self.eval(a) {
                ConstValue::Known(v) => out.push(v),
                _ => return ConstValue::Unknown,
            }
        }
        ConstValue::Known(Value::Array(out))
    }

    /// The entries of an object literal; a spread of a known object merges its entries.
    fn object(&mut self, args: &[NodeId]) -> ConstValue {
        let mut out = BTreeMap::new();
        for &a in args {
            if let Some(inner) = spread_arg(self.model, a) {
                match self.eval(inner) {
                    ConstValue::Known(Value::Object(entries)) => out.extend(entries),
                    _ => return ConstValue::Unknown,
                }
                continue;
            }
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

    /// A call: only a callee the hook classifies is read.
    fn call(&mut self, args: &[NodeId]) -> ConstValue {
        let Some((&callee, rest)) = args.split_first() else {
            return ConstValue::Unknown;
        };
        let kind = self.ext.and_then(|ext| ext.call_kind(self.model, callee));
        match kind {
            Some(CallKind::ClassNames) => self.class_names(rest),
            None => ConstValue::Unknown,
        }
    }

    /// `clsx(..)`: every argument contributes class text or nothing; the result is the space-joined text.
    fn class_names(&mut self, args: &[NodeId]) -> ConstValue {
        let mut parts: Vec<ClassPart> = Vec::new();
        for &a in args {
            self.class_part(a, &mut parts);
        }
        join_classes(&parts)
    }

    /// Appends what the clsx-style argument `node` contributes.
    fn class_part(&mut self, node: NodeId, out: &mut Vec<ClassPart>) {
        if let Some(inner) = spread_arg(self.model, node) {
            return self.class_part(inner, out);
        }
        if let Some((op, entries)) = op_form(self.model, node) {
            match op.as_str() {
                OP_ARRAY => {
                    for e in entries {
                        self.class_part(e, out);
                    }
                    return;
                }
                OP_OBJECT => {
                    for e in entries {
                        self.class_entry(e, out);
                    }
                    return;
                }
                OP_AND => {
                    // `cond && "x"` contributes "x" or nothing; `cond && [..]` likewise.
                    if let [cond, then] = entries.as_slice() {
                        let c = self.eval(*cond);
                        match c.known() {
                            Some(v) if !truthy(v) => {}
                            Some(_) => self.class_part(*then, out),
                            None => {
                                let mut inner = Vec::new();
                                self.class_part(*then, &mut inner);
                                out.push(ClassPart::Maybe(inner));
                            }
                        }
                        return;
                    }
                }
                _ => {}
            }
        }
        let v = self.eval(node);
        out.push(ClassPart::from_value(&v));
    }

    /// One `{ "class": condition }` entry of a clsx object argument.
    fn class_entry(&mut self, entry: NodeId, out: &mut Vec<ClassPart>) {
        if let Some(inner) = spread_arg(self.model, entry) {
            return self.class_part(inner, out);
        }
        let Some((op, kv)) = op_form(self.model, entry) else {
            return out.push(ClassPart::Dynamic);
        };
        let ([k, v], true) = (kv.as_slice(), op == OP_PROP) else {
            return out.push(ClassPart::Dynamic);
        };
        let Some(key) = self.eval(*k).known_str().map(str::to_owned) else {
            return out.push(ClassPart::Dynamic);
        };
        match self.eval(*v).known() {
            Some(c) if !truthy(c) => {}
            Some(_) => out.push(ClassPart::Text(key)),
            None => out.push(ClassPart::Maybe(vec![ClassPart::Text(key)])),
        }
    }
}

/// One contribution to a joined class string.
#[derive(Debug, Clone, PartialEq, Eq)]
enum ClassPart {
    /// Certain text (may hold several tokens).
    Text(String),
    /// Text that is there only in some outcomes.
    Maybe(Vec<ClassPart>),
    /// One of these texts (an empty one stands for "nothing").
    OneOf(Vec<String>),
    /// Unknown text.
    Dynamic,
    /// Partly known text.
    Fragments(Vec<Fragment>),
}

impl ClassPart {
    fn from_value(v: &ConstValue) -> Self {
        match v {
            ConstValue::Known(v) => Self::OneOf(class_texts(std::slice::from_ref(v))).simplify(),
            ConstValue::OneOf(vs) => Self::OneOf(class_texts(vs)).simplify(),
            ConstValue::Fragments(f) => Self::Fragments(f.clone()),
            ConstValue::Unknown => Self::Dynamic,
        }
    }

    /// A one-alternative `OneOf` is certain text.
    fn simplify(self) -> Self {
        match self {
            Self::OneOf(mut v) if v.len() == 1 => Self::Text(v.remove(0)),
            other => other,
        }
    }
}

/// The class text each value contributes (falsy values contribute the empty text; arrays join their items).
fn class_texts(values: &[Value]) -> Vec<String> {
    let mut out: BTreeSet<String> = BTreeSet::new();
    for v in values {
        out.insert(match v {
            Value::Str(s) => s.trim().to_owned(),
            Value::Int(i) if *i != 0 => i.to_string(),
            Value::Array(items) => items
                .iter()
                .flat_map(|i| class_texts(std::slice::from_ref(i)))
                .filter(|t| !t.is_empty())
                .collect::<Vec<_>>()
                .join(" "),
            Value::Object(map) => map
                .iter()
                .filter(|(_, c)| truthy(c))
                .map(|(k, _)| k.as_str())
                .collect::<Vec<_>>()
                .join(" "),
            Value::Bool(_) | Value::Null | Value::Int(_) => String::new(),
        });
    }
    out.into_iter().collect()
}

/// Joins the parts with single spaces: exact alternatives while they stay within [`MAX_ONE_OF`], else fragments.
fn join_classes(parts: &[ClassPart]) -> ConstValue {
    let mut alts: Vec<String> = vec![String::new()];
    for part in parts {
        let Some(options) = part_options(part) else {
            return fragment_classes(parts);
        };
        let mut next: BTreeSet<String> = BTreeSet::new();
        for a in &alts {
            for o in &options {
                next.insert(join_text(a, o));
            }
        }
        if next.len() > MAX_ONE_OF {
            return fragment_classes(parts);
        }
        alts = next.into_iter().collect();
    }
    ConstValue::one_of(alts.into_iter().map(Value::Str).collect())
}

/// Space-joins two class texts, dropping an empty side.
fn join_text(a: &str, b: &str) -> String {
    match (a.is_empty(), b.is_empty()) {
        (true, _) => b.to_owned(),
        (_, true) => a.to_owned(),
        _ => format!("{a} {b}"),
    }
}

/// The exact alternatives a part contributes, or `None` when it is not exactly known.
fn part_options(part: &ClassPart) -> Option<Vec<String>> {
    match part {
        ClassPart::Text(t) => Some(vec![t.clone()]),
        ClassPart::OneOf(v) => Some(v.clone()),
        ClassPart::Maybe(inner) => {
            let mut acc: Vec<String> = vec![String::new()];
            for p in inner {
                let opts = part_options(p)?;
                acc = acc
                    .iter()
                    .flat_map(|a| opts.iter().map(move |o| join_text(a, o)))
                    .collect::<BTreeSet<_>>()
                    .into_iter()
                    .collect();
            }
            if !acc.iter().any(String::is_empty) {
                acc.push(String::new());
            }
            Some(acc)
        }
        ClassPart::Dynamic | ClassPart::Fragments(_) => None,
    }
}

/// The joined classes as known text around unknown parts (no exact alternatives are claimed).
fn fragment_classes(parts: &[ClassPart]) -> ConstValue {
    let mut frags: Vec<Fragment> = Vec::new();
    let push = |f: Fragment, frags: &mut Vec<Fragment>| match (frags.last_mut(), f) {
        (Some(Fragment::Known(a)), Fragment::Known(b)) => a.push_str(&b),
        (Some(Fragment::Unknown), Fragment::Unknown) => {}
        (_, f) => frags.push(f),
    };
    for part in parts {
        let pieces: Vec<Fragment> = match part {
            ClassPart::Text(t) => vec![Fragment::Known(t.clone())],
            ClassPart::Fragments(f) => f.clone(),
            ClassPart::OneOf(_) | ClassPart::Maybe(_) | ClassPart::Dynamic => {
                vec![Fragment::Unknown]
            }
        };
        let empty = matches!(pieces.as_slice(), [Fragment::Known(t)] if t.is_empty());
        if empty {
            continue;
        }
        if !frags.is_empty() {
            push(Fragment::Known(" ".to_owned()), &mut frags);
        }
        for p in pieces {
            push(p, &mut frags);
        }
    }
    match frags.as_slice() {
        [] => ConstValue::Known(Value::Str(String::new())),
        [Fragment::Known(s)] => ConstValue::Known(Value::Str(s.clone())),
        [Fragment::Unknown] => ConstValue::Unknown,
        _ => ConstValue::Fragments(frags),
    }
}

/// The text of a scalar value inside a concatenation.
fn scalar_text(v: &Value) -> Option<String> {
    match v {
        Value::Str(s) => Some(s.clone()),
        Value::Int(i) => Some(i.to_string()),
        Value::Bool(b) => Some(b.to_string()),
        Value::Null | Value::Array(_) | Value::Object(_) => None,
    }
}

/// The concatenation of parts that each have a few alternatives (a conditional in a template literal):
/// every combination, or `None` when a part is not exactly known, an addition has no string operand
/// (it is a sum), or the combinations pass [`MAX_ONE_OF`].
fn text_product(parts: &[ConstValue], add: bool) -> Option<ConstValue> {
    let mut options: Vec<Vec<Value>> = Vec::with_capacity(parts.len());
    for p in parts {
        options.push(p.alternatives()?);
    }
    if add && !options.iter().flatten().any(|v| matches!(v, Value::Str(_))) {
        return None;
    }
    let mut acc: BTreeSet<String> = BTreeSet::from([String::new()]);
    for alts in &options {
        let texts: Vec<String> = alts.iter().map(scalar_text).collect::<Option<_>>()?;
        acc = acc
            .iter()
            .flat_map(|a| texts.iter().map(move |t| format!("{a}{t}")))
            .collect();
        if acc.len() > MAX_ONE_OF {
            return None;
        }
    }
    Some(ConstValue::one_of(
        acc.into_iter().map(Value::Str).collect(),
    ))
}

/// JavaScript truthiness of a known value.
fn truthy(v: &Value) -> bool {
    match v {
        Value::Bool(b) => *b,
        Value::Int(i) => *i != 0,
        Value::Str(s) => !s.is_empty(),
        Value::Null => false,
        Value::Array(_) | Value::Object(_) => true,
    }
}

/// The argument of a spread form `apply(op spread)`.
fn spread_arg(model: &Model, node: NodeId) -> Option<NodeId> {
    match op_form(model, node)? {
        (op, args) if op == OP_SPREAD => args.first().copied(),
        _ => None,
    }
}

/// The value expression of a `unit(kind = const)`: its first non-attachment child, or when that is a body
/// `group` (after the `sig` facet group of an adapter that lowers declarations) the first child inside it.
pub fn const_value_node(model: &Model, unit: NodeId) -> Option<NodeId> {
    let term = model.term();
    let n = term.node(unit);
    if !matches!(&n.op, Operator::Universal(Universal::Unit { kind, .. }) if kind == CONST_KIND) {
        return None;
    }
    let first = n.children.iter().copied().find(|&c| {
        let child = term.node(c);
        !child.op.is_attachment() && child.attrs.get_str(reserved::FACET) != Some("sig")
    })?;
    let inner = term.node(first);
    if matches!(inner.op, Operator::Universal(Universal::Group { .. })) {
        return inner
            .children
            .iter()
            .copied()
            .find(|&c| !term.node(c).op.is_attachment());
    }
    Some(first)
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
