//! The Kleene evaluator over a plan's condition ops (grl-spec.md 7.0 and 7.1).
//!
//! Every op denotes a [`Verdict`] under an environment of bound variables. Quantifiers range
//! over the hi bound of their kind's domain, weight each candidate by its membership truth, and
//! add an Unknown disjunct when the model has unread regions (review 2.2 item 7).

use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use gob_ir::{Location, Model, NodeId, Truth};
use gob_text::SourceText;
use regex::Regex;

use super::field::{Datum, Reader, Scalar, compare};
use super::kind::{KindTest, may_hide_members};
use super::verdict::{Doubt, Verdict};
use crate::plan::{Op, OpId, Operand, PlanParts, Position, Quant, StrId, VarId};

/// A value a variable is bound to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Val {
    /// A node of the model.
    Node(NodeId),
}

/// Variable slots; `None` is unbound.
pub(crate) type Env = Vec<Option<Val>>;

/// A kind's members in location order with their membership truth.
pub(crate) type Domain = Rc<Vec<(NodeId, Truth)>>;

/// A compiled `matches` pattern.
pub(crate) enum Matcher {
    Regex(Regex),
    Glob(globset::GlobMatcher),
}

/// The evaluator for one plan over one model.
pub(crate) struct Eval<'a> {
    pub(crate) plan: &'a PlanParts,
    pub(crate) rd: Reader<'a>,
    pub(crate) hidden: bool,
    kinds: HashMap<StrId, KindTest>,
    matchers: HashMap<OpId, Matcher>,
    order: Vec<NodeId>,
    domains: RefCell<HashMap<StrId, Domain>>,
}

impl<'a> Eval<'a> {
    /// Builds the evaluator from pre-validated pieces (see `ExecError` for refusals).
    pub(crate) fn new(
        plan: &'a PlanParts,
        model: &'a Model,
        source: Option<&'a SourceText>,
        kinds: HashMap<StrId, KindTest>,
        matchers: HashMap<OpId, Matcher>,
    ) -> Self {
        Self {
            plan,
            rd: Reader { model, source },
            hidden: may_hide_members(model),
            kinds,
            matchers,
            order: model.term().nodes_by_location(),
            domains: RefCell::default(),
        }
    }

