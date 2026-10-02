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
use gob_rules::Finding;
use gob_symbols::{CallEdge, SymbolGraph, SymbolKind, SymbolRecord, Symref};
use gob_text::{FileInterner, Span};

use crate::rules::Cov001;
use crate::util::finding;

/// True for functions and methods.
fn is_callable(rec: &SymbolRecord) -> bool {
    matches!(rec.kind, SymbolKind::Function | SymbolKind::Method)
}

/// Number of functions and methods in `graph`: the subjects `COV001` looks at.
pub(crate) fn callables(graph: &SymbolGraph) -> usize {
    graph.records().filter(|r| is_callable(r)).count()
}

/// Forward call adjacency: graph edges plus unique-name edges found in function bodies.
fn adjacency(graph: &SymbolGraph, sources: &mut Sources) -> HashMap<Symref, Vec<Symref>> {
    let mut adj: HashMap<Symref, Vec<Symref>> = HashMap::new();
    for edge in graph.call_edges() {
        match edge {
            CallEdge::Resolved { caller, callee } => {
                adj.entry(caller.clone()).or_default().push(callee.clone());
            }
            CallEdge::Ambiguous { caller, candidates } => {
                adj.entry(caller.clone())
                    .or_default()
                    .extend(candidates.iter().cloned());
            }
            CallEdge::Unresolved { .. } => {}
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
    let adj = adjacency(graph, &mut sources);
    let mut reached: HashSet<Symref> = HashSet::new();
    let mut queue: VecDeque<Symref> = tests.iter().cloned().collect();
    while let Some(s) = queue.pop_front() {
        if !reached.insert(s.clone()) {
            continue;
        }
        queue.extend(adj.get(&s).into_iter().flatten().cloned());
    }
    let covered = declared(graph, directives);
    tracing::debug!(
        tests = tests.len(),
        reached = reached.len(),
        declared = covered.len(),
        "COV001 reach computed"
    );
    let mut out = Vec::new();
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
        out.push(finding(
            &Cov001,
            Some(Span::new(file, rec.span)),
            format!(
                "public {} `{}` is reached by no test; add one or bind it with `frob:tests`",
                format!("{:?}", rec.kind).to_lowercase(),
                rec.symref
            ),
            &rec.symref.to_string(),
        ));
    }
    out
}
