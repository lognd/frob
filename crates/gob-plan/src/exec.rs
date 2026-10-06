//! A small executor for GRL rules over the web-engine catalog kinds: compile a
//! parsed rule against [`crate::catalog`], run it on a [`gob_ir::Model`]
//! (grl-spec.md sections 6 and 7.2, language-engines.md section 5).
//!
//! Supported shape: one `find v: KIND(.field = literal, ...)` over `element` or
//! `attribute`, `where` clauses built from `not`, `and`, `or`, `v.field ==
//! literal`, `v has attribute(.field = literal, ...)` and boolean fields, and a
//! `report v "message"`. Everything else is a [`CompileError`], never silently
//! ignored. Evaluation is Kleene: a dynamic value or a spread makes a test
//! `Unknown`, and an `Unknown` result lands in [`Outcome::unresolved`], not in
//! [`Outcome::fired`].

use gob_ir::const_value::{ConstValue, Value};
use gob_ir::markup::{self, Attribute, Element, TagKind};
use gob_ir::{Model, NodeId, Truth};
use gob_text::Span;
use tracing::{debug, trace};

use crate::catalog::{self, Kind};
use crate::grl::ast::{
    ClauseKind, CmpOp, Cond, CondKind, Containment, FieldEq, LiteralKind, Object, Rel, RelKind,
    Rule, ShapeKind, Source, Term, TermKind,
};

/// Why a rule cannot be compiled or is outside the supported shape.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum CompileError {
    /// GRL001: a kind word is not in the catalog.
    #[error("GRL001: unknown kind `{word}`")]
    UnknownKind {
        /// The word as written.
        word: String,
        /// Where it was written.
        span: Span,
    },
    /// GRL001: a field is not a field of the kind.
    #[error("GRL001: `{kind}` has no field `{field}`")]
    UnknownField {
        /// The kind.
        kind: &'static str,
        /// The field as written.
        field: String,
        /// Where it was written.
        span: Span,
    },
    /// A construct this executor does not run yet.
    #[error("unsupported construct: {what}")]
    Unsupported {
        /// What was met.
        what: &'static str,
        /// Where.
        span: Span,
    },
    /// The rule has no `find` or no `report`.
    #[error("rule has no {0}")]
    Missing(&'static str),
}

#[derive(Debug, Clone, PartialEq)]
enum Lit {
    Str(String),
    Bool(bool),
}

#[derive(Debug, Clone, PartialEq)]
struct Shape {
    kind: &'static Kind,
    fields: Vec<(String, Lit)>,
}

#[derive(Debug, Clone, PartialEq)]
enum Pred {
    Not(Box<Pred>),
    And(Vec<Pred>),
    Or(Vec<Pred>),
    Eq(String, Lit, bool),
    Flag(String),
    HasAttribute(Shape),
}

/// A compiled rule.
#[derive(Debug, Clone, PartialEq)]
pub struct Program {
    rule: String,
    subject: Shape,
    var: String,
    conds: Vec<Pred>,
    message: String,
}

/// The result of running a [`Program`] on one model.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Outcome {
    /// Subjects where the rule certainly fires.
    pub fired: Vec<NodeId>,
    /// Subjects where the rule might fire: a dynamic value or spread decides.
    pub unresolved: Vec<NodeId>,
    /// The rule's message.
    pub message: String,
}

fn lit_of(t: &Term) -> Result<Lit, CompileError> {
    match &t.node {
        TermKind::Literal(l) => match &l.node {
            LiteralKind::Str(s) => Ok(Lit::Str(s.clone())),
            LiteralKind::Bool(b) => Ok(Lit::Bool(*b)),
            _ => Err(CompileError::Unsupported {
                what: "non string or bool literal",
                span: t.span,
            }),
        },
        _ => Err(CompileError::Unsupported {
            what: "non literal term",
            span: t.span,
        }),
    }
}

fn field_name(w: &str) -> &str {
    w.strip_prefix('.').unwrap_or(w)
}

fn check_field(kind: &'static Kind, name: &str, span: Span) -> Result<(), CompileError> {
    if kind.field(name).is_some() {
        Ok(())
    } else {
        Err(CompileError::UnknownField {
            kind: kind.word,
            field: name.to_owned(),
            span,
        })
    }
}

fn shape_of(word: &str, fields: &[FieldEq], wspan: Span) -> Result<Shape, CompileError> {
    let kind = catalog::kind(word).ok_or_else(|| CompileError::UnknownKind {
        word: word.to_owned(),
        span: wspan,
    })?;
    let mut out = Vec::new();
    for f in fields {
        let name = field_name(&f.name.text);
        check_field(kind, name, f.name.span)?;
        let value = match &f.value.node {
            LiteralKind::Str(s) => Lit::Str(s.clone()),
            LiteralKind::Bool(b) => Lit::Bool(*b),
            _ => {
                return Err(CompileError::Unsupported {
                    what: "non string or bool field value",
                    span: f.value.span,
                });
            }
        };
        out.push((name.to_owned(), value));
    }
    Ok(Shape { kind, fields: out })
}

