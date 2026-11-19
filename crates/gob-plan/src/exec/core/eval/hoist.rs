//! Quantifiers whose body is one graph test against a variable bound outside them.
//!
//! `some t: test where t reaches f via calls within n` asks, for every `f`, whether any member of
//! `test` reaches it. Scanning the members per `f` costs `members * bindings`; the members do not
//! depend on `f`, so once the quantifier has run a few times their reach (or edges, or
//! ancestry) is folded into one set and each later `f` is a lookup. Only a decided answer is
//! taken from the set: an Unknown carries doubts that name the members, so those fall back to the
//! scan, which keeps every verdict identical (frob:ticket 01M4PTYYJ0Z968WHGQ0PYM5S6B).

use std::collections::HashSet;
use std::rc::Rc;

use gob_ir::{NodeId, Truth};

use super::{Domain, Env, Eval};
use crate::exec::core::kind::unwrap_statement;
use crate::exec::relations::{ClosureUnion, EdgeUnion, OWNED_BY, PEER_OF};
use crate::plan::{Certainty, Op, OpId, VarId};

/// Evaluations of one quantifier before its members are folded.
const WARM: u32 = 8;

/// A folded quantifier body.
pub(super) enum Hoist {
    /// `some t: K where sub inside t`: the members of `K`.
    Inside {
        /// The members of the kind.
        members: HashSet<NodeId>,
        /// The outer variable that must sit inside one of them.
        sub: VarId,
    },
    /// `some t: K where t reaches to via R within n`.
    Reach {
        /// What any member reaches.
        union: ClosureUnion,
        /// The outer variable that must be reached.
        to: VarId,
    },
    /// `some t: K where t VERB object`.
    Edge {
        /// The edges out of the members.
        union: EdgeUnion,
        /// The outer variable the edge must end at.
        object: VarId,
    },
}

impl Eval<'_> {
    /// The decided truth of `some var: domain where cond` under `env`, when the body is a graph
    /// test that was folded; `None` means scan the members.
    pub(super) fn hoisted(
        &self,
        var: VarId,
        cond: OpId,
        domain: &Domain,
        env: &Env,
    ) -> Option<Truth> {
        if let Some(h) = self.hoists.borrow().get(&cond) {
            return h.as_ref().and_then(|h| self.probe(h, env));
        }
        let warm = {
            let mut seen = self.warmth.borrow_mut();
            let n = seen.entry(cond).or_insert(0u32);
            *n += 1;
            *n
        };
        if warm <= WARM {
            return None;
        }
        let built = self.fold(var, cond, domain).map(Rc::new);
        let answer = built.as_ref().and_then(|h| self.probe(h, env));
        self.hoists.borrow_mut().insert(cond, built);
        answer
    }

    /// Folds the members of `domain` for the body `cond`, when it has a foldable shape and every
    /// member is a certain one (a May member would add a doubt of its own).
    fn fold(&self, var: VarId, cond: OpId, domain: &Domain) -> Option<Hoist> {
        if domain.iter().any(|&(_, m)| m != Truth::Yes) {
            return None;
        }
        let default = |c: Certainty| self.effective(c) == Certainty::Default;
        match self.plan.ops[cond as usize] {
            Op::Inside {
                sub,
                sup,
                direct: false,
            } if sup == var && sub != var => Some(Hoist::Inside {
                members: domain.iter().map(|&(n, _)| n).collect(),
                sub,
            }),
            Op::Reaches {
                from,
                to,
                via,
                within,
                certainty,
            } if from == var && to != var && default(certainty) => {
                let mut union = ClosureUnion::new();
                for &(n, _) in domain.iter() {
                    self.closure_of(via, n, within).join_into(&mut union);
                }
                Some(Hoist::Reach { union, to })
            }
            Op::Verb {
                subject,
                object,
                verb,
                certainty,
            } if subject == var
                && object != var
                && default(certainty)
                && !matches!(self.string(verb), OWNED_BY | PEER_OF) =>
            {
                let rel = self.wired.edges[&verb];
                let mut union = EdgeUnion::new();
                for &(n, _) in domain.iter() {
                    union.add(rel, unwrap_statement(self.rd.model, n));
                }
                Some(Hoist::Edge { union, object })
            }
            _ => None,
        }
    }

    /// The decided truth of the folded quantifier for the outer binding in `env`.
    fn probe(&self, h: &Hoist, env: &Env) -> Option<Truth> {
        match h {
            Hoist::Inside { members, sub } => {
                let term = self.rd.model.term();
                let found =
                    std::iter::successors(term.parent(Self::node(env, *sub)), |&n| term.parent(n))
                        .any(|a| members.contains(&a));
                Some(Truth::from_bool(found))
            }
            Hoist::Reach { union, to } => union.decides(self.unit_of(Self::node(env, *to))),
            Hoist::Edge { union, object } => union.decides(Self::node(env, *object)),
        }
    }
}
