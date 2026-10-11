//! Syntax tree to a name-based tree: the checked clauses with no numbering decided yet.

// frob:ticket 01M3ZX7EKNE5Q0NB0DKCH77AZX
use gob_text::Span;

use super::LowerError;
use crate::grl::ast::{
    self, Binding, Clause, ClauseKind, CondKind, Header, HeaderKind, LangSet, LiteralKind,
    MessagePart, Object, RelKind, Rule, ShapeKind, Source, Term, TermKind,
};
use crate::plan::{Certainty, CmpOp, Need, Polarity, Position, Quant};

/// A value a condition compares, by name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Opd {
    Var(String),
    Field(String, String),
    Int(i64),
    Str(String),
    Bool(bool),
}

/// A condition by variable name. Its `Debug` text is the planner's sort key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Cond {
    And(Vec<Cond>),
    Or(Vec<Cond>),
    Not(Box<Cond>),
    Quant {
        quant: Quant,
        var: String,
        kind: String,
        cond: Box<Cond>,
    },
    Inside {
        sub: String,
        sup: String,
        direct: bool,
    },
    Order {
        a: String,
        b: String,
        pos: Position,
    },
    Verb {
        subject: String,
        object: String,
        verb: String,
        certainty: Certainty,
    },
    Cmp {
        lhs: Opd,
        op: CmpOp,
        rhs: Opd,
    },
    Regex {
        subject: Opd,
        pattern: String,
    },
    Glob {
        subject: Opd,
        pattern: String,
    },
}

/// What a `find` ranges over.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub(super) enum Src {
    Kind(String),
    Side(Need, String),
}

/// A binder with the conditions written on it (field equalities, relations, `where`).
pub(super) struct FindItem {
    pub name: String,
    pub src: Src,
    pub attached: Vec<Cond>,
}

pub(super) struct ReportItem {
    pub subject: String,
    pub message: String,
    pub when: Option<Cond>,
}

/// Which languages, by name.
pub(super) enum LangNames {
    Any,
    Nothing,
    Only(Vec<String>),
}

/// One rule in name form.
pub(super) struct Lowered {
    pub id: String,
    pub langs: LangNames,
    pub polarity: Polarity,
    pub needs: Vec<Need>,
    pub repo_scope: bool,
    pub finds: Vec<FindItem>,
    pub wheres: Vec<Cond>,
    pub unresolved: Vec<(Cond, String)>,
    pub reports: Vec<ReportItem>,
}

struct Cx {
    scope: Vec<String>,
    fresh: u32,
}

fn unsupported<T>(what: &'static str, span: Span) -> Result<T, LowerError> {
    Err(LowerError::Unsupported { what, span })
}

pub(super) fn convert(rule: &Rule) -> Result<Lowered, LowerError> {
    let mut out = Lowered {
        id: rule.id.text.clone(),
        langs: LangNames::Any,
        polarity: Polarity::Pplus,
        needs: Vec::new(),
        repo_scope: false,
        finds: Vec::new(),
        wheres: Vec::new(),
        unresolved: Vec::new(),
        reports: Vec::new(),
    };
    for h in &rule.headers {
        header(&mut out, h)?;
    }
    let mut cx = Cx {
        scope: Vec::new(),
        fresh: 0,
    };
    for c in &rule.clauses {
        if let ClauseKind::Find(b) = &c.node {
            if cx.scope.contains(&b.name.text) {
                return Err(LowerError::Duplicate {
                    name: b.name.text.clone(),
                    span: b.name.span,
                });
            }
            cx.scope.push(b.name.text.clone());
        }
    }
    for c in &rule.clauses {
        clause(&mut out, &mut cx, c)?;
    }
    Ok(out)
}

fn header(out: &mut Lowered, h: &Header) -> Result<(), LowerError> {
    match &h.node {
        HeaderKind::Lang(l) => {
            out.langs = match l {
                LangSet::Any { .. } => LangNames::Any,
                LangSet::Nothing => LangNames::Nothing,
                LangSet::One(w) => LangNames::Only(vec![w.text.clone()]),
                LangSet::List(ws) => LangNames::Only(ws.iter().map(|w| w.text.clone()).collect()),
            };
        }
        HeaderKind::Polarity(p) => out.polarity = *p,
        HeaderKind::Scope(s) => out.repo_scope = matches!(s, ast::Scope::Repo),
        HeaderKind::Needs(words) => {
            for w in words {
                out.needs.push(match w.text.as_str() {
                    "config" => Need::Config,
                    "diff" => Need::Diff,
                    "lease" => Need::Lease,
                    "model" => Need::Model,
                    other => {
                        return Err(LowerError::UnknownNeed {
                            name: other.to_owned(),
                            span: w.span,
                        });
                    }
                });
            }
        }
        HeaderKind::Knob(k) => return unsupported("a knob", k.name.span),
        HeaderKind::Severity(_) | HeaderKind::MustMeasure | HeaderKind::Rollup(_) => {}
    }
    Ok(())
}

