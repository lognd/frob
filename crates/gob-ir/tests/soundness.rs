//! Property tests that try to falsify Theorems 2 (adequacy) and 3 (honesty) of universal-model.md.
//!
//! Layer A draws a random lo/hi relation (certain edges, possible edges, and nodes with an
//! Unknown outgoing edge), Layer B draws a random term whose call sites resolve Must, May,
//! Unknown or through a non-name head and reads the relation back through `Ctx::rel_calls`.
//! Both evaluate random formulas (atoms, not/and/or, some/no, count against k, bounded and
//! unbounded reach) in Kleene logic and compare every definite answer with the classical answer
//! in every sampled completion (soundness); structures with no May or Unknown part must never
//! yield Unknown (exactness). Formal review 2026-10-08 section 4 item 8.
#![allow(clippy::many_single_char_names, reason = "terse generators")]

mod support;

use gob_ir::{AttrValue, Ctx, Model, NodeId, Operator, Relation, Truth, reserved};
use proptest::prelude::*;
use support::B;

const MAX_N: usize = 5;
const WITHIN: usize = 3;

#[derive(Debug, Clone, Copy)]
enum Cmp {
    Eq,
    Ge,
    Le,
}

/// The formula grammar; variables index the quantifier environment modulo its length.
#[derive(Debug, Clone)]
enum F {
    Edge(usize, usize),
    Reach(usize, usize),
    Within(usize, usize, usize),
    Not(Box<F>),
    And(Box<F>, Box<F>),
    Or(Box<F>, Box<F>),
    Some(Box<F>),
    No(Box<F>),
    Count(usize, Cmp, usize),
}

fn formula() -> impl Strategy<Value = F> {
    let leaf = prop_oneof![
        (0..4usize, 0..4usize).prop_map(|(a, b)| F::Edge(a, b)),
        (0..4usize, 0..4usize).prop_map(|(a, b)| F::Reach(a, b)),
        (1..=WITHIN, 0..4usize, 0..4usize).prop_map(|(k, a, b)| F::Within(k, a, b)),
        (
            0..4usize,
            prop_oneof![Just(Cmp::Eq), Just(Cmp::Ge), Just(Cmp::Le)],
            0..4usize
        )
            .prop_map(|(x, c, k)| F::Count(x, c, k)),
    ];
    leaf.prop_recursive(4, 24, 2, |inner| {
        prop_oneof![
            inner.clone().prop_map(|f| F::Not(Box::new(f))),
            (inner.clone(), inner.clone()).prop_map(|(a, b)| F::And(Box::new(a), Box::new(b))),
            (inner.clone(), inner.clone()).prop_map(|(a, b)| F::Or(Box::new(a), Box::new(b))),
            inner.clone().prop_map(|f| F::Some(Box::new(f))),
            inner.prop_map(|f| F::No(Box::new(f))),
        ]
    })
}

fn cmp_k3(c: Cmp, lo: usize, hi: usize, k: usize) -> Truth {
    match c {
        Cmp::Eq if lo == hi && lo == k => Truth::Yes,
        Cmp::Eq if k < lo || k > hi => Truth::No,
        Cmp::Ge if lo >= k => Truth::Yes,
        Cmp::Ge if hi < k => Truth::No,
        Cmp::Le if hi <= k => Truth::Yes,
        Cmp::Le if lo > k => Truth::No,
        _ => Truth::Unknown,
    }
}

/// The Kleene reading of a relation: edge, closure and bounded-reach relations.
struct K3 {
    ids: Vec<NodeId>,
    edge: Relation,
    reach: Relation,
    within: Vec<Relation>,
}

impl K3 {
    fn new(ids: Vec<NodeId>, edge: Relation) -> Self {
        let reach = edge.closure();
        let mut within = Vec::new();
        let (mut acc, mut cur) = (edge.clone(), edge.clone());
        within.push(acc.clone());
        for _ in 1..WITHIN {
            cur = cur.compose(&edge);
            acc = acc.union(&cur);
            within.push(acc.clone());
        }
        Self {
            ids,
            edge,
            reach,
            within,
        }
    }

