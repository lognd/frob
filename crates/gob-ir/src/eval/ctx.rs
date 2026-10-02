//! The evaluation context: relation accessors that track the dependency cone.
//!
//! Every accessor that touches an `opaque` node, a `hole` node or a non-`Must`
//! resolution edge records a [`Poison`]. The evaluator reads the record after a
//! subject's check: an `Exact` answer computed through poisoned atoms is
//! downgraded to `Unknown` (universal-model.md 4.3, soundness under Kleene logic).

use std::cell::RefCell;
use std::collections::BTreeMap;
use std::rc::Rc;

use tracing::trace;

use super::relation::Relation;
use crate::answer::{Answer, Truth};
use crate::operator::{Operator, Universal};
use crate::query::Model;
use crate::scope::{Resolution, Status};
use crate::term::{NodeId, Term};

/// Why an atom is not exact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PoisonReason {
    /// An opaque node with this reason code.
    Opaque(String),
    /// A hole or parse-error node.
    Hole,
    /// A resolution edge below `Must`.
    Edge(Status),
}

impl PoisonReason {
    /// A stable reason code for findings.
    pub fn code(&self) -> String {
        match self {
            Self::Opaque(r) => r.clone(),
            Self::Hole => "hole".to_owned(),
            Self::Edge(Status::May) => "edge:may".to_owned(),
            Self::Edge(_) => "edge:unknown".to_owned(),
        }
    }
}

/// One poisoned atom in a dependency cone.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Poison {
    /// The node whose atom was not exact.
    pub node: NodeId,
    /// Why.
    pub reason: PoisonReason,
}

/// Read access to the term relations for one rule evaluation.
#[derive(Debug)]
pub struct Ctx<'m> {
    model: &'m Model,
    poison: RefCell<Vec<Poison>>,
    derived: RefCell<BTreeMap<String, Rc<Relation>>>,
}

impl<'m> Ctx<'m> {
    /// A context over `model` with no derived relations.
    pub fn new(model: &'m Model) -> Self {
        Self {
            model,
            poison: RefCell::default(),
            derived: RefCell::default(),
        }
    }

