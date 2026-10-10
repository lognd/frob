//! SYS013: an import or call edge between two owners with no flow between them.
//!
//! The edges come from the one symbol graph of the snapshot (`gob-symbols`: TS and TSX imports,
//! calls and JSX component uses, Python, C# and Rust calls), the owners from the owner function
//! of binding.md 2.6, and the permission from the model's flows (a flow is directed data movement
//! and code edges run with or against it, so a flow in either direction between two owners allows
//! the edge). Per binding.md 6, a P+ rule fires only
//! from `lo`: both ends owned at Must and the edge itself Must. An edge whose target is Unknown
//! or May, or whose end owner is May or Unknown, is Unresolved and never reads clean.

// frob:ticket 01M48FXAG32KFM90XWVFS8AX88
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067

use std::collections::{BTreeMap, BTreeSet};

use gob_rules::Severity;
use gob_symbols::{CrateDeps, EdgeKind, GapReason, Status as EdgeStatus, StatusEdge, SymbolGraph};
use gob_walk::Owner;
use grimble_model::ast::EntityKind;

use crate::code::Code;
use crate::model::Model;
use crate::rules::{Cx, Output, path_of};
use crate::types::Reason;

/// The rule id.
const RULE: &str = "SYS013";

/// How many example edges one aggregated finding names.
const EXAMPLES: usize = 3;

/// True when the model has two nodes that own code: the only models SYS013 can apply to.
pub fn needs_graph(model: &Model) -> bool {
    model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
        .count()
        >= 2
}

/// Why SYS013 has no subject, or `None` when two code-owning nodes and an edge exist.
pub fn sys013_inapplicable(model: &Model, graph: &SymbolGraph) -> Option<&'static str> {
    if !needs_graph(model) {
        return Some(
            "the model has fewer than two nodes that own code, so no edge can cross owners",
        );
    }
    (!graph.edges_with_status().iter().any(is_subject))
        .then_some("the snapshot has no import or call edge to check")
}

fn is_subject(e: &StatusEdge) -> bool {
    matches!(e.kind, EdgeKind::Imports | EdgeKind::Calls)
}

/// What the owner function says about one end of an edge.
enum End {
    /// Exactly this node owns it.
    Node(String),
    /// Some node may own it, or its file hides what owns it.
    Uncertain,
    /// No node claims it: unchecked (binding.md B6).
    Foreign,
}

fn end_of(cx: &Cx<'_>, symref: &str) -> End {
    if let Some(uo) = cx.owners.units.get(symref) {
        return match &uo.merged.owner {
            Owner::Must(n) => End::Node(n.as_str().to_owned()),
            Owner::Foreign => End::Foreign,
            Owner::May(_) | Owner::Unknown(_) => End::Uncertain,
        };
    }
    match cx.owners.files.get(path_of(symref)) {
        Some(fo) if fo.expanded => End::Uncertain,
        _ => End::Foreign,
    }
}

