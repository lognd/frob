//! COH001 "independent jobs" (cohesion.md 1.1): slice a unit's top-level statements into
//! connected components over the def-use edges, once with every edge (`lo`, May merged) and once
//! with Must edges only (`hi`), and judge the pair.
//!
//! Granularity is the unit's top-level statement: a compound statement (`if`, `for`, `try`) is
//! one node holding its condition and body, which makes every inner statement control-dependent
//! on it and keeps the analysis conservative (coarser nodes only merge components, so the rule
//! can miss a split but never invents one). Parameters glue nothing; trivial statements are
//! removed with their edges before counting; components below `min_slice_statements` do not count.

// frob:ticket 01M4CXSQB9YJGH0FRSHX5ECTEM

use std::collections::{BTreeMap, BTreeSet};

use gob_ir::{DefUseEdge, GroupOrder, MayCause, NodeId, Operator, Status, Term, Universal};
use gob_symbols::{Folded, def_use_of};
use tracing::{debug, trace};

/// Knobs of COH001 (the `[coh]` table of cohesion.md, defaults here until the table lands).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CohOptions {
    /// A component with fewer top-level statements than this does not count as a job.
    pub min_slice_statements: usize,
    /// Callee or macro names that are trivial (logging, metrics, asserts); such statements are dropped.
    pub trivial: Vec<String>,
}

impl Default for CohOptions {
    fn default() -> Self {
        Self {
            min_slice_statements: 2,
            trivial: [
                "print", "println", "log", "debug", "info", "warn", "error", "trace", "assert",
            ]
            .map(str::to_owned)
            .to_vec(),
        }
    }
}

/// A May edge that joins two otherwise independent jobs: the reason a verdict is Unresolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MayWitness {
    /// The variable or attribute location the edge is about.
    pub var: String,
    /// Why the edge is May.
    pub cause: MayCause,
    /// Statement holding the write.
    pub def: NodeId,
    /// Statement holding the read.
    pub use_site: NodeId,
}

/// The extract-unit edit for one job: the statements to move and the names they take in.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExtractUnit {
    /// The job's statements in source order.
    pub statements: Vec<NodeId>,
    /// Byte ranges of those statements (empty when the artifact has no text spans).
    pub ranges: Vec<(u32, u32)>,
    /// Parameters the job reads: the arguments of the extracted unit.
    pub params: Vec<String>,
}

/// COH001's judgement of one unit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Coh001 {
    /// `lo >= 2`: two jobs in every completion of the May edges; one edit per job.
    Fire {
        /// Components with May edges merged.
        lo: usize,
        /// Components with Must edges only.
        hi: usize,
        /// The extract-unit edit per job (the `lo` components).
        fixes: Vec<ExtractUnit>,
    },
    /// `hi <= 1`: one job even if no May edge held.
    Clean,
    /// `lo < 2 < hi + 1`: the May edges decide; they are the witnesses.
    Unresolved {
        /// Components with May edges merged.
        lo: usize,
        /// Components with Must edges only.
        hi: usize,
        /// The May edges that join Must components.
        witnesses: Vec<MayWitness>,
    },
}

struct Union(Vec<usize>);

impl Union {
    fn new(n: usize) -> Self {
        Self((0..n).collect())
    }
    fn find(&mut self, x: usize) -> usize {
        let p = self.0[x];
        if p == x {
            return x;
        }
        let r = self.find(p);
        self.0[x] = r;
        r
    }
    fn join(&mut self, a: usize, b: usize) {
        let (a, b) = (self.find(a), self.find(b));
        self.0[a.max(b)] = a.min(b);
    }
}

fn is_let(term: &Term, id: NodeId) -> bool {
    matches!(term.node(id).op(), Operator::Universal(Universal::Bind { kind, .. }) if kind == "let")
}

fn is_punct(term: &Term, id: NodeId) -> bool {
    matches!(
        term.node(id).op(),
        Operator::Universal(Universal::Lit { .. })
    )
}

fn flatten(term: &Term, list: NodeId, out: &mut Vec<NodeId>) {
    for &c in term.node(list).children() {
        if is_let(term, c) {
            if let [scope, rhs, ..] = term.node(c).children() {
                if matches!(
                    term.node(*scope).op(),
                    Operator::Universal(Universal::Group { .. })
                ) {
                    flatten(term, *scope, out);
                } else {
                    out.push(*scope);
                }
                out.push(*rhs);
            }
        } else if !is_punct(term, c) {
            out.push(c);
        }
    }
}

/// The unit's top-level statements, Rust `let` chains flattened, sorted by node id.
pub(crate) fn statements(term: &Term, unit: NodeId) -> Vec<NodeId> {
    let body = term.node(unit).children().iter().rev().copied().find(|&c| {
        matches!(
            term.node(c).op(),
            Operator::Universal(Universal::Group {
                order: GroupOrder::Sequence
            })
        )
    });
    let mut out = Vec::new();
    if let Some(b) = body {
        flatten(term, b, &mut out);
    }
    out.sort();
    out.dedup();
    out
}

fn statement_of(term: &Term, stmts: &BTreeMap<NodeId, usize>, mut n: NodeId) -> Option<usize> {
    if is_let(term, n) {
        n = *term.node(n).children().get(1)?;
    }
    loop {
        if let Some(&i) = stmts.get(&n) {
            return Some(i);
        }
        n = term.node(n).parent()?;
    }
}