fn shape_source(source: &Source) -> Result<Shape, CompileError> {
    let Source::Shape(s) = source else {
        return Err(CompileError::Unsupported {
            what: "side relation source",
            span: source.span(),
        });
    };
    match &s.node {
        ShapeKind::Kind {
            kind,
            fields,
            arg: None,
        } => shape_of(&kind.text, fields, kind.span),
        _ => Err(CompileError::Unsupported {
            what: "snippet, alternatives or kind argument",
            span: s.span,
        }),
    }
}

fn path_field<'t>(var: &str, t: &'t Term) -> Result<&'t str, CompileError> {
    if let TermKind::Path(p) = &t.node
        && let [v, f] = p.segments.as_slice()
        && v.text == var
    {
        return Ok(field_name(&f.text));
    }
    Err(CompileError::Unsupported {
        what: "term other than `var.field`",
        span: t.span,
    })
}

fn pred(var: &str, subject: &'static Kind, c: &Cond) -> Result<Pred, CompileError> {
    match &c.node {
        CondKind::Not(inner) => Ok(Pred::Not(Box::new(pred(var, subject, inner)?))),
        CondKind::And(cs) => Ok(Pred::And(
            cs.iter()
                .map(|c| pred(var, subject, c))
                .collect::<Result<_, _>>()?,
        )),
        CondKind::Or(cs) => Ok(Pred::Or(
            cs.iter()
                .map(|c| pred(var, subject, c))
                .collect::<Result<_, _>>()?,
        )),
        CondKind::Cmp {
            op: op @ (CmpOp::Eq | CmpOp::Ne),
            lhs,
            rhs,
        } => {
            let name = path_field(var, lhs)?;
            check_field(subject, name, lhs.span)?;
            Ok(Pred::Eq(name.to_owned(), lit_of(rhs)?, *op == CmpOp::Ne))
        }
        CondKind::Flag(t) => {
            let name = path_field(var, t)?;
            check_field(subject, name, t.span)?;
            Ok(Pred::Flag(name.to_owned()))
        }
        CondKind::Rel { subject: s, rel } => has_attribute(var, subject, s, rel),
        _ => Err(CompileError::Unsupported {
            what: "condition form",
            span: c.span,
        }),
    }
}

fn has_attribute(
    var: &str,
    subject: &'static Kind,
    s: &Term,
    rel: &Rel,
) -> Result<Pred, CompileError> {
    let unsupported = |what| CompileError::Unsupported {
        what,
        span: rel.span,
    };
    if !matches!(&s.node, TermKind::Path(p) if p.segments.len() == 1 && p.segments[0].text == var) {
        return Err(unsupported("relation subject other than the variable"));
    }
    let RelKind::Containment {
        directly: _,
        dir: Containment::Has,
        object: Object::Shape(sh),
    } = &rel.node
    else {
        return Err(unsupported("relation other than `has`"));
    };
    let ShapeKind::Kind {
        kind,
        fields,
        arg: None,
    } = &sh.node
    else {
        return Err(unsupported("object other than a kind shape"));
    };
    let shape = shape_of(&kind.text, fields, kind.span)?;
    if subject.word != "element" || shape.kind.word != "attribute" {
        return Err(unsupported("`has` other than element has attribute"));
    }
    Ok(Pred::HasAttribute(shape))
}

/// Compile one rule against the catalog.
///
/// # Errors
/// [`CompileError`] naming the first unknown word (GRL001) or unsupported construct.
pub fn compile(rule: &Rule) -> Result<Program, CompileError> {
    let mut subject = None;
    let mut conds = Vec::new();
    let mut message = None;
    for clause in &rule.clauses {
        match &clause.node {
            ClauseKind::Find(b) if subject.is_none() => {
                if !b.rels.is_empty() {
                    return Err(CompileError::Unsupported {
                        what: "relations on find",
                        span: b.span,
                    });
                }
                let shape = shape_source(&b.source)?;
                if !matches!(shape.kind.word, "element" | "attribute") {
                    return Err(CompileError::Unsupported {
                        what: "subject kind other than element or attribute",
                        span: b.span,
                    });
                }
                if let Some(f) = &b.filter {
                    conds.push(pred(&b.name.text, shape.kind, f)?);
                }
                subject = Some((b.name.text.clone(), shape));
            }
            ClauseKind::Where(c) => {
                let (var, shape) = subject.as_ref().ok_or(CompileError::Missing("find"))?;
                conds.push(pred(var, shape.kind, c)?);
            }
            ClauseKind::Report(r) if r.when.is_none() => {
                message = Some(
                    r.message
                        .parts
                        .iter()
                        .map(|p| match p {
                            crate::grl::ast::MessagePart::Text { value, .. } => value.as_str(),
                            crate::grl::ast::MessagePart::Interp { .. } => "",
                        })
                        .collect::<String>(),
                );
            }
            _ => {
                return Err(CompileError::Unsupported {
                    what: "clause form",
                    span: clause.span,
                });
            }
        }
    }
    let (var, subject) = subject.ok_or(CompileError::Missing("find"))?;
    let message = message.ok_or(CompileError::Missing("report"))?;
    debug!(rule = %rule.id.text, kind = subject.kind.word, conds = conds.len(), "rule compiled");
    Ok(Program {
        rule: rule.id.text.clone(),
        subject,
        var,
        conds,
        message,
    })
}