fn clause(out: &mut Lowered, cx: &mut Cx, c: &Clause) -> Result<(), LowerError> {
    cx.fresh = 0;
    match &c.node {
        ClauseKind::Find(b) => {
            let (src, attached) = binding_parts(cx, b, true)?;
            out.finds.push(FindItem {
                name: b.name.text.clone(),
                src,
                attached,
            });
        }
        ClauseKind::Where(cond) => out.wheres.push(cond_of(cx, cond)?),
        ClauseKind::Quant { quant, binding } => out.wheres.push(quantifier(cx, *quant, binding)?),
        ClauseKind::Def(d) => return unsupported("a def", d.name.span),
        ClauseKind::Report(r) => {
            require_bound(cx, &r.target)?;
            out.reports.push(ReportItem {
                subject: r.target.text.clone(),
                message: message_text(&r.message),
                when: r.when.as_ref().map(|w| cond_of(cx, w)).transpose()?,
            });
        }
        ClauseKind::Unresolved(u) => {
            out.unresolved
                .push((cond_of(cx, &u.when)?, message_text(&u.because)));
        }
        ClauseKind::Note(_) | ClauseKind::Fix(_) => {}
    }
    Ok(())
}

fn require_bound(cx: &Cx, w: &ast::Word) -> Result<(), LowerError> {
    if cx.scope.contains(&w.text) {
        Ok(())
    } else {
        Err(LowerError::UnknownVar {
            name: w.text.clone(),
            span: w.span,
        })
    }
}

fn message_text(m: &ast::Message) -> String {
    m.parts
        .iter()
        .map(|p| match p {
            MessagePart::Text { value, .. } => value.clone(),
            MessagePart::Interp { path, .. } => {
                let names: Vec<&str> = path.segments.iter().map(|s| s.text.as_str()).collect();
                format!("{{{}}}", names.join("."))
            }
        })
        .collect()
}

/// The source of a binder and the conditions written on it: field equalities, relations, filter.
fn binding_parts(cx: &mut Cx, b: &Binding, top: bool) -> Result<(Src, Vec<Cond>), LowerError> {
    let name = b.name.text.clone();
    let mut attached = Vec::new();
    let src = match &b.source {
        Source::Shape(s) => match &s.node {
            ShapeKind::Kind { kind, fields, arg } => {
                if arg.is_some() {
                    return unsupported("a kind with a string argument", s.span);
                }
                for f in fields {
                    attached.push(Cond::Cmp {
                        lhs: Opd::Field(name.clone(), f.name.text.clone()),
                        op: CmpOp::Eq,
                        rhs: literal(&f.value)?,
                    });
                }
                Src::Kind(kind.text.clone())
            }
            ShapeKind::Snippet { .. } => return unsupported("a snippet", s.span),
            ShapeKind::Alt(_) => return unsupported("alternative shapes", s.span),
        },
        Source::Side(p) => {
            let need = match p.segments[0].text.as_str() {
                "config" => Need::Config,
                "diff" => Need::Diff,
                "lease" => Need::Lease,
                "model" => Need::Model,
                _ => return unsupported("an unknown side relation", p.span),
            };
            if !top {
                return unsupported("a side relation inside a quantifier", p.span);
            }
            let table: Vec<&str> = p.segments[1..].iter().map(|s| s.text.as_str()).collect();
            Src::Side(need, table.join("."))
        }
    };
    if !top {
        cx.scope.push(name.clone());
    }
    let rest: Result<Vec<Cond>, LowerError> = (|| {
        for r in &b.rels {
            attached.push(rel_cond(cx, &name, r)?);
        }
        if let Some(f) = &b.filter {
            attached.push(cond_of(cx, f)?);
        }
        Ok(attached)
    })();
    if !top {
        cx.scope.pop();
    }
    Ok((src, rest?))
}

fn quantifier(cx: &mut Cx, q: ast::Quant, b: &Binding) -> Result<Cond, LowerError> {
    let (src, mut conds) = binding_parts(cx, b, false)?;
    let Src::Kind(kind) = src else {
        return unsupported("a side relation inside a quantifier", b.span);
    };
    let cond = if conds.len() == 1 {
        conds.remove(0)
    } else {
        Cond::And(conds)
    };
    Ok(Cond::Quant {
        quant: match q {
            ast::Quant::Some => Quant::Some,
            ast::Quant::No => Quant::No,
        },
        var: b.name.text.clone(),
        kind,
        cond: Box::new(cond),
    })
}