/// True for a statement that only hands values out (`return`, or a Rust tail expression): it is an
/// output, so each returned component belongs to its own slice and the statement joins none.
fn is_exit(term: &Term, stmt: NodeId, last: bool) -> bool {
    match term.node(stmt).op() {
        Operator::Adapter(a) => {
            a.name == "return_statement"
                || (last && !a.name.ends_with("_statement") && !a.name.ends_with("_declaration"))
        }
        Operator::Universal(Universal::Ref { .. } | Universal::Lit { .. }) => last,
        Operator::Universal(_) => false,
    }
}

fn mentions(term: &Term, n: NodeId, names: &[String]) -> bool {
    let name = match term.node(n).op() {
        Operator::Universal(Universal::Ref { name }) => Some(name.as_str()),
        Operator::Universal(Universal::Lit { kind, lexeme }) if kind == "identifier" => {
            Some(lexeme.as_str())
        }
        _ => None,
    };
    name.is_some_and(|s| names.iter().any(|t| t == s.trim_end_matches('!')))
        || term
            .node(n)
            .children()
            .iter()
            .any(|&c| mentions(term, c, names))
}

fn count(comps: &mut Union, live: &[usize], min: usize) -> (usize, BTreeMap<usize, Vec<usize>>) {
    let mut groups: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for &i in live {
        groups.entry(comps.find(i)).or_default().push(i);
    }
    let jobs = groups.values().filter(|g| g.len() >= min).count();
    (jobs, groups)
}

/// Judge `unit` of `folded` (language tag `lang`); `None` when def-use does not support the language.
pub fn coh001(folded: &Folded, lang: &str, unit: NodeId, opts: &CohOptions) -> Option<Coh001> {
    let edges = def_use_of(folded, lang, unit)?;
    Some(judge(&folded.term, unit, &edges, opts))
}

/// Judge a unit from precomputed def-use edges (the pure core of [`coh001`]).
pub fn judge(term: &Term, unit: NodeId, edges: &[DefUseEdge], opts: &CohOptions) -> Coh001 {
    let stmts = statements(term, unit);
    let index: BTreeMap<NodeId, usize> = stmts.iter().enumerate().map(|(i, &s)| (s, i)).collect();
    // (def stmt, use stmt, edge) for edges between two distinct statements; parameters glue nothing.
    let linked: Vec<(usize, usize, &DefUseEdge)> = edges
        .iter()
        .filter(|e| e.def != unit)
        .filter_map(|e| {
            let d = statement_of(term, &index, e.def)?;
            let u = statement_of(term, &index, e.use_site)?;
            (d != u).then_some((d, u, e))
        })
        .collect();
    let writers: BTreeSet<usize> = linked.iter().map(|&(d, ..)| d).collect();
    let live: Vec<usize> = (0..stmts.len())
        .filter(|&i| !is_exit(term, stmts[i], i + 1 == stmts.len()))
        .filter(|&i| writers.contains(&i) || !mentions(term, stmts[i], &opts.trivial))
        .collect();
    let live_set: BTreeSet<usize> = live.iter().copied().collect();
    let mut must = Union::new(stmts.len());
    let mut may = Union::new(stmts.len());
    for &(d, u, e) in &linked {
        if !live_set.contains(&d) || !live_set.contains(&u) {
            continue;
        }
        may.join(d, u);
        if e.strength == Status::Must {
            must.join(d, u);
        }
    }
    let (lo, may_groups) = count(&mut may, &live, opts.min_slice_statements);
    let (hi_raw, _) = count(&mut must, &live, opts.min_slice_statements);
    let hi = hi_raw.max(lo);
    debug!(unit = ?unit, statements = stmts.len(), lo, hi, "coh001 components");
    if lo >= 2 {
        let fixes = may_groups
            .values()
            .filter(|g| g.len() >= opts.min_slice_statements)
            .map(|g| extract_unit(term, unit, &stmts, g, edges))
            .collect();
        return Coh001::Fire { lo, hi, fixes };
    }
    if hi <= 1 {
        return Coh001::Clean;
    }
    let mut witnesses = Vec::new();
    for &(d, u, e) in &linked {
        let (Some(cause), true) = (e.cause, live_set.contains(&d) && live_set.contains(&u)) else {
            continue;
        };
        if e.strength != Status::Must && must.find(d) != must.find(u) {
            trace!(var = %e.var, "coh001 witness");
            witnesses.push(MayWitness {
                var: e.var.clone(),
                cause,
                def: stmts[d],
                use_site: stmts[u],
            });
        }
    }
    witnesses.sort_by(|a, b| (a.def, a.use_site, &a.var).cmp(&(b.def, b.use_site, &b.var)));
    witnesses.dedup();
    Coh001::Unresolved { lo, hi, witnesses }
}

fn extract_unit(
    term: &Term,
    unit: NodeId,
    stmts: &[NodeId],
    group: &[usize],
    edges: &[DefUseEdge],
) -> ExtractUnit {
    let statements: Vec<NodeId> = group.iter().map(|&i| stmts[i]).collect();
    let inside = |n: NodeId| statements.iter().any(|&s| s == n || is_within(term, n, s));
    let params: BTreeSet<String> = edges
        .iter()
        .filter(|e| e.def == unit && inside(e.use_site))
        .map(|e| e.var.clone())
        .collect();
    let ranges = statements
        .iter()
        .filter_map(|&s| term.node(s).location().span())
        .map(|sp| (u32::from(sp.range.start()), u32::from(sp.range.end())))
        .collect();
    ExtractUnit {
        statements,
        ranges,
        params: params.into_iter().collect(),
    }
}

fn is_within(term: &Term, mut n: NodeId, ancestor: NodeId) -> bool {
    while let Some(p) = term.node(n).parent() {
        if p == ancestor {
            return true;
        }
        n = p;
    }
    false
}