/// The value of a field of the subject being tested.
enum Val {
    Str(String),
    Bool(bool),
    Const(ConstValue),
    Unknown,
}

enum Subject<'a> {
    Element(&'a Element),
    Attribute(&'a Attribute),
}

fn field_of(model: &Model, s: &Subject<'_>, name: &str) -> Val {
    match (s, name) {
        (Subject::Element(e), "tag") => e.tag.clone().map_or(Val::Unknown, Val::Str),
        (Subject::Element(e), "kind") => Val::Str(
            match e.kind {
                TagKind::Intrinsic => "intrinsic",
                TagKind::Component => "component",
                TagKind::Unknown => "unknown",
            }
            .to_owned(),
        ),
        (Subject::Attribute(a), "name") => a.name.clone().map_or(Val::Unknown, Val::Str),
        (Subject::Attribute(a), "spread") => Val::Bool(a.is_spread()),
        (Subject::Attribute(a), "value") => Val::Const(markup::attribute_value(model, a)),
        _ => Val::Unknown,
    }
}

fn eq(v: &Val, lit: &Lit) -> Truth {
    let want = match lit {
        Lit::Str(s) => Value::Str(s.clone()),
        Lit::Bool(b) => Value::Bool(*b),
    };
    match v {
        Val::Str(a) => Truth::from_bool(Value::Str(a.clone()) == want),
        Val::Bool(a) => Truth::from_bool(Value::Bool(*a) == want),
        Val::Const(ConstValue::Known(k)) => Truth::from_bool(*k == want),
        Val::Const(ConstValue::OneOf(vs)) if vs.contains(&want) => Truth::Unknown,
        Val::Const(ConstValue::OneOf(_)) => Truth::No,
        Val::Const(_) | Val::Unknown => Truth::Unknown,
    }
}

fn holds(model: &Model, p: &Pred, s: &Subject<'_>) -> Truth {
    match p {
        Pred::Not(i) => !holds(model, i, s),
        Pred::And(ps) => Truth::all(ps.iter().map(|p| holds(model, p, s))),
        Pred::Or(ps) => Truth::any(ps.iter().map(|p| holds(model, p, s))),
        Pred::Eq(f, lit, negate) => {
            let t = eq(&field_of(model, s, f), lit);
            if *negate { !t } else { t }
        }
        Pred::Flag(f) => eq(&field_of(model, s, f), &Lit::Bool(true)),
        Pred::HasAttribute(shape) => {
            let Subject::Element(e) = s else {
                return Truth::Unknown;
            };
            let found = Truth::any(e.attributes.iter().filter(|a| !a.is_spread()).map(|a| {
                Truth::all(
                    shape
                        .fields
                        .iter()
                        .map(|(f, l)| eq(&field_of(model, &Subject::Attribute(a), f), l)),
                )
            }));
            // A spread may supply an attribute no listed one matches.
            if found == Truth::No && e.has_spread() {
                Truth::Unknown
            } else {
                found
            }
        }
    }
}

impl Program {
    /// The rule id.
    pub fn rule(&self) -> &str {
        &self.rule
    }

    /// The variable the rule binds.
    pub fn var(&self) -> &str {
        &self.var
    }

    /// Run on `model`: every subject where all `where` clauses hold fires, those
    /// that are `Unknown` are unresolved.
    pub fn run(&self, model: &Model) -> Outcome {
        let mut out = Outcome {
            message: self.message.clone(),
            ..Outcome::default()
        };
        for el in markup::elements(model) {
            let subjects: Vec<(NodeId, Subject<'_>)> = if self.subject.kind.word == "element" {
                vec![(el.node, Subject::Element(&el))]
            } else {
                el.attributes
                    .iter()
                    .map(|a| (a.node, Subject::Attribute(a)))
                    .collect()
            };
            for (node, s) in subjects {
                let shape = Truth::all(
                    self.subject
                        .fields
                        .iter()
                        .map(|(f, l)| eq(&field_of(model, &s, f), l)),
                );
                let t = shape & Truth::all(self.conds.iter().map(|p| holds(model, p, &s)));
                trace!(rule = %self.rule, %node, truth = %t, "subject tested");
                match t {
                    Truth::Yes => out.fired.push(node),
                    Truth::Unknown => out.unresolved.push(node),
                    Truth::No => {}
                }
            }
        }
        out
    }
}