fn cond_of(cx: &mut Cx, c: &ast::Cond) -> Result<Cond, LowerError> {
    Ok(match &c.node {
        CondKind::Or(v) | CondKind::Any(v) => {
            Cond::Or(v.iter().map(|x| cond_of(cx, x)).collect::<Result<_, _>>()?)
        }
        CondKind::And(v) => Cond::And(v.iter().map(|x| cond_of(cx, x)).collect::<Result<_, _>>()?),
        CondKind::Not(x) => Cond::Not(Box::new(cond_of(cx, x)?)),
        CondKind::Quant { quant, binding } => quantifier(cx, *quant, binding)?,
        CondKind::Rel { subject, rel } => {
            let Some(name) = var_name(cx, subject)? else {
                return unsupported("a relation on a non-variable", subject.span);
            };
            rel_cond(cx, &name, rel)?
        }
        CondKind::Cmp { op, lhs, rhs } => Cond::Cmp {
            lhs: operand(cx, lhs)?,
            op: match op {
                ast::CmpOp::Eq => CmpOp::Eq,
                ast::CmpOp::Ne => CmpOp::Ne,
                ast::CmpOp::Lt => CmpOp::Lt,
                ast::CmpOp::Le => CmpOp::Le,
                ast::CmpOp::Gt => CmpOp::Gt,
                ast::CmpOp::Ge => CmpOp::Ge,
            },
            rhs: operand(cx, rhs)?,
        },
        CondKind::RegexMatch { lhs, rhs } => match &rhs.node {
            TermKind::Literal(l) => match &l.node {
                LiteralKind::Regex(r) => Cond::Regex {
                    subject: operand(cx, lhs)?,
                    pattern: regex_text(r),
                },
                _ => return unsupported("a non-regex pattern after ~", rhs.span),
            },
            _ => return unsupported("a non-literal pattern after ~", rhs.span),
        },
        CondKind::GlobMatch { lhs, rhs } => {
            let subject = operand(cx, lhs)?;
            let globs = glob_literals(rhs)?;
            let mut alts: Vec<Cond> = globs
                .into_iter()
                .map(|pattern| Cond::Glob {
                    subject: subject.clone(),
                    pattern,
                })
                .collect();
            if alts.len() == 1 {
                alts.remove(0)
            } else {
                Cond::Or(alts)
            }
        }
        CondKind::Flag(t) => match &t.node {
            TermKind::Path(p) if p.segments.len() == 2 => Cond::Cmp {
                lhs: operand(cx, t)?,
                op: CmpOp::Eq,
                rhs: Opd::Bool(true),
            },
            _ => return unsupported("a flag that is not a field", t.span),
        },
        CondKind::In { .. } => return unsupported("`in`", c.span),
        CondKind::Is { .. } | CondKind::IsSnippet { .. } => return unsupported("`is`", c.span),
        CondKind::HasAttr { .. } => return unsupported("`has attr`", c.span),
        CondKind::DefCall(_) => return unsupported("a def call", c.span),
        CondKind::Exists(_) => return unsupported("`exists`", c.span),
    })
}

fn regex_text(r: &crate::grl::Regex) -> String {
    let mut flags = String::new();
    if r.ignore_case {
        flags.push('i');
    }
    if r.multi_line {
        flags.push('m');
    }
    if flags.is_empty() {
        r.pattern.clone()
    } else {
        format!("(?{flags}){}", r.pattern)
    }
}

fn glob_literals(t: &Term) -> Result<Vec<String>, LowerError> {
    match &t.node {
        TermKind::Literal(l) => match &l.node {
            LiteralKind::Str(s) => Ok(vec![s.clone()]),
            LiteralKind::List(items) if !items.is_empty() => items
                .iter()
                .map(|i| match &i.node {
                    LiteralKind::Str(s) => Ok(s.clone()),
                    _ => unsupported("a non-string glob", i.span),
                })
                .collect(),
            _ => unsupported("a non-string glob", t.span),
        },
        _ => unsupported("a glob that is not a literal", t.span),
    }
}

/// The variable a term names, when it is a one-segment path of a variable in scope.
fn var_name(cx: &Cx, t: &Term) -> Result<Option<String>, LowerError> {
    match &t.node {
        TermKind::Path(p) if p.segments.len() == 1 => {
            let w = &p.segments[0];
            require_bound(cx, w)?;
            Ok(Some(w.text.clone()))
        }
        _ => Ok(None),
    }
}

