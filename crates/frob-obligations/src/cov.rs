//! COV001: public functions and methods that no test reaches.
//!
//! Reach is forward from every test function: the resolved and ambiguous call
//! edges of the symbol graph, plus the unique-name call scan that
//! `frob-tests` uses as a backstop for calls the graph cannot see (macro
//! arguments, calls across workspace crates). A `frob:tests` directive naming
//! a symbol covers it as well.

use std::collections::{BTreeSet, HashMap, HashSet, VecDeque};
use std::path::Path;

use frob_tests::catalog::{is_test_file, is_test_fn};
use frob_tests::reach::{Sources, called_names};
use gob_directives::Binding;
use gob_directives::DirectiveRecord;
use gob_languages::Language;
use gob_rules::{Finding, Severity};
use gob_symbols::{
    Admit, CallEdge, CrateDeps, EdgeKind, Status, StatusEdge, SymbolGraph, SymbolKind,
    SymbolRecord, Symref, Target,
};
use gob_text::{FileInterner, Span};

use crate::rules::Cov001;
use crate::util::{finding, rule_id};

/// True for functions and methods.
fn is_callable(rec: &SymbolRecord) -> bool {
    matches!(rec.kind, SymbolKind::Function | SymbolKind::Method)
}

// frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF
/// Number of test-capable source files (Rust, Python and C#) in `graph`: the subjects `COV001` examines.
///
/// Zero while the walk holds Rust files means the graph came up empty, so a
/// clean `COV001` would be silence, not a pass.
pub(crate) fn test_capable_files(graph: &SymbolGraph) -> usize {
    graph
        .records()
        .filter(|r| matches!(r.symref.target(), Target::File))
        .filter(|r| {
            matches!(
                Language::detect(r.symref.path()),
                Some(Language::Rust | Language::Python | Language::CSharp)
            )
        })
        .count()
}

/// Forward call adjacency: graph edges plus unique-name edges found in function bodies.
fn adjacency(
    graph: &SymbolGraph,
    sources: &mut Sources,
    include_ambiguous: bool,
) -> HashMap<Symref, Vec<Symref>> {
    let mut adj: HashMap<Symref, Vec<Symref>> = HashMap::new();
    for edge in graph.call_edges() {
        match edge {
            CallEdge::Resolved { caller, callee } => {
                adj.entry(caller.clone()).or_default().push(callee.clone());
            }
            CallEdge::Ambiguous { caller, candidates } if include_ambiguous => {
                adj.entry(caller.clone())
                    .or_default()
                    .extend(candidates.iter().cloned());
            }
            CallEdge::Ambiguous { .. } | CallEdge::Unresolved { .. } => {}
        }
    }
    let callables: Vec<&SymbolRecord> = graph.records().filter(|r| is_callable(r)).collect();
    let mut by_name: HashMap<&str, Vec<&Symref>> = HashMap::new();
    for r in &callables {
        if let Some(n) = r.symref.name() {
            by_name.entry(n).or_default().push(&r.symref);
        }
    }
    for r in &callables {
        let Some(text) = sources.get(r.symref.path()) else {
            continue;
        };
        let range = usize::try_from(u32::from(r.span.start())).unwrap_or(usize::MAX)
            ..usize::try_from(u32::from(r.span.end())).unwrap_or(usize::MAX);
        let Some(body) = text.get(range) else {
            continue;
        };
        for name in called_names(body) {
            if let Some([only]) = by_name.get(name.as_str()).map(Vec::as_slice)
                && **only != r.symref
            {
                adj.entry(r.symref.clone())
                    .or_default()
                    .push((*only).clone());
            }
        }
    }
    adj
}

/// Symbols that `frob:tests` directives declare covered.
/// Every symbol reachable from `tests` over `adj`, the tests included.
fn reach_of(tests: &BTreeSet<Symref>, adj: &HashMap<Symref, Vec<Symref>>) -> HashSet<Symref> {
    let mut reached: HashSet<Symref> = HashSet::new();
    let mut queue: VecDeque<Symref> = tests.iter().cloned().collect();
    while let Some(s) = queue.pop_front() {
        if !reached.insert(s.clone()) {
            continue;
        }
        queue.extend(adj.get(&s).into_iter().flatten().cloned());
    }
    reached
}

