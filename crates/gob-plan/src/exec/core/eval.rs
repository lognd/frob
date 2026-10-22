//! The Kleene evaluator over a plan's condition ops (grl-spec.md 7.0 and 7.1).
//!
//! Every op denotes a [`Verdict`] under an environment of bound variables. Quantifiers range
//! over the hi bound of their kind's domain, weight each candidate by its membership truth, and
//! add an Unknown disjunct when the model has unread regions (review 2.2 item 7).

use std::cell::{Cell, RefCell};
use std::collections::{HashMap, HashSet};
use std::ops::Range;
use std::rc::Rc;

use gob_ir::{Location, Model, NodeId, Relation, Truth};
use gob_text::SourceText;
use regex::Regex;

use super::field::{Datum, Reader, Scalar, compare};
use super::fxmap::FastMap;
use super::kind::{KindTest, is_canonical_unit};
use super::verdict::{Doubt, Verdict};
use crate::exec::relations::{self, Count, Knobs, OWNED_BY, PEER_OF, SideRow, SideTable};
use crate::plan::{Certainty, Limit, Op, OpId, Operand, PlanParts, Position, Quant, StrId, VarId};

mod index;
mod predicate;

pub(crate) use predicate::is_test_word;

/// The byte ranges a snippet matched in the file, or `None` when the text could not be scanned.
type SnippetRanges = Rc<Option<Vec<Range<usize>>>>;

/// A value a variable is bound to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Val {
    /// A node of the model.
    Node(NodeId),
    /// A row of a side relation (`find p: diff.changed`).
    Row(SideRow),
}

/// Variable slots; `None` is unbound.
pub(crate) type Env = Vec<Option<Val>>;

/// A kind's members in location order with their membership truth.
pub(crate) type Domain = Rc<Vec<(NodeId, Truth)>>;

/// The cache key of a computed comparison side: the op, the side, and the values of the (up to
/// two) variables the operand reads.
type OperandKey = (OpId, bool, Option<Val>, Option<Val>);

/// A node's cached line span: `None` when the node has no location.
type LineSpan = Option<(u32, u32)>;

/// A comparison side: freshly read, or shared from the operand cache.
enum Side {
    Fresh(Datum),
    Shared(Rc<Datum>),
}

impl std::ops::Deref for Side {
    type Target = Datum;

    fn deref(&self) -> &Datum {
        match self {
            Self::Fresh(d) => d,
            Self::Shared(d) => d,
        }
    }
}

/// A compiled `matches` pattern.
pub(crate) enum Matcher {
    Regex(Regex),
    Glob(globset::GlobMatcher),
    /// Any glob of a side-relation column.
    Set(globset::GlobSet),
    /// A grammar-level snippet pattern.
    Snippet(Box<gob_pattern::grammar::Pattern>),
}

/// The relation inputs a plan names, resolved by the plan string that names them.
#[derive(Default)]
pub(crate) struct Wired<'a> {
    /// Edge relations by the string id of the verb word or `via` family.
    pub(crate) edges: HashMap<StrId, &'a Relation>,
    /// Side tables by the string id of the relation name.
    pub(crate) side: HashMap<StrId, &'a SideTable>,
    /// Kind words (by string id) that range over rows of the side table of the same id.
    pub(crate) row_kinds: HashSet<StrId>,
    /// The `owned by` globs per model node name, built from `model.selectors`.
    pub(crate) owners: HashMap<String, globset::GlobSet>,
    /// The `[rules]` knob overrides.
    pub(crate) knobs: Knobs,
    /// The most condition evaluations before the run gives up.
    pub(crate) budget: u64,
}

/// The evaluator for one plan over one model.
pub(crate) struct Eval<'a> {
    pub(crate) plan: &'a PlanParts,
    pub(crate) rd: Reader<'a>,
    pub(crate) hidden: bool,
    kinds: HashMap<StrId, KindTest>,
    matchers: HashMap<OpId, Matcher>,
    wired: Wired<'a>,
    /// Per-node (first line, last line) of its text span, filled on first use (`adjoins`).
    spans: RefCell<Vec<Option<LineSpan>>>,
    /// Bounded forward closures by (via relation, from, steps), computed once per run.
    closures: RefCell<FastMap<(StrId, NodeId, u16), Rc<relations::Closure>>>,
    /// Computed operands (`slug`, `resolve`, dotted fields) by (op, side, argument values).
    operands: RefCell<FastMap<OperandKey, Rc<Datum>>>,
    /// Equality-join indexes by the id of the equality conjunct they serve.
    indexes: RefCell<FastMap<OpId, Rc<index::EqIndex>>>,
    /// The unit each closure target stands for, computed once per node.
    units: RefCell<FastMap<NodeId, NodeId>>,
    domains: RefCell<FastMap<StrId, Domain>>,
    /// Materialised def views by (def, argument values): each is computed once (7.0.2).
    views: RefCell<FastMap<(u16, Vec<Val>), Verdict>>,
    steps: Cell<u64>,
    /// Snippet matches by op: the byte ranges found in the file text, computed once per run.
    snippets: RefCell<FastMap<OpId, SnippetRanges>>,
}

