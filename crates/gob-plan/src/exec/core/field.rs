//! Field values and three-valued comparison (grl-spec.md sections 6 and 7.2).
//!
//! A field read answers a [`Datum`]: a known scalar, one of several candidates (a `const_value`
//! that may be either of two things), absent (the node has no such field) or unknown (a dynamic
//! value, a spread, a missing source). A comparison over data is Kleene: unknown data never
//! decides, a candidate set decides only when every candidate agrees.

use std::cmp::Ordering;

use gob_ir::const_value::{ConstValue, Value};
use gob_ir::markup;
use gob_ir::style;
use gob_ir::{AttrValue, Model, NodeId, Operator, Truth, Universal};
use gob_text::SourceText;

use crate::plan::CmpOp;

/// A known scalar.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum Scalar {
    /// Text.
    Str(String),
    /// A whole number.
    Int(i64),
    /// A boolean.
    Bool(bool),
}

/// What a field read or a literal operand yields.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Datum {
    /// Exactly this value.
    Known(Scalar),
    /// One of these values; the executor cannot tell which.
    OneOf(Vec<Scalar>),
    /// A node itself (compared by identity).
    Node(NodeId),
    /// The node has no such field.
    Absent,
    /// The value exists but cannot be read statically.
    Unknown,
}

impl Datum {
    pub(crate) fn text(s: impl Into<String>) -> Self {
        Self::Known(Scalar::Str(s.into()))
    }

    pub(crate) fn int(i: impl TryInto<i64>) -> Self {
        i.try_into()
            .map_or(Self::Unknown, |i| Self::Known(Scalar::Int(i)))
    }
}

fn scalar_of(v: &Value) -> Option<Scalar> {
    match v {
        Value::Str(s) => Some(Scalar::Str(s.clone())),
        Value::Int(i) => Some(Scalar::Int(*i)),
        Value::Bool(b) => Some(Scalar::Bool(*b)),
        Value::Null | Value::Array(_) | Value::Object(_) => None,
    }
}

/// A `const_value` as a datum: a structured value is not a scalar, so it is unknown.
pub(crate) fn datum_of_const(c: &ConstValue) -> Datum {
    match c {
        ConstValue::Known(v) => scalar_of(v).map_or(Datum::Unknown, Datum::Known),
        ConstValue::OneOf(vs) => {
            let all: Option<Vec<Scalar>> = vs.iter().map(scalar_of).collect();
            all.map_or(Datum::Unknown, Datum::OneOf)
        }
        ConstValue::Fragments(_) | ConstValue::Unknown => Datum::Unknown,
    }
}

fn order_holds(op: CmpOp, ord: Ordering) -> bool {
    match op {
        CmpOp::Eq => ord == Ordering::Equal,
        CmpOp::Ne => ord != Ordering::Equal,
        CmpOp::Lt => ord == Ordering::Less,
        CmpOp::Le => ord != Ordering::Greater,
        CmpOp::Gt => ord == Ordering::Greater,
        CmpOp::Ge => ord != Ordering::Less,
    }
}

/// One scalar against one scalar; mismatched types are equal never, and unordered.
fn scalar_cmp(op: CmpOp, a: &Scalar, b: &Scalar) -> Truth {
    match (a, b) {
        (Scalar::Str(x), Scalar::Str(y)) => Truth::from_bool(order_holds(op, x.cmp(y))),
        (Scalar::Int(x), Scalar::Int(y)) => Truth::from_bool(order_holds(op, x.cmp(y))),
        (Scalar::Bool(x), Scalar::Bool(y)) => Truth::from_bool(order_holds(op, x.cmp(y))),
        _ => match op {
            CmpOp::Eq => Truth::No,
            CmpOp::Ne => Truth::Yes,
            CmpOp::Lt | CmpOp::Le | CmpOp::Gt | CmpOp::Ge => Truth::Unknown,
        },
    }
}