/// An unresolved call in a test's reach that could be a call of some callable.
#[derive(Debug, Clone)]
struct Poison {
    /// True when the call's qualifier pins exactly this callable among the candidates.
    pinned: bool,
    /// The call site: `file:line` and the call text.
    site: String,
    /// What the call's qualifier says, for the message.
    how: String,
}

/// The `file:line: text` call site of `e`, the text in backticks.
fn site_of(e: &StatusEdge) -> String {
    format!(
        "{}:{}: `{}`",
        e.from.path(),
        e.line.unwrap_or(0),
        e.text.as_deref().unwrap_or("?")
    )
}

/// The callables each unresolved call in a test's reach could be, matched on (qualifier, name).
///
/// A qualifier-less call keeps the broad name match; a qualified one only
/// admits callables its qualifier cannot rule out (`SymbolGraph::admits`).
fn poison_map(
    graph: &SymbolGraph,
    tests: &BTreeSet<Symref>,
    by_name: &HashMap<&str, Vec<&SymbolRecord>>,
    deps: &mut CrateDeps,
) -> HashMap<Symref, Poison> {
    let mut poisoned: HashSet<Symref> = HashSet::new();
    for t in tests {
        poisoned.extend(graph.reach_with_status(t, &[EdgeKind::Calls]).poisoned_by);
    }
    let mut out: HashMap<Symref, Poison> = HashMap::new();
    for e in graph
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.status == Status::Unknown)
        .filter(|e| poisoned.contains(&e.from))
    {
        let Some(cands) = e.name.as_deref().and_then(|n| by_name.get(n)) else {
            continue;
        };
        let linked: Vec<&SymbolRecord> = cands
            .iter()
            .copied()
            .filter(|r| deps.file_can_reach(e.from.path(), r.symref.path()))
            .collect();
        let admitted: Vec<(&SymbolRecord, Admit)> = match &e.qualifier {
            None => linked.iter().map(|r| (*r, Admit::Maybe)).collect(),
            Some(q) => linked
                .iter()
                .map(|r| (*r, graph.admits(q, r)))
                .filter(|(_, a)| *a != Admit::No)
                .collect(),
        };
        let only_one = admitted.len() == 1;
        let how = e.qualifier.as_ref().map_or_else(
            || "no qualifier is known".to_owned(),
            gob_symbols::CallQualifier::describe,
        );
        for (rec, a) in admitted {
            let pinned = only_one && a == Admit::Pinned;
            let better = out.get(&rec.symref).is_none_or(|p| pinned && !p.pinned);
            if better {
                out.insert(
                    rec.symref.clone(),
                    Poison {
                        pinned,
                        site: site_of(e),
                        how: how.clone(),
                    },
                );
            }
        }
    }
    tracing::debug!(
        poisoned_callables = out.len(),
        "COV001 qualifier-matched poison"
    );
    out
}

/// For each callable reached only through May edges, the ambiguous call that first made it so.
///
/// Walks forward from every May edge leaving the Must-reached set; callables
/// further down inherit the label of the May edge that started their chain.
fn may_sites<'g>(
    graph: &'g SymbolGraph,
    must: &HashSet<Symref>,
) -> HashMap<&'g Symref, &'g StatusEdge> {
    let mut out: HashMap<&Symref, &StatusEdge> = HashMap::new();
    let mut calls_from: HashMap<&Symref, Vec<&StatusEdge>> = HashMap::new();
    let mut queue: VecDeque<(&Symref, &StatusEdge)> = VecDeque::new();
    for e in graph
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.to.is_some())
    {
        calls_from.entry(&e.from).or_default().push(e);
        if let (Some(to), true) = (&e.to, e.status == Status::May && must.contains(&e.from))
            && !must.contains(to)
            && !out.contains_key(to)
            && e.line.is_some()
        {
            out.insert(to, e);
            queue.push_back((to, e));
        }
    }
    while let Some((n, label)) = queue.pop_front() {
        for e in calls_from.get(n).into_iter().flatten() {
            if let Some(to) = &e.to
                && !must.contains(to)
                && !out.contains_key(to)
            {
                out.insert(to, label);
                queue.push_back((to, label));
            }
        }
    }
    out
}