/// Sorts `members` into location order, ties by id (the order of `nodes_by_location`).
fn order_members(model: &Model, members: &mut [(NodeId, Truth)]) {
    let term = model.term();
    members.sort_by(|&(a, _), &(b, _)| {
        term.node(a)
            .location()
            .cmp(term.node(b).location())
            .then(a.cmp(&b))
    });
}

/// One pass over the model: whether any part is unread, and every plan kind's ordered domain.
///
/// frob:ticket 01M5C7AA29V08HTNZM0BA2A6ST
/// Fusing these passes reads each node once instead of once per kind plus once for `hidden`;
/// on cheap rules the repeated cold traversals dominated the run.
fn scan(model: &Model, kinds: &HashMap<StrId, KindTest>) -> (bool, FastMap<StrId, Domain>) {
    let term = model.term();
    let tests: Vec<(StrId, KindTest)> = kinds.iter().map(|(&k, &t)| (k, t)).collect();
    let mut found: Vec<Vec<(NodeId, Truth)>> = vec![Vec::new(); tests.len()];
    let mut hidden = false;
    for n in term.ids() {
        let op = term.node(n).op();
        hidden |= op.is_opaque() || op.is_hole();
        for (i, (_, t)) in tests.iter().enumerate() {
            if let Some(m) = t.member(model, n) {
                found[i].push((n, m));
            }
        }
    }
    let mut domains = FastMap::default();
    for ((kind, _), mut members) in tests.into_iter().zip(found) {
        order_members(model, &mut members);
        domains.insert(kind, Rc::new(members));
    }
    (hidden, domains)
}

impl<'a> Eval<'a> {
    /// Builds the evaluator from pre-validated pieces (see `ExecError` for refusals).
    pub(crate) fn new(
        plan: &'a PlanParts,
        model: &'a Model,
        source: Option<&'a SourceText>,
        kinds: HashMap<StrId, KindTest>,
        matchers: HashMap<OpId, Matcher>,
        wired: Wired<'a>,
    ) -> Self {
        let (hidden, domains) = scan(model, &kinds);
        Self {
            plan,
            rd: Reader { model, source },
            hidden,
            kinds,
            matchers,
            wired,
            spans: RefCell::new(vec![None; model.term().ids().count()]),
            closures: RefCell::default(),
            units: RefCell::default(),
            indexes: RefCell::default(),
            operands: RefCell::default(),
            domains: RefCell::new(domains),
            views: RefCell::default(),
            steps: Cell::new(0),
            snippets: RefCell::default(),
        }
    }