/// Kleene comparison `lhs op rhs`.
///
/// A candidate set is `Yes` only when every candidate satisfies the comparison, `No` only when
/// none does. An absent side satisfies only `!=` (there is nothing to equal).
pub fn compare(op: CmpOp, lhs: &Datum, rhs: &Datum) -> Truth {
    use Datum::{Absent, Known, Node, OneOf, Unknown};
    match (lhs, rhs) {
        (Unknown, _) | (_, Unknown) => Truth::Unknown,
        (Absent, Absent) => Truth::from_bool(matches!(op, CmpOp::Eq | CmpOp::Le | CmpOp::Ge)),
        (Node(a), Node(b)) => match op {
            CmpOp::Eq => Truth::from_bool(a == b),
            CmpOp::Ne => Truth::from_bool(a != b),
            _ => Truth::Unknown,
        },
        // An absent field, or a node against a scalar, equals nothing.
        (Absent | Node(_), _) | (_, Absent | Node(_)) => Truth::from_bool(op == CmpOp::Ne),
        (Known(a), Known(b)) => scalar_cmp(op, a, b),
        (OneOf(vs), Known(b)) => fold_candidates(vs.iter().map(|a| scalar_cmp(op, a, b))),
        (Known(a), OneOf(vs)) => fold_candidates(vs.iter().map(|b| scalar_cmp(op, a, b))),
        (OneOf(xs), OneOf(ys)) => fold_candidates(
            xs.iter()
                .flat_map(|a| ys.iter().map(move |b| scalar_cmp(op, a, b))),
        ),
    }
}

/// `Yes` when every candidate is `Yes`, `No` when every one is `No`, else `Unknown`.
fn fold_candidates(items: impl Iterator<Item = Truth>) -> Truth {
    let (mut yes, mut no) = (false, false);
    for t in items {
        match t {
            Truth::Yes => yes = true,
            Truth::No => no = true,
            Truth::Unknown => return Truth::Unknown,
        }
    }
    match (yes, no) {
        (true, false) => Truth::Yes,
        (false, true) => Truth::No,
        _ => Truth::Unknown,
    }
}

/// Where field reads get their information: the model and, when supplied, the file's text.
#[derive(Clone, Copy)]
pub(crate) struct Reader<'a> {
    pub(crate) model: &'a Model,
    pub(crate) source: Option<&'a SourceText>,
}