    fn eval(&self, f: &F, env: &mut Vec<usize>) -> Truth {
        let v = |env: &[usize], i: usize| self.ids[env[i % env.len()]];
        match f {
            F::Edge(a, b) => self.edge.get(v(env, *a), v(env, *b)),
            F::Reach(a, b) => self.reach.get(v(env, *a), v(env, *b)),
            F::Within(k, a, b) => self.within[k - 1].get(v(env, *a), v(env, *b)),
            F::Not(g) => !self.eval(g, env),
            F::And(a, b) => self.eval(a, env) & self.eval(b, env),
            F::Or(a, b) => self.eval(a, env) | self.eval(b, env),
            F::Some(g) => self.quantify(g, env),
            F::No(g) => !self.quantify(g, env),
            F::Count(x, c, k) => {
                let xn = v(env, *x);
                let (mut lo, mut hi) = (0, 0);
                for &y in &self.ids {
                    match self.edge.get(xn, y) {
                        Truth::Yes => {
                            lo += 1;
                            hi += 1;
                        }
                        Truth::Unknown => hi += 1,
                        Truth::No => {}
                    }
                }
                cmp_k3(*c, lo, hi, *k)
            }
        }
    }

    fn quantify(&self, g: &F, env: &mut Vec<usize>) -> Truth {
        let mut out = Truth::No;
        for i in 0..self.ids.len() {
            env.push(i);
            out = out | self.eval(g, env);
            env.pop();
        }
        out
    }
}

/// The classical reading of one completion: a plain adjacency matrix.
struct Classical {
    n: usize,
    adj: Vec<Vec<bool>>,
    reach: Vec<Vec<bool>>,
    within: Vec<Vec<Vec<bool>>>,
}

fn mul(a: &[Vec<bool>], b: &[Vec<bool>]) -> Vec<Vec<bool>> {
    let n = a.len();
    (0..n)
        .map(|i| (0..n).map(|j| (0..n).any(|m| a[i][m] && b[m][j])).collect())
        .collect()
}

fn or(a: &[Vec<bool>], b: &[Vec<bool>]) -> Vec<Vec<bool>> {
    a.iter()
        .zip(b)
        .map(|(r, s)| r.iter().zip(s).map(|(x, y)| *x || *y).collect())
        .collect()
}

impl Classical {
    fn new(adj: Vec<Vec<bool>>) -> Self {
        let n = adj.len();
        let mut reach = adj.clone();
        for _ in 0..n {
            reach = or(&reach, &mul(&reach, &adj));
        }
        let mut within = vec![adj.clone()];
        let (mut acc, mut cur) = (adj.clone(), adj.clone());
        for _ in 1..WITHIN {
            cur = mul(&cur, &adj);
            acc = or(&acc, &cur);
            within.push(acc.clone());
        }
        Self {
            n,
            adj,
            reach,
            within,
        }
    }

    fn eval(&self, f: &F, env: &mut Vec<usize>) -> bool {
        let v = |env: &[usize], i: usize| env[i % env.len()];
        match f {
            F::Edge(a, b) => self.adj[v(env, *a)][v(env, *b)],
            F::Reach(a, b) => self.reach[v(env, *a)][v(env, *b)],
            F::Within(k, a, b) => self.within[k - 1][v(env, *a)][v(env, *b)],
            F::Not(g) => !self.eval(g, env),
            F::And(a, b) => self.eval(a, env) && self.eval(b, env),
            F::Or(a, b) => self.eval(a, env) || self.eval(b, env),
            F::Some(g) => self.quantify(g, env),
            F::No(g) => !self.quantify(g, env),
            F::Count(x, c, k) => {
                let xn = v(env, *x);
                let cnt = self.adj[xn].iter().filter(|b| **b).count();
                match c {
                    Cmp::Eq => cnt == *k,
                    Cmp::Ge => cnt >= *k,
                    Cmp::Le => cnt <= *k,
                }
            }
        }
    }

    fn quantify(&self, g: &F, env: &mut Vec<usize>) -> bool {
        (0..self.n).any(|i| {
            env.push(i);
            let r = self.eval(g, env);
            env.pop();
            r
        })
    }
}

/// Check the soundness clause against every completion and, when `closed`, exactness.
fn check(
    k3: &K3,
    completions: &[Classical],
    f: &F,
    free: &[usize],
    closed: bool,
) -> Result<(), TestCaseError> {
    let t = k3.eval(f, &mut free.to_vec());
    if closed {
        prop_assert_ne!(
            t,
            Truth::Unknown,
            "closed structure answered Unknown: {:?}",
            f
        );
    }
    for c in completions {
        let b = c.eval(f, &mut free.to_vec());
        match t {
            Truth::Yes => prop_assert!(b, "Yes but a completion says No: {:?}", f),
            Truth::No => prop_assert!(!b, "No but a completion says Yes: {:?}", f),
            Truth::Unknown => {}
        }
    }
    Ok(())
}