/// Why `rec` is neither covered nor provably uncovered, naming the ambiguous call site.
fn unresolved_reach(
    rec: &SymbolRecord,
    maybe: &HashSet<Symref>,
    maybe_sites: &HashMap<&Symref, &StatusEdge>,
    poison: &HashMap<Symref, Poison>,
) -> Option<String> {
    if let Some(e) = maybe_sites.get(&rec.symref) {
        return Some(format!(
            "it is reached only through ambiguous (May) calls, e.g. {}",
            site_of(e)
        ));
    }
    if maybe.contains(&rec.symref) {
        return Some("it is reached only through ambiguous (May) calls".to_owned());
    }
    poison.get(&rec.symref).map(|p| {
        let strength = if p.pinned { "names it" } else { "may name it" };
        format!(
            "a test reaches the unresolved call {} that {strength} ({})",
            p.site, p.how
        )
    })
}

fn declared(graph: &SymbolGraph, directives: &[DirectiveRecord]) -> HashSet<Symref> {
    let mut out = HashSet::new();
    for d in directives
        .iter()
        .filter(|d| d.namespace == "frob" && d.verb == "tests")
    {
        if d.source.is_some() {
            let Some(target) = d.args.positional.first() else {
                continue;
            };
            match graph.resolve(&target.value) {
                Ok(r) => {
                    out.insert(r.symref.clone());
                }
                Err(gob_symbols::ResolveError::Ambiguous(c)) => out.extend(c),
                Err(gob_symbols::ResolveError::NotFound(_)) => {}
            }
        } else if let Binding::Symbol(s) = &d.bound {
            out.insert(s.clone());
        }
    }
    out
}

/// COV001 over the repo: public functions and methods with no test reaching them.
pub(crate) fn cov001(
    root: &Path,
    graph: &SymbolGraph,
    directives: &[DirectiveRecord],
    files: &mut FileInterner,
) -> Vec<Finding> {
    let mut sources = Sources::new(root);
    let tests: BTreeSet<Symref> = graph
        .records()
        .filter(|r| {
            let text = sources.get(r.symref.path()).map(str::to_owned);
            is_test_fn(r, text.as_deref())
        })
        .map(|r| r.symref.clone())
        .collect();
    let must = reach_of(&tests, &adjacency(graph, &mut sources, false));
    let maybe = reach_of(&tests, &adjacency(graph, &mut sources, true));
    let mut by_name: HashMap<&str, Vec<&SymbolRecord>> = HashMap::new();
    for r in graph.records().filter(|r| is_callable(r)) {
        if let Some(n) = r.symref.name() {
            by_name.entry(n).or_default().push(r);
        }
    }
    let poison = poison_map(graph, &tests, &by_name, &mut CrateDeps::new(root));
    let reached = must;
    let maybe_sites = may_sites(graph, &reached);
    let covered = declared(graph, directives);
    tracing::debug!(
        tests = tests.len(),
        reached = reached.len(),
        declared = covered.len(),
        "COV001 reach computed"
    );
    let mut out = Vec::new();
    let partial = frob_ack::partial_parse_files(graph);
    if let Some((first, _)) = partial.first() {
        out.push(Finding::new(
            rule_id(&Cov001),
            Severity::Unresolved,
            None,
            format!(
                "{} file(s) parsed partially (first `{first}`); callables inside a parse hole are unseen, so COV001 is undecided for them",
                partial.len()
            ),
            "partial-parse",
        ));
    }
    for rec in graph.public_api() {
        if !is_callable(rec)
            || rec.implements.is_some()
            || is_test_file(rec.symref.path())
            || tests.contains(&rec.symref)
            || reached.contains(&rec.symref)
            || covered.contains(&rec.symref)
        {
            continue;
        }
        let file = files.intern(rec.symref.path());
        let kind = format!("{:?}", rec.kind).to_lowercase();
        if let Some(why) = unresolved_reach(rec, &maybe, &maybe_sites, &poison) {
            tracing::info!(symref = %rec.symref, %why, "COV001 unresolved");
            out.push(Finding::new(
                rule_id(&Cov001),
                Severity::Unresolved,
                Some(Span::new(file, rec.span)),
                format!(
                    "public {kind} `{}`: cannot tell whether a test reaches it, {why}",
                    rec.symref
                ),
                &rec.symref.to_string(),
            ));
            continue;
        }
        out.push(finding(
            &Cov001,
            Some(Span::new(file, rec.span)),
            format!(
                "public {kind} `{}` is reached by no test; add one or bind it with `frob:tests`",
                rec.symref
            ),
            &rec.symref.to_string(),
        ));
    }
    out
}