impl Reader<'_> {
    /// The 1-based line of `node`'s start, when the text is known.
    pub(crate) fn line_of(&self, node: NodeId) -> Option<u32> {
        let range = match self.model.term().node(node).location() {
            gob_ir::Location::Text { range, .. } => *range,
            _ => return None,
        };
        let lc = self.source?.line_col(range.start())?;
        Some(lc.line)
    }

    /// The text of `node` as written, when the text is known.
    fn slice(&self, node: NodeId) -> Option<&str> {
        let range = match self.model.term().node(node).location() {
            gob_ir::Location::Text { range, .. } => *range,
            _ => return None,
        };
        self.source?.slice(range)
    }

    /// Reads the field `name` of `node`.
    ///
    /// Dotted names read through a node-valued field: `callee.name`, `file.path`.
    pub(crate) fn field(&self, node: NodeId, name: &str) -> Datum {
        if let Some((head, rest)) = name.split_once('.') {
            return self.dotted(node, head, rest);
        }
        match name {
            "path" => Datum::text(self.model.term().locator()),
            "line" => self.line_of(node).map_or(Datum::Unknown, Datum::int),
            "kind" => self.kind(node),
            "role" => match self.model.term().node(node).op() {
                Operator::Universal(Universal::Unit { role, .. }) => Datum::text(role.clone()),
                _ => Datum::Absent,
            },
            "name" => self.name(node),
            "text" => self.text(node),
            "public" | "exported" => self.visibility(node),
            "tag" | "spread" | "value" => self.markup(node, name),
            "selector" | "property" | "important" | "raw" => self.style(node, name),
            "callee" => self.callee(node).map_or(Datum::Absent, Datum::text),
            _ => Datum::Unknown,
        }
    }

    fn dotted(&self, node: NodeId, head: &str, rest: &str) -> Datum {
        match (head, rest) {
            ("callee", "name") => self.callee(node).map_or(Datum::Absent, |c| {
                Datum::text(c.rsplit(['.', ':']).next().unwrap_or(&c))
            }),
            ("file", "path") => self.field(node, "path"),
            _ => Datum::Unknown,
        }
    }

    fn kind(&self, node: NodeId) -> Datum {
        if let Some(e) = markup::element(self.model, node) {
            return Datum::text(match e.kind {
                markup::TagKind::Intrinsic => "intrinsic",
                markup::TagKind::Component => "component",
                markup::TagKind::Unknown => "unknown",
            });
        }
        match self.model.term().node(node).op() {
            Operator::Universal(
                Universal::Unit { kind, .. }
                | Universal::Anon { kind }
                | Universal::Apply { kind }
                | Universal::Bind { kind, .. }
                | Universal::Lit { kind, .. }
                | Universal::Region { kind }
                | Universal::Phase { kind }
                | Universal::Hole { kind },
            ) => Datum::text(kind.clone()),
            Operator::Universal(u) => Datum::text(u.tag()),
            Operator::Adapter(a) => Datum::text(a.name.clone()),
        }
    }

    fn name(&self, node: NodeId) -> Datum {
        let n = self.model.term().node(node);
        if matches!(n.op(), Operator::Adapter(a) if a.lang == markup::LANG && a.name == "spread") {
            return Datum::Unknown;
        }
        match (n.name(), n.op()) {
            (Some(s), _) => Datum::text(s),
            (None, Operator::Universal(Universal::Ref { name })) => Datum::text(name.clone()),
            (None, _) => Datum::Absent,
        }
    }

    fn text(&self, node: NodeId) -> Datum {
        match self.model.term().node(node).op() {
            Operator::Universal(Universal::Lit { lexeme, .. }) => Datum::text(lexeme.clone()),
            Operator::Universal(Universal::Comment { text }) => Datum::text(text.clone()),
            Operator::Universal(Universal::Ref { name }) => Datum::text(name.clone()),
            _ => self.slice(node).map_or(Datum::Unknown, Datum::text),
        }
    }

    /// `public` and `exported` read the `visibility` attribute; an adapter that does not provide
    /// attributes completely (`ir.attrs_provided = false`) cannot say "not public".
    fn visibility(&self, node: NodeId) -> Datum {
        let term = self.model.term();
        match term.node(node).attrs().get_str("visibility") {
            Some(v) => Datum::Known(Scalar::Bool(v == "public")),
            None => match term
                .node(term.root())
                .attrs()
                .get(gob_ir::reserved::ATTRS_PROVIDED)
            {
                Some(AttrValue::Bool(false)) => Datum::Unknown,
                _ => Datum::Known(Scalar::Bool(false)),
            },
        }
    }

    fn markup(&self, node: NodeId, field: &str) -> Datum {
        if let Some(e) = markup::element(self.model, node) {
            return match field {
                "tag" => e.tag.map_or(Datum::Unknown, Datum::text),
                _ => Datum::Absent,
            };
        }
        let term = self.model.term();
        let is_spread = match term.node(node).op() {
            Operator::Adapter(a) if a.lang == markup::LANG && a.name == "attribute" => false,
            Operator::Adapter(a) if a.lang == markup::LANG && a.name == "spread" => true,
            _ => return Datum::Absent,
        };
        match field {
            "spread" => Datum::Known(Scalar::Bool(is_spread)),
            "value" => {
                let attr = markup::Attribute {
                    node,
                    name: term.node(node).name().map(str::to_owned),
                    value: term.node(node).children().first().copied(),
                    status: if is_spread {
                        gob_ir::Status::May
                    } else {
                        gob_ir::Status::Must
                    },
                };
                datum_of_const(&markup::attribute_value(self.model, &attr))
            }
            _ => Datum::Absent,
        }
    }

    fn style(&self, node: NodeId, field: &str) -> Datum {
        let n = self.model.term().node(node);
        match (field, n.op()) {
            ("selector", Operator::Universal(Universal::Unit { kind, .. }))
                if kind == style::STYLE_RULE =>
            {
                n.name().map_or(Datum::Unknown, Datum::text)
            }
            ("property", Operator::Adapter(a)) if a.lang == style::LANG => {
                n.name().map_or(Datum::Unknown, Datum::text)
            }
            ("important", Operator::Adapter(a)) if a.lang == style::LANG => {
                Datum::Known(Scalar::Bool(matches!(
                    n.attrs().get(style::IMPORTANT),
                    Some(AttrValue::Bool(true))
                )))
            }
            ("raw", _) => n
                .attrs()
                .get_str(style::RAW)
                .map_or(Datum::Absent, Datum::text),
            _ => Datum::Absent,
        }
    }

    /// The callee of a call as written: the spelled name of the head `ref`.
    fn callee(&self, node: NodeId) -> Option<String> {
        let term = self.model.term();
        let n = term.node(node);
        if !matches!(n.op(), Operator::Universal(Universal::Apply { kind }) if kind == "call") {
            return None;
        }
        let head = *n.children().first()?;
        match term.node(head).op() {
            Operator::Universal(Universal::Ref { name }) => Some(name.clone()),
            _ => None,
        }
    }
}