fn bits() -> impl Strategy<Value = Vec<bool>> {
    prop::collection::vec(prop::bool::weighted(0.3), 64)
}

fn free_vars() -> impl Strategy<Value = Vec<usize>> {
    prop::collection::vec(0..MAX_N, 2..=3)
}

/// Layer A edge kinds: 0 Must, 1 May.
#[derive(Debug, Clone)]
struct SpecA {
    n: usize,
    edges: Vec<(usize, usize, bool)>,
    frontier: Vec<usize>,
}

fn spec_a(closed: bool) -> impl Strategy<Value = SpecA> {
    (2..=MAX_N).prop_flat_map(move |n| {
        (
            Just(n),
            prop::collection::vec((0..n, 0..n, any::<bool>()), 0..8),
            prop::collection::vec(0..n, 0..3),
        )
            .prop_map(move |(n, edges, frontier)| SpecA {
                n,
                edges: edges
                    .into_iter()
                    .map(|(a, b, may)| (a, b, may && !closed))
                    .collect(),
                frontier: if closed { Vec::new() } else { frontier },
            })
    })
}

fn lit_ids() -> Vec<NodeId> {
    let mut b = B::new("a.rs", "rust");
    let kids: Vec<NodeId> = (0..MAX_N).map(|i| b.lit(&format!("l{i}"))).collect();
    let root = b.file_unit(&kids);
    let t = b.finish(root);
    kids.iter()
        .map(|k| t.ids().find(|i| i == k).unwrap())
        .collect()
}

fn run_a(
    s: &SpecA,
    seeds: &[Vec<bool>],
    f: &F,
    free: &[usize],
    closed: bool,
) -> Result<(), TestCaseError> {
    let ids = lit_ids()[..s.n].to_vec();
    let mut rel = Relation::new();
    for &(a, b, may) in &s.edges {
        rel.insert(
            ids[a],
            ids[b],
            if may { Truth::Unknown } else { Truth::Yes },
        );
    }
    for &u in &s.frontier {
        rel.mark_unknown_out(ids[u]);
    }
    let k3 = K3::new(ids, rel);
    let comps: Vec<Classical> = seeds
        .iter()
        .map(|seed| {
            let mut adj = vec![vec![false; s.n]; s.n];
            for (e, &(a, b, may)) in s.edges.iter().enumerate() {
                if !may || seed[e % seed.len()] {
                    adj[a][b] = true;
                }
            }
            for &u in &s.frontier {
                for j in 0..s.n {
                    if seed[(8 + u * MAX_N + j) % seed.len()] {
                        adj[u][j] = true;
                    }
                }
            }
            Classical::new(adj)
        })
        .collect();
    let free: Vec<usize> = free.iter().map(|x| x % s.n).collect();
    check(&k3, &comps, f, &free, closed)
}

/// Layer B call-site kinds.
#[derive(Debug, Clone, Copy)]
enum Call {
    Must(usize),
    May(usize),
    Ghost,
    NonRef,
}

#[derive(Debug, Clone)]
struct SpecB {
    n: usize,
    calls: Vec<Vec<Call>>,
}

fn spec_b(closed: bool) -> impl Strategy<Value = SpecB> {
    (2..=MAX_N).prop_flat_map(move |n| {
        let call = if closed {
            (0..n).prop_map(Call::Must).boxed()
        } else {
            prop_oneof![
                4 => (0..n).prop_map(Call::Must),
                2 => (0..n).prop_map(Call::May),
                1 => Just(Call::Ghost),
                1 => Just(Call::NonRef),
            ]
            .boxed()
        };
        (
            Just(n),
            prop::collection::vec(prop::collection::vec(call, 0..3), n),
        )
            .prop_map(|(n, calls)| SpecB { n, calls })
    })
}

/// The status each call site really gets: a May opaque hint downgrades every call to that name.
fn normalise(s: &SpecB) -> Vec<Vec<Call>> {
    s.calls
        .iter()
        .map(|cs| {
            let may: Vec<usize> = cs
                .iter()
                .filter_map(|c| if let Call::May(j) = c { Some(*j) } else { None })
                .collect();
            cs.iter()
                .map(|c| match c {
                    Call::Must(j) if may.contains(j) => Call::May(*j),
                    other => *other,
                })
                .collect()
        })
        .collect()
}