    fn string(&self, id: StrId) -> &'a str {
        &self.plan.strings[id as usize]
    }

    /// Whether `kind` ranges over rows of a model side table rather than nodes of the code term.
    pub(crate) fn is_row_kind(&self, kind: StrId) -> bool {
        self.wired.row_kinds.contains(&kind)
    }

    /// The members of kind `kind` in location order.
    pub(crate) fn domain(&self, kind: StrId) -> Domain {
        if let Some(d) = self.domains.borrow().get(&kind) {
            return Rc::clone(d);
        }
        let test = self.kinds[&kind];
        let mut members = Vec::new();
        for n in self.rd.model.term().ids() {
            if let Some(t) = test.member(self.rd.model, n) {
                members.push((n, t));
            }
        }
        order_members(self.rd.model, &mut members);
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
            Some(Val::Row(_)) => {
                unreachable!("a side-relation row is read by column, never as a node")
            }
            None => unreachable!("validated plans use only bound variables"),
        }
    }

    /// The rows of the side relation named by string `table`, in supply order.
    pub(crate) fn side_rows(&self, table: StrId) -> u32 {
        let rows = self.wired.side[&table].len();
        u32::try_from(rows).expect("side tables are far below u32::MAX rows")
    }

    /// Reads field `f` of the variable `v`: a node field, or a column of a side-relation row.
    fn field_of(&self, env: &Env, v: VarId, f: StrId) -> Datum {
        match env[usize::from(v)] {
            Some(Val::Node(n)) => self.rd.field(n, self.string(f)),
            Some(Val::Row(r)) => self.wired.side[&r.table].cell(r.index, self.string(f)),
            None => unreachable!("validated plans use only bound variables"),
        }
    }

    /// The value of an operand under `env`.
    pub(crate) fn datum(&self, o: &Operand, env: &Env) -> Datum {
        match *o {
            Operand::Var(v) => Datum::Node(Self::node(env, v)),
            Operand::Field(v, f) => self.field_of(env, v, f),
            Operand::Int(i) => Datum::Known(Scalar::Int(i)),
            Operand::Str(s) => Datum::text(self.string(s)),
            Operand::Bool(b) => Datum::Known(Scalar::Bool(b)),
            Operand::Slug(a) => super::call::slug(self.leaf_text(a.operand(), env)),
            Operand::Resolve(a, b) => super::call::resolve(
                self.leaf_text(a.operand(), env),
                self.leaf_text(b.operand(), env),
            ),
        }
    }

    /// A comparison side; the loop-invariant computed operands are cached per argument values
    /// (frob:ticket 01M5C7AA29V08HTNZM0BA2A6ST).
    fn side(&self, op: OpId, rhs: bool, o: &Operand, env: &Env) -> Side {
        let val = |l: Operand| match l {
            Operand::Var(v) | Operand::Field(v, _) => env[usize::from(v)],
            _ => None,
        };
        let vals = match *o {
            Operand::Slug(a) => (val(a.operand()), None),
            Operand::Resolve(a, b) => (val(a.operand()), val(b.operand())),
            Operand::Field(v, f) if self.string(f).contains('.') => (env[usize::from(v)], None),
            _ => return Side::Fresh(self.datum(o, env)),
        };
        let key = (op, rhs, vals.0, vals.1);
        if let Some(d) = self.operands.borrow().get(&key) {
            return Side::Shared(Rc::clone(d));
        }
        let d = Rc::new(self.datum(o, env));
        self.operands.borrow_mut().insert(key, Rc::clone(&d));
        Side::Shared(d)
    }

    /// A call argument as a datum; a file node stands for its path.
    fn leaf_text(&self, o: Operand, env: &Env) -> Datum {
        match self.datum(&o, env) {
            Datum::Node(n) => self.rd.field(n, "path"),
            d => d,
        }
    }

    fn describe(&self, o: &Operand, env: &Env) -> Doubt {
        match *o {
            Operand::Field(v, f) => Doubt::Dynamic {
                node: match env[usize::from(v)] {
                    Some(Val::Node(n)) => Some(n),
                    _ => None,
                },
                field: self.string(f).to_owned(),
            },
            _ => Doubt::Dynamic {
                node: None,
                field: "operand".to_owned(),
            },
        }
    }

    /// Whether the evaluation budget is spent.
    pub(crate) fn exhausted(&self) -> bool {
        self.steps.get() > self.wired.budget
    }

    /// Evaluates condition `id` under `env`; Unknown once the budget is spent.
    pub(crate) fn eval(&self, id: OpId, env: &mut Env) -> Verdict {
        self.steps.set(self.steps.get() + 1);
        if self.exhausted() {
            return Verdict::unknown(Doubt::StepBudget);
        }
        self.eval_op(id, env)
    }

    /// The first member of `kind` in location order whose body `cond` has the truth `want`
    /// under `env` (grl-spec.md 7.0.5 witnesses).
    pub(crate) fn witness(
        &self,
        var: VarId,
        kind: StrId,
        cond: OpId,
        want: Truth,
        env: &mut Env,
    ) -> Option<NodeId> {
        if self.wired.row_kinds.contains(&kind) {
            return None;
        }
        let mut found = None;
        for &(n, member) in self.domain(kind).iter() {
            env[usize::from(var)] = Some(Val::Node(n));
            if self.eval(cond, env).truth & member == want {
                found = Some(n);
                break;
            }
        }
        env[usize::from(var)] = None;
        found
    }

    /// `and`: short-circuits on the first certain `no`.
    fn conjunction(&self, cs: &[OpId], env: &mut Env) -> Verdict {
        let mut acc = Verdict::yes();
        for &c in cs {
            acc = acc.and(self.eval(c, env));
            if acc.truth == Truth::No {
                break;
            }
        }
        acc
    }

    /// `or`: short-circuits on the first certain `yes`.
    fn disjunction(&self, cs: &[OpId], env: &mut Env) -> Verdict {
        let mut acc = Verdict::no();
        for &c in cs {
            acc = acc.or(self.eval(c, env));
            if acc.truth == Truth::Yes {
                break;
            }
        }
        acc
    }

    /// Evaluates a verb edge between two bound variables (`owned by`, `peer of`, or a graph edge).
    fn verb_op(
        &self,
        (subject, object, verb): (VarId, VarId, StrId),
        certainty: Certainty,
        env: &Env,
    ) -> Verdict {
        if self.string(verb) == OWNED_BY {
            return self.owned_by(env, subject, object);
        }
        let (a, b) = (Self::node(env, subject), Self::node(env, object));
        if self.string(verb) == PEER_OF {
            return Verdict::certain(self.peer_of(a, b));
        }
        relations::verb(self.wired.edges[&verb], a, b, certainty)
    }

    fn eval_op(&self, id: OpId, env: &mut Env) -> Verdict {
        match &self.plan.ops[id as usize] {
            Op::And(cs) => self.conjunction(cs, env),
            Op::Or(cs) => self.disjunction(cs, env),
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
                let (l, r) = (
                    self.side(id, false, lhs, env),
                    self.side(id, true, rhs, env),
                );
                Verdict::of(compare(*op, &l, &r), || {
                    if *l == Datum::Unknown {
                        self.describe(lhs, env)
                    } else {
                        self.describe(rhs, env)
                    }
                })
            }
            Op::MatchRegex { subject, .. }
            | Op::MatchGlob { subject, .. }
            | Op::MatchGlobSet { subject, .. } => self.matches(id, subject, env),
            Op::MatchSnippet { var, within, .. } => self.snippet_op(id, *var, *within, env),
            op @ (Op::Is { .. }
            | Op::Exists { .. }
            | Op::HasAttr { .. }
            | Op::Under { .. }
            | Op::MatchGlobOperand { .. }
            | Op::InVocab { .. }
            | Op::InUnit { .. }) => self.predicate_op(op, env),
            Op::CountCmp {
                var,
                kind,
                cond,
                op,
                limit,
            } => {
                let n = self.count(*var, *kind, *cond, env);
                let limit = match *limit {
                    Limit::Int(n) => Count::exactly(n),
                    Limit::Knob { name, default } => {
                        self.wired.knobs.limit(self.string(name), default)
                    }
                };
                Verdict::of(n.compare(*op, &limit), || Doubt::CountBounds {
                    lo: n.lo,
                    hi: n.hi,
                })
            }
            Op::CountPair { lhs, op, rhs } => {
                let l = self.count(lhs.var, lhs.kind, lhs.cond, env);
                let r = self.count(rhs.var, rhs.kind, rhs.cond, env);
                Verdict::of(l.compare_scaled(lhs.scale, *op, &r, rhs.scale), || {
                    Doubt::CountBounds { lo: l.lo, hi: l.hi }
                })
            }
            Op::Call { def, args } => self.call(*def, args, env),
            Op::Verb {
                subject,
                object,
                verb,
                certainty,
            } => self.verb_op((*subject, *object, *verb), *certainty, env),
            Op::Reaches {
                from,
                to,
                via,
                within,
                certainty,
            } => {
                let (a, b) = (Self::node(env, *from), self.unit_of(Self::node(env, *to)));
                let rel = self.wired.edges[via];
                let key = (*via, a, *within);
                let cached = self.closures.borrow().get(&key).map(Rc::clone);
                let closure = cached.unwrap_or_else(|| {
                    let c = Rc::new(relations::Closure::of(rel, a, *within));
                    self.closures.borrow_mut().insert(key, Rc::clone(&c));
                    c
                });
                relations::reaches_in(&closure, a, b, *within, *certainty)
            }
            Op::Find { .. } | Op::FindSide { .. } => {
                unreachable!("binders are clauses, enumerated by the run")
            }
        }
    }

    /// The number of def views computed so far.
    pub(crate) fn view_count(&self) -> usize {
        self.views.borrow().len()
    }

    /// `d(args)`: the def's view at the argument values, computed once per distinct arguments.
    fn call(&self, def: u16, args: &[VarId], env: &Env) -> Verdict {
        let vals: Vec<Val> = args
            .iter()
            .map(|&a| env[usize::from(a)].expect("validated plans use only bound variables"))
            .collect();
        let key = (def, vals);
        if let Some(v) = self.views.borrow().get(&key) {
            return v.clone();
        }
        let d = &self.plan.defs[usize::from(def)];
        let mut inner: Env = vec![None; usize::from(self.plan.vars)];
        for (&p, &v) in d.params.iter().zip(&key.1) {
            inner[usize::from(p)] = Some(v);
        }
        let v = self.eval(d.body, &mut inner);
        tracing::trace!(def, truth = ?v.truth, "def view computed");
        self.views.borrow_mut().insert(key, v.clone());
        v
    }

    /// The unit a closure target stands for: the node itself if it is a unit, else the nearest
    /// enclosing unit (`f reaches call(...)` ends at the unit containing the call, 7.1).
    fn unit_of(&self, node: NodeId) -> NodeId {
        if let Some(&u) = self.units.borrow().get(&node) {
            return u;
        }
        let model = self.rd.model;
        let unit = std::iter::once(node)
            .chain(model.term().ancestors(node))
            .find(|&n| is_canonical_unit(model, n))
            .unwrap_or(node);
        self.units.borrow_mut().insert(node, unit);
        unit
    }

    /// The (first, last) line of `n`'s text span, cached per node; None without text or lines.
    fn line_span(&self, n: NodeId, r: gob_text::TextRange) -> Option<(u32, u32)> {
        if let Some(Some(s)) = self.spans.borrow().get(n.index()) {
            return *s;
        }
        let last = if r.is_empty() {
            r.start()
        } else {
            gob_text::TextSize::new(u32::from(r.end()) - 1)
        };
        let line = |o| self.rd.source.and_then(|s| s.line_col(o)).map(|lc| lc.line);
        let span = line(r.start()).zip(line(last));
        self.spans.borrow_mut()[n.index()] = Some(span);
        span
    }

    /// `a peer of b`: distinct nodes under the same nearest enclosing unit (or both at the top).
    fn peer_of(&self, a: NodeId, b: NodeId) -> bool {
        let model = self.rd.model;
        let up = |n: NodeId| {
            model
                .term()
                .ancestors(n)
                .into_iter()
                .find(|&p| is_canonical_unit(model, p))
        };
        a != b && up(a) == up(b)
    }

    /// `count(var: kind where cond)` under `env`: the interval of satisfying members (7.0.2).
    ///
    /// `lo` counts members whose membership and condition are both Yes; `hi` those for which
    /// neither is No; `hi` is unbounded when the model has unread regions.
    pub(crate) fn count(&self, var: VarId, kind: StrId, cond: OpId, env: &mut Env) -> Count {
        let (mut lo, mut hi) = (0u64, 0u64);
        if self.wired.row_kinds.contains(&kind) {
            for index in 0..self.side_rows(kind) {
                env[usize::from(var)] = Some(Val::Row(SideRow { table: kind, index }));
                let t = self.eval(cond, env).truth;
                lo += u64::from(t == Truth::Yes);
                hi += u64::from(t != Truth::No);
            }
            env[usize::from(var)] = None;
            return Count { lo, hi: Some(hi) };
        }
        for &(n, member) in self.domain(kind).iter() {
            env[usize::from(var)] = Some(Val::Node(n));
            let t = self.eval(cond, env).truth & member;
            lo += u64::from(t == Truth::Yes);
            hi += u64::from(t != Truth::No);
        }
        env[usize::from(var)] = None;
        Count {
            lo,
            hi: (!self.hidden).then_some(hi),
        }
    }

    /// `some var: kind where cond`: the `or` over the domain, plus the hidden-member disjunct.
    fn some(&self, var: VarId, kind: StrId, cond: OpId, env: &mut Env) -> Verdict {
        let mut acc = Verdict::no();
        if self.wired.row_kinds.contains(&kind) {
            for index in 0..self.side_rows(kind) {
                env[usize::from(var)] = Some(Val::Row(SideRow { table: kind, index }));
                acc = acc.or(self.eval(cond, env));
                if acc.truth == Truth::Yes {
                    break;
                }
            }
            env[usize::from(var)] = None;
            return acc;
        }
        let domain = self.domain(kind);
        let visit = self.candidates(var, cond, &domain, env);
        let count = visit.as_ref().map_or(domain.len(), Vec::len);
        for i in 0..count {
            let pos = visit.as_ref().map_or(i, |v| v[i] as usize);
            let (n, member) = domain[pos];
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

    /// `u owned by n`: the file of `u` matches a selector `n` owns in the model; Unknown when the
    /// path or the node's name is not readable.
    ///
    /// frob:ticket 01M5ETB7SWJPH7EVK97WHEVEHY
    fn owned_by(&self, env: &Env, subject: VarId, object: VarId) -> Verdict {
        let node = Self::node(env, subject);
        let Some(Val::Row(row)) = env[usize::from(object)] else {
            unreachable!("validated plans bind the owner of `owned by` as a model node row")
        };
        let name = self.wired.side[&row.table].cell(row.index, "name");
        let (Datum::Known(Scalar::Str(path)), Datum::Known(Scalar::Str(name))) =
            (self.rd.field(node, "path"), name)
        else {
            return Verdict::unknown(Doubt::Dynamic {
                node: Some(node),
                field: "path".to_owned(),
            });
        };
        Verdict::certain(
            self.wired
                .owners
                .get(&name)
                .is_some_and(|g| g.is_match(&path)),
        )
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
            Position::Adjoins => match (self.line_span(a, *ra), self.line_span(b, *rb)) {
                (Some((sa, ea)), Some((sb, eb))) => {
                    let near = |end: u32, start: u32| end == start || end + 1 == start;
                    Verdict::certain(near(ea, sb) || near(eb, sa))
                }
                _ => Verdict::unknown(Doubt::Dynamic {
                    node: Some(a),
                    field: "line".to_owned(),
                }),
            },
        }
    }

    /// `var is` a snippet: the node's span is exactly a pattern match; Unknown when the file
    /// text is missing, does not parse, or the node has no text location.
    fn snippet_op(&self, id: OpId, var: VarId, within: bool, env: &Env) -> Verdict {
        let node = Self::node(env, var);
        let unknown = |field: &str| {
            Verdict::unknown(Doubt::Dynamic {
                node: Some(node),
                field: field.to_owned(),
            })
        };
        let cached = self.snippets.borrow().get(&id).map(Rc::clone);
        let found = cached.unwrap_or_else(|| {
            let ranges = self.rd.source.and_then(|s| {
                let Matcher::Snippet(p) = &self.matchers[&id] else {
                    unreachable!("prepared as a snippet");
                };
                match p.find(s.as_str()) {
                    Ok(ms) => Some(ms.into_iter().map(|m| m.range).collect::<Vec<_>>()),
                    Err(e) => {
                        tracing::warn!(error = %e, "snippet pattern could not scan the file");
                        None
                    }
                }
            });
            tracing::debug!(
                op = id,
                matches = ranges.as_ref().map(Vec::len),
                "snippet scanned"
            );
            let rc = Rc::new(ranges);
            self.snippets.borrow_mut().insert(id, Rc::clone(&rc));
            rc
        });
        let Some(ranges) = found.as_ref() else {
            return unknown("text");
        };
        match self.rd.model.term().node(node).location() {
            Location::Text { range, .. } => {
                let r = u32::from(range.start()) as usize..u32::from(range.end()) as usize;
                Verdict::certain(if within {
                    ranges.iter().any(|m| m.start <= r.start && r.end <= m.end)
                } else {
                    ranges.contains(&r)
                })
            }
            _ => unknown("location"),
        }
    }

    fn matches(&self, id: OpId, subject: &Operand, env: &Env) -> Verdict {
        let test = |s: &str| match &self.matchers[&id] {
            Matcher::Regex(r) => r.is_match(s),
            Matcher::Glob(g) => g.is_match(s),
            Matcher::Set(g) => g.is_match(s),
            Matcher::Snippet(_) => unreachable!("a snippet op tests a node, not a string"),
        };
        // frob:ticket 01M5C7AA29V08HTNZM0BA2A6ST
        // `x.text` of a comment, literal or reference is matched in place, not copied.
        if let Operand::Field(v, f) = *subject
            && self.string(f) == "text"
            && let Some(Val::Node(n)) = env[usize::from(v)]
            && let Some(s) = self.rd.text_str(n)
        {
            return Verdict::certain(test(s));
        }
        let d = self.datum(subject, env);
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