    fn string(&self, id: StrId) -> &'a str {
        &self.plan.strings[id as usize]
    }

    /// The members of kind `kind` in location order.
    pub(crate) fn domain(&self, kind: StrId) -> Domain {
        if let Some(d) = self.domains.borrow().get(&kind) {
            return Rc::clone(d);
        }
        let test = self.kinds[&kind];
        let members: Vec<(NodeId, Truth)> = self
            .order
            .iter()
            .filter_map(|&n| test.member(self.rd.model, n).map(|t| (n, t)))
            .collect();
        tracing::debug!(
            kind = self.string(kind),
            members = members.len(),
            "domain built"
        );
        let d = Rc::new(members);
        self.domains.borrow_mut().insert(kind, Rc::clone(&d));
        d
    }

    fn node(env: &Env, v: VarId) -> NodeId {
        match env[usize::from(v)] {
            Some(Val::Node(n)) => n,
            None => unreachable!("validated plans use only bound variables"),
        }
    }

    /// The value of an operand under `env`.
    pub(crate) fn datum(&self, o: &Operand, env: &Env) -> Datum {
        match *o {
            Operand::Var(v) => Datum::Node(Self::node(env, v)),
            Operand::Field(v, f) => self.rd.field(Self::node(env, v), self.string(f)),
            Operand::Int(i) => Datum::Known(Scalar::Int(i)),
            Operand::Str(s) => Datum::text(self.string(s)),
            Operand::Bool(b) => Datum::Known(Scalar::Bool(b)),
        }
    }

    fn describe(&self, o: &Operand, env: &Env) -> Doubt {
        match *o {
            Operand::Field(v, f) => Doubt::Dynamic {
                node: Some(Self::node(env, v)),
                field: self.string(f).to_owned(),
            },
            _ => Doubt::Dynamic {
                node: None,
                field: "operand".to_owned(),
            },
        }
    }

    /// Evaluates condition `id` under `env`.
    pub(crate) fn eval(&self, id: OpId, env: &mut Env) -> Verdict {
        match &self.plan.ops[id as usize] {
            Op::And(cs) => {
                let mut acc = Verdict::yes();
                for &c in cs {
                    acc = acc.and(self.eval(c, env));
                    if acc.truth == Truth::No {
                        break;
                    }
                }
                acc
            }
            Op::Or(cs) => {
                let mut acc = Verdict::no();
                for &c in cs {
                    acc = acc.or(self.eval(c, env));
                    if acc.truth == Truth::Yes {
                        break;
                    }
                }
                acc
            }
            Op::Not(c) => !self.eval(*c, env),
            Op::Quant {
                quant,
                var,
                kind,
                cond,
            } => {
                let some = self.some(*var, *kind, *cond, env);
                match quant {
                    Quant::Some => some,
                    Quant::No => !some,
                }
            }
            Op::Inside { sub, sup, direct } => {
                let (sub, sup) = (Self::node(env, *sub), Self::node(env, *sup));
                Verdict::certain(self.inside(sub, sup, *direct))
            }
            Op::Order { a, b, pos } => self.order(Self::node(env, *a), Self::node(env, *b), *pos),
            Op::Cmp { lhs, op, rhs } => {
                let (l, r) = (self.datum(lhs, env), self.datum(rhs, env));
                Verdict::of(compare(*op, &l, &r), || {
                    if l == Datum::Unknown {
                        self.describe(lhs, env)
                    } else {
                        self.describe(rhs, env)
                    }
                })
            }
            Op::MatchRegex { subject, .. } | Op::MatchGlob { subject, .. } => {
                self.matches(id, subject, env)
            }
            Op::Find { .. } | Op::FindSide { .. } | Op::Verb { .. } | Op::Reaches { .. } => {
                unreachable!("refused before the run starts")
            }
        }
    }

    /// `some var: kind where cond`: the `or` over the domain, plus the hidden-member disjunct.
    fn some(&self, var: VarId, kind: StrId, cond: OpId, env: &mut Env) -> Verdict {
        let mut acc = Verdict::no();
        for &(n, member) in self.domain(kind).iter() {
            env[usize::from(var)] = Some(Val::Node(n));
            let mut v = self.eval(cond, env);
            if member == Truth::Unknown {
                v = v.and(Verdict::unknown(Doubt::Member { node: n }));
            }
            acc = acc.or(v);
            if acc.truth == Truth::Yes {
                break;
            }
        }
        env[usize::from(var)] = None;
        if acc.truth == Truth::No && self.hidden {
            return Verdict::unknown(Doubt::Hidden);
        }
        acc
    }

    /// `sub inside sup`: `sup` is an ancestor (the parent when `direct`).
    fn inside(&self, sub: NodeId, sup: NodeId, direct: bool) -> bool {
        let term = self.rd.model.term();
        if direct {
            term.parent(sub) == Some(sup)
        } else {
            term.is_ancestor(sup, sub)
        }
    }

    /// Source order of two nodes of one file: `before` means `a` ends no later than `b` starts.
    fn order(&self, a: NodeId, b: NodeId, pos: Position) -> Verdict {
        let term = self.rd.model.term();
        let (la, lb) = (term.node(a).location(), term.node(b).location());
        let (
            Location::Text {
                file: fa,
                range: ra,
            },
            Location::Text {
                file: fb,
                range: rb,
            },
        ) = (la, lb)
        else {
            return Verdict::unknown(Doubt::Dynamic {
                node: Some(a),
                field: "location".to_owned(),
            });
        };
        if fa != fb {
            return Verdict::no();
        }
        match pos {
            Position::Before => Verdict::certain(ra.end() <= rb.start()),
            Position::After => Verdict::certain(rb.end() <= ra.start()),
            Position::Adjoins => {
                let ends = |r: gob_text::TextRange| {
                    let last = if r.is_empty() {
                        r.start()
                    } else {
                        gob_text::TextSize::new(u32::from(r.end()) - 1)
                    };
                    (r.start(), last)
                };
                let (sa, ea) = ends(*ra);
                let (sb, eb) = ends(*rb);
                let line = |o| self.rd.source.and_then(|s| s.line_col(o)).map(|lc| lc.line);
                match (line(sa), line(ea), line(sb), line(eb)) {
                    (Some(sa), Some(ea), Some(sb), Some(eb)) => {
                        let near = |end: u32, start: u32| end == start || end + 1 == start;
                        Verdict::certain(near(ea, sb) || near(eb, sa))
                    }
                    _ => Verdict::unknown(Doubt::Dynamic {
                        node: Some(a),
                        field: "line".to_owned(),
                    }),
                }
            }
        }
    }

    fn matches(&self, id: OpId, subject: &Operand, env: &Env) -> Verdict {
        let d = self.datum(subject, env);
        let test = |s: &str| match &self.matchers[&id] {
            Matcher::Regex(r) => r.is_match(s),
            Matcher::Glob(g) => g.is_match(s),
        };
        let truth = match &d {
            Datum::Known(Scalar::Str(s)) => Truth::from_bool(test(s)),
            Datum::OneOf(vs) => {
                let hits: Vec<bool> = vs
                    .iter()
                    .filter_map(|v| match v {
                        Scalar::Str(s) => Some(test(s)),
                        _ => None,
                    })
                    .collect();
                if hits.iter().all(|&h| h) && !hits.is_empty() {
                    Truth::Yes
                } else if hits.iter().all(|&h| !h) {
                    Truth::No
                } else {
                    Truth::Unknown
                }
            }
            Datum::Absent | Datum::Known(_) | Datum::Node(_) => Truth::No,
            Datum::Unknown => Truth::Unknown,
        };
        Verdict::of(truth, || self.describe(subject, env))
    }
}