fn literal(l: &ast::Literal) -> Result<Opd, LowerError> {
    match &l.node {
        LiteralKind::Int(i) => i64::try_from(*i)
            .map(Opd::Int)
            .or_else(|_| unsupported("an integer beyond 64 bits", l.span)),
        LiteralKind::Str(s) => Ok(Opd::Str(s.clone())),
        LiteralKind::Bool(b) => Ok(Opd::Bool(*b)),
        _ => unsupported("this literal as an operand", l.span),
    }
}

fn operand(cx: &Cx, t: &Term) -> Result<Opd, LowerError> {
    match &t.node {
        TermKind::Literal(l) => literal(l),
        TermKind::Path(p) => {
            require_bound(cx, &p.segments[0])?;
            match p.segments.as_slice() {
                [v] => Ok(Opd::Var(v.text.clone())),
                [v, f] => Ok(Opd::Field(v.text.clone(), f.text.clone())),
                _ => unsupported("a path of more than two segments", p.span),
            }
        }
        TermKind::Knob(w) => unsupported("a knob", w.span),
        _ => unsupported("this term", t.span),
    }
}

/// The object of a relation as a variable: a variable in scope, or an anonymous kind shape that
/// becomes `some _n: KIND where ...` around the relation.
fn with_object(
    cx: &mut Cx,
    object: &Object,
    build: impl FnOnce(String) -> Cond,
) -> Result<Cond, LowerError> {
    let (kind, fields): (String, Vec<(String, Opd)>) = match object {
        Object::Term(t) => match &t.node {
            TermKind::Path(p) if p.segments.len() == 1 => {
                let w = &p.segments[0];
                if cx.scope.contains(&w.text) {
                    return Ok(build(w.text.clone()));
                }
                (w.text.clone(), Vec::new())
            }
            _ => return unsupported("this relation object", t.span),
        },
        Object::Shape(s) => match &s.node {
            ShapeKind::Kind { kind, fields, arg } => {
                if arg.is_some() {
                    return unsupported("a kind with a string argument", s.span);
                }
                let fs = fields
                    .iter()
                    .map(|f| Ok((f.name.text.clone(), literal(&f.value)?)))
                    .collect::<Result<_, LowerError>>()?;
                (kind.text.clone(), fs)
            }
            _ => return unsupported("a snippet or alternatives as a relation object", s.span),
        },
    };
    let var = format!("_{}", cx.fresh);
    cx.fresh += 1;
    let mut conds = vec![build(var.clone())];
    for (f, v) in fields {
        conds.push(Cond::Cmp {
            lhs: Opd::Field(var.clone(), f),
            op: CmpOp::Eq,
            rhs: v,
        });
    }
    Ok(Cond::Quant {
        quant: Quant::Some,
        var,
        kind,
        cond: Box::new(if conds.len() == 1 {
            conds.remove(0)
        } else {
            Cond::And(conds)
        }),
    })
}

fn rel_cond(cx: &mut Cx, subject: &str, r: &ast::Rel) -> Result<Cond, LowerError> {
    let s = subject.to_owned();
    match &r.node {
        RelKind::Containment {
            directly,
            dir,
            object,
        } => {
            let (directly, dir) = (*directly, *dir);
            with_object(cx, object, move |o| match dir {
                ast::Containment::Inside => Cond::Inside {
                    sub: s,
                    sup: o,
                    direct: directly,
                },
                ast::Containment::Has => Cond::Inside {
                    sub: o,
                    sup: s,
                    direct: directly,
                },
            })
        }
        RelKind::Position { position, object } => {
            let pos = match position {
                ast::Position::Before => Position::Before,
                ast::Position::After => Position::After,
                ast::Position::Adjoins => Position::Adjoins,
            };
            with_object(cx, object, move |o| Cond::Order { a: s, b: o, pos })
        }
        RelKind::Verb {
            certainty,
            verb,
            object,
        } => {
            let certainty = match certainty {
                None => Certainty::Default,
                Some(ast::Certainty::Certainly) => Certainty::Certainly,
                Some(ast::Certainty::Possibly) => Certainty::Possibly,
            };
            let verb = verb.text.clone();
            with_object(cx, object, move |o| Cond::Verb {
                subject: s,
                object: o,
                verb,
                certainty,
            })
        }
        RelKind::InUnit { .. } => unsupported("`in unit`", r.span),
        RelKind::Under { .. } => unsupported("`under`", r.span),
        RelKind::Reaches { .. } => unsupported("`reaches`", r.span),
    }
}