fn build_b(s: &SpecB) -> (Model, Vec<NodeId>) {
    let mut b = B::new("c.rs", "rust");
    let mut units = Vec::new();
    for (i, cs) in s.calls.iter().enumerate() {
        let mut kids = Vec::new();
        let mut hinted = Vec::new();
        for c in cs {
            match c {
                Call::Must(j) => kids.push(b.call(&format!("f{j}"), &[])),
                Call::May(j) => {
                    if !hinted.contains(j) {
                        hinted.push(*j);
                        let spec = b.spec(Operator::opaque("dynamic:unresolvable", b"x")).attr(
                            reserved::MAY_DEFINE,
                            AttrValue::List(vec![AttrValue::Str(format!("f{j}"))]),
                        );
                        kids.push(b.add(spec, &[]));
                    }
                    kids.push(b.call(&format!("f{j}"), &[]));
                }
                Call::Ghost => kids.push(b.call("ghost", &[])),
                Call::NonRef => {
                    let obj = b.lit("obj");
                    let head = b.node(Operator::apply("member"), &[obj]);
                    kids.push(b.node(Operator::apply("call"), &[head]));
                }
            }
        }
        units.push(b.unit("function", &format!("f{i}"), &[], &kids));
    }
    let root = b.file_unit(&units);
    let m = Model::lexical(b.finish(root));
    let nodes = (0..s.n)
        .map(|i| {
            m.term()
                .units()
                .into_iter()
                .find(|u| u.symref.to_string() == format!("c.rs::f{i}"))
                .unwrap()
                .node
        })
        .collect();
    (m, nodes)
}

fn run_b(
    s: &SpecB,
    seeds: &[Vec<bool>],
    f: &F,
    free: &[usize],
    closed: bool,
) -> Result<(), TestCaseError> {
    let (m, ids) = build_b(s);
    let ctx = Ctx::new(&m);
    let k3 = K3::new(ids, ctx.rel_calls());
    let calls = normalise(s);
    let comps: Vec<Classical> = seeds
        .iter()
        .map(|seed| {
            let mut adj = vec![vec![false; s.n]; s.n];
            let mut site = 0usize;
            for (i, cs) in calls.iter().enumerate() {
                for c in cs {
                    site += 1;
                    let bit = |k: usize| seed[(site * 7 + k) % seed.len()];
                    match c {
                        Call::Must(j) => adj[i][*j] = true,
                        Call::May(j) => adj[i][*j] |= bit(0),
                        Call::Ghost | Call::NonRef => {
                            for (j, cell) in adj[i].iter_mut().enumerate() {
                                *cell |= bit(j + 1);
                            }
                        }
                    }
                }
            }
            Classical::new(adj)
        })
        .collect();
    let free: Vec<usize> = free.iter().map(|x| x % s.n).collect();
    check(&k3, &comps, f, &free, closed)
}

proptest! {
    #![proptest_config(ProptestConfig { failure_persistence: None, cases: 400, ..ProptestConfig::default() })]

    // frob:ticket 01M4CXTWDFFNQ045N7PJVT37ES
    #[test]
    fn relations_are_sound_over_every_completion(
        s in spec_a(false),
        seeds in prop::collection::vec(bits(), 4),
        f in formula(),
        free in free_vars(),
    ) {
        run_a(&s, &seeds, &f, &free, false)?;
    }

    // frob:ticket 01M4CXTWDFFNQ045N7PJVT37ES
    #[test]
    fn closed_relations_are_exact(
        s in spec_a(true),
        f in formula(),
        free in free_vars(),
    ) {
        run_a(&s, &[vec![false; 64]], &f, &free, true)?;
    }

    // frob:ticket 01M4CXTWDFFNQ045N7PJVT37ES
    #[test]
    fn call_graphs_are_sound_over_every_completion(
        s in spec_b(false),
        seeds in prop::collection::vec(bits(), 4),
        f in formula(),
        free in free_vars(),
    ) {
        run_b(&s, &seeds, &f, &free, false)?;
    }

    // frob:ticket 01M4CXTWDFFNQ045N7PJVT37ES
    #[test]
    fn closed_call_graphs_are_exact(
        s in spec_b(true),
        f in formula(),
        free in free_vars(),
    ) {
        run_b(&s, &[vec![false; 64]], &f, &free, true)?;
    }
}