    /// The model.
    pub fn model(&self) -> &'m Model {
        self.model
    }

    /// The term.
    pub fn term(&self) -> &'m Term {
        self.model.term()
    }

    fn record(&self, node: NodeId, reason: PoisonReason) {
        trace!(%node, ?reason, "dependency cone poisoned");
        self.poison.borrow_mut().push(Poison { node, reason });
    }

    /// Record `node` if it is opaque or a hole; returns whether it was.
    pub fn touch(&self, node: NodeId) -> bool {
        match &self.term().node(node).op {
            Operator::Universal(Universal::Opaque { reason, .. }) => {
                self.record(node, PoisonReason::Opaque(reason.clone()));
                true
            }
            Operator::Universal(Universal::Hole { .. }) => {
                self.record(node, PoisonReason::Hole);
                true
            }
            _ => false,
        }
    }

    /// Poison recorded since the last [`Ctx::clear_poison`].
    pub fn poison(&self) -> Vec<Poison> {
        self.poison.borrow().clone()
    }

    /// Forget recorded poison (the evaluator does this before each subject).
    pub fn clear_poison(&self) {
        self.poison.borrow_mut().clear();
    }

    /// Atom `pred(op(n))`: `Unknown` on an opaque or hole node.
    pub fn op_is(&self, n: NodeId, pred: impl Fn(&Operator) -> bool) -> Truth {
        if self.touch(n) {
            Truth::Unknown
        } else {
            Truth::from_bool(pred(&self.term().node(n).op))
        }
    }

    /// Children of `n`: `Unknown` when `n` is opaque or a hole; opaque or hole children are touched.
    pub fn children(&self, n: NodeId) -> Answer<Vec<NodeId>> {
        if self.touch(n) {
            return Answer::Unknown;
        }
        let kids = self.term().children(n).to_vec();
        for &k in &kids {
            self.touch(k);
        }
        Answer::Exact(kids)
    }

    /// Descendants of `n` in preorder; every opaque or hole among them is touched.
    pub fn descendants(&self, n: NodeId) -> Answer<Vec<NodeId>> {
        if self.touch(n) {
            return Answer::Unknown;
        }
        let ds = self.term().descendants(n);
        for &d in &ds {
            self.touch(d);
        }
        Answer::Exact(ds)
    }

    /// The parent of `n` (always exact).
    pub fn parent(&self, n: NodeId) -> Option<NodeId> {
        self.term().parent(n)
    }

    /// Attributes and comments attached to `n`.
    pub fn attached(&self, n: NodeId) -> Answer<Vec<NodeId>> {
        if self.touch(n) {
            Answer::Unknown
        } else {
            Answer::Exact(self.term().attachments(n))
        }
    }

    /// Resolve the `ref` node `n`; a non-`Must` result poisons the cone.
    pub fn resolve(&self, n: NodeId) -> Resolution {
        let r = self.model.resolve_node(n);
        if r.status() != Status::Must {
            self.record(n, PoisonReason::Edge(r.status()));
        }
        r
    }

    /// Atom "the reference `r` resolves to the declaration containing node `d`".
    pub fn resolves_to(&self, r: NodeId, d: NodeId) -> Truth {
        let Some(decl) = self.model.scopes().decl_at(d) else {
            return Truth::No;
        };
        match self.resolve(r) {
            Resolution::Must(x) => Truth::from_bool(x == decl),
            Resolution::May(set) if set.contains(&decl) => Truth::Unknown,
            Resolution::May(_) => Truth::No,
            Resolution::Unknown => Truth::Unknown,
        }
    }

    /// Atom `loc(a) < loc(b)` in the location order.
    pub fn loc_before(&self, a: NodeId, b: NodeId) -> Truth {
        let t = self.term();
        Truth::from_bool(t.node(a).location < t.node(b).location)
    }

    /// Atom "the location of `a` contains the location of `b`".
    pub fn loc_contains(&self, a: NodeId, b: NodeId) -> Truth {
        let t = self.term();
        Truth::from_bool(t.node(a).location.contains(&t.node(b).location))
    }

    /// Poison-aware membership: an `Unknown` pair poisons; an absent pair at a poisoned node is `Unknown`.
    pub fn holds(&self, rel: &Relation, a: NodeId, b: NodeId) -> Truth {
        match rel.get(a, b) {
            Truth::Yes => Truth::Yes,
            Truth::Unknown => {
                self.record(a, PoisonReason::Edge(Status::May));
                Truth::Unknown
            }
            Truth::No => {
                if self.touch(a) | self.touch(b) {
                    Truth::Unknown
                } else {
                    Truth::No
                }
            }
        }
    }

    /// The child relation: `(parent, child)`, all `Yes`.
    pub fn rel_child(&self) -> Relation {
        let mut r = Relation::new();
        for id in self.term().ids() {
            for &c in self.term().children(id) {
                r.insert(id, c, Truth::Yes);
            }
        }
        r
    }

    /// The resolution relation: `(ref node, declaring node)`; `Must` is `Yes`, `May` is `Unknown`.
    ///
    /// References that resolve to `Unknown` contribute no pair and poison the cone.
    pub fn rel_resolves(&self) -> Relation {
        let mut r = Relation::new();
        let scopes = self.model.scopes();
        for id in self.term().ids() {
            let Some(rf) = scopes.ref_at(id) else {
                continue;
            };
            match scopes.resolve(rf) {
                Resolution::Must(d) => {
                    for &n in &scopes.decl(d).nodes {
                        r.insert(id, n, Truth::Yes);
                    }
                }
                Resolution::May(set) => {
                    self.record(id, PoisonReason::Edge(Status::May));
                    for d in set {
                        for &n in &scopes.decl(d).nodes {
                            r.insert(id, n, Truth::Unknown);
                        }
                    }
                }
                Resolution::Unknown => self.record(id, PoisonReason::Edge(Status::Unknown)),
            }
        }
        r
    }

    /// The call graph over units: `(caller unit, callee unit)` for every `apply` whose head is a
    /// `ref`; the callee is the first part of the resolved identity.
    pub fn rel_calls(&self) -> Relation {
        let mut r = Relation::new();
        let t = self.term();
        let scopes = self.model.scopes();
        for id in t.ids() {
            if !matches!(t.node(id).op, Operator::Universal(Universal::Apply { .. })) {
                continue;
            }
            let Some(caller) = t
                .ancestors(id)
                .into_iter()
                .find(|&a| t.node(a).op.is_unit_like())
            else {
                continue;
            };
            let head = t.children(id)[0];
            if self.touch(head) {
                continue;
            }
            let Some(rf) = scopes.ref_at(head) else {
                continue;
            };
            match scopes.resolve(rf) {
                Resolution::Must(d) => {
                    if let Some(&n) = scopes.decl(d).nodes.first() {
                        r.insert(caller, n, Truth::Yes);
                    }
                }
                Resolution::May(set) => {
                    self.record(head, PoisonReason::Edge(Status::May));
                    for d in set {
                        if let Some(&n) = scopes.decl(d).nodes.first() {
                            r.insert(caller, n, Truth::Unknown);
                        }
                    }
                }
                Resolution::Unknown => self.record(head, PoisonReason::Edge(Status::Unknown)),
            }
        }
        r
    }

    /// A relation derived by an earlier stratum.
    pub fn derived(&self, name: &str) -> Option<Rc<Relation>> {
        self.derived.borrow().get(name).cloned()
    }

    pub(crate) fn set_derived(&self, name: &str, rel: Relation) {
        self.derived
            .borrow_mut()
            .insert(name.to_owned(), Rc::new(rel));
    }
}