/// Edges grouped by what they say, before findings are written.
#[derive(Default)]
struct Tally {
    /// Undeclared owner pairs with the edges that cross them.
    crossing: BTreeMap<(String, String), Vec<(String, String)>>,
    /// Unresolved edges per (reason, owner label) with example texts.
    soft: BTreeMap<(&'static str, String), (Reason, usize, Vec<String>)>,
}

impl Tally {
    fn soft(&mut self, reason: Reason, owner: &str, example: String) {
        let e = self
            .soft
            .entry((reason.code(), owner.to_owned()))
            .or_insert((reason, 0, Vec::new()));
        e.1 += 1;
        if e.2.len() < EXAMPLES {
            e.2.push(example);
        }
    }
}

fn spell(edge: &StatusEdge) -> String {
    let to = edge
        .to
        .as_ref()
        .map(ToString::to_string)
        .or_else(|| edge.name.clone())
        .unwrap_or_else(|| "?".to_owned());
    format!("{} -> {to}", edge.from)
}

fn declared(model: &Model, from: &str, to: &str) -> bool {
    model.entities.values().any(|e| {
        e.kind == EntityKind::Flow
            && e.ends.as_ref().is_some_and(|(a, b)| {
                let (a, b) = (a.as_deref(), b.as_deref());
                (a == Some(from) && b == Some(to)) || (a == Some(to) && b == Some(from))
            })
    })
}

fn classify(cx: &Cx<'_>, edge: &StatusEdge, out: &mut Output, t: &mut Tally) {
    out.count(RULE, 1);
    let from = end_of(cx, &edge.from.to_string());
    if matches!(from, End::Foreign) {
        return;
    }
    let owner_label = match &from {
        End::Node(n) => n.as_str(),
        _ => "an uncertain owner",
    };
    let Some(to) = &edge.to else {
        // A gap: nothing can be claimed about the target, except that a package outside the
        // repository is not an edge between owners at all.
        if edge.reason == Some(GapReason::External) {
            return;
        }
        t.soft(Reason::UnresolvedEdge, owner_label, spell(edge));
        return;
    };
    let to_end = end_of(cx, &to.to_string());
    match (&from, to_end) {
        (_, End::Foreign) => {}
        (End::Node(a), End::Node(b)) => {
            if a == &b || declared(cx.model, a, &b) {
                return;
            }
            if edge.status == EdgeStatus::Must {
                t.crossing
                    .entry((a.clone(), b))
                    .or_default()
                    .push((edge.from.path().to_owned(), spell(edge)));
            } else {
                t.soft(Reason::UnresolvedEdge, owner_label, spell(edge));
            }
        }
        _ => t.soft(Reason::MayOnlyOwner, owner_label, spell(edge)),
    }
}

/// The symbol graph of the folded `code`, assembled from the file views the fold already made.
pub fn build_graph(root: &std::path::Path, code: &Code) -> SymbolGraph {
    let files = code
        .files
        .iter()
        .filter_map(|f| f.symbols().cloned())
        .collect();
    let mut deps = CrateDeps::new(root);
    let graph = SymbolGraph::from_files_with_deps(files, &mut deps);
    tracing::info!(
        edges = graph.edges_with_status().len(),
        "symbol graph assembled for SYS013"
    );
    graph
}

/// Evaluate SYS013 over the edges of `graph`.
pub fn sys013(cx: &Cx<'_>, out: &mut Output) {
    if !needs_graph(cx.model) {
        // The graph may exist for the CAP rules; with one code-owning node no edge crosses owners.
        return;
    }
    let graph = cx.graph;
    let mut t = Tally::default();
    let mut seen = BTreeSet::new();
    for edge in graph.edges_with_status().iter().filter(|e| is_subject(e)) {
        if seen.insert((
            edge.from.to_string(),
            edge.to.clone(),
            edge.kind,
            edge.name.clone(),
        )) {
            classify(cx, edge, out, &mut t);
        }
    }
    for ((a, b), edges) in t.crossing {
        let n = edges.len();
        let shown = edges
            .iter()
            .take(EXAMPLES)
            .map(|(_, e)| e.as_str())
            .collect::<Vec<_>>()
            .join("; ");
        let site = edges.first().map(|(f, _)| f.clone());
        out.fire(
            RULE,
            Severity::Error,
            format!("{n} edge(s) from `{a}` to `{b}` with no flow between them: {shown}"),
            &format!("edge/{a}->{b}"),
            site.as_deref().map(|f| (f, (0, 0))),
        );
    }
    for ((_, owner), (reason, n, examples)) in t.soft {
        out.unresolved(
            RULE,
            reason,
            &format!(
                "{n} edge(s) from {owner} cannot be placed between owners ({}): {}",
                reason.code(),
                examples.join("; ")
            ),
            &format!("edge/{owner}|{}", reason.code()),
            None,
        );
    }
    tracing::info!(
        subjects = out.subjects.get(RULE).copied().unwrap_or(0),
        "SYS013 evaluated"
    );
}
