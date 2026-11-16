//! The flow and wireframe checks: every state reachable from the entry, no dead ends, every
//! fallible step has an error path, every decision has all its branches, and a scene authored at
//! `fidelity = "wire"` uses no brand tokens. A flow with one node is valid; an absent fidelity
//! means final, so the wire rule is silent.

// frob:ticket 01M5XCZ119D08JHJJZ8TTR3HMR

use std::collections::{BTreeMap, BTreeSet, VecDeque};

use crate::flow_files::FlowFacts;
use crunk_spec::FlowFile;

/// The fidelity value that marks a scene as a wireframe.
pub const WIRE: &str = "wire";

/// What a flow finding is about.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum FlowIssue {
    /// A state cannot be reached from the flow's entry node.
    Unreachable,
    /// A non-terminal state has no outgoing edge.
    DeadEnd,
    /// A fallible state has no edge into an error state.
    NoErrorPath,
    /// A decision state lacks an outgoing edge for one of its branches.
    MissingBranch,
    /// A wire-fidelity scene uses a brand token.
    BrandInWire,
}

/// One flow or wireframe finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FlowFinding {
    /// What kind of finding.
    pub issue: FlowIssue,
    /// The flow or scene file it is about, relative to the project root.
    pub path: String,
    /// The state or token the finding names.
    pub subject: String,
    /// The human message.
    pub message: String,
}

/// Author annotations for one flow: which states end it, which can fail, which decide.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FlowNotes {
    /// States flagged `terminal = true`; they may have no outgoing edge.
    pub terminal: BTreeSet<String>,
    /// States marked fallible; each needs an edge into an error state.
    pub fallible: BTreeSet<String>,
    /// Decision states with the triggers every branch must carry.
    pub decisions: BTreeMap<String, BTreeSet<String>>,
}

/// A scene as the wire rule reads it: its fidelity and the tokens it references.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SceneTokens {
    /// The scene file, relative to the project root.
    pub path: String,
    /// The authored fidelity; `None` means final.
    pub fidelity: Option<String>,
    /// Token names the scene references.
    pub tokens: Vec<String>,
}

/// True when `state` names an error state (`error`, `failed`, `fail-...`).
fn is_error_state(node: &str) -> bool {
    let state = node.split_once(':').map_or(node, |(_, s)| s).to_lowercase();
    state.starts_with("error") || state.starts_with("fail")
}

/// True when token `name` is a brand token: any `.`, `-` or `_` separated segment is `brand`.
fn is_brand(name: &str) -> bool {
    name.split(['.', '-', '_']).any(|seg| seg == "brand")
}

/// The nodes reachable from the flow's entry (its first node), entry included.
fn reachable(flow: &FlowFile) -> BTreeSet<&str> {
    let mut seen = BTreeSet::new();
    let mut queue = VecDeque::new();
    if let Some(entry) = flow.nodes.first() {
        seen.insert(entry.as_str());
        queue.push_back(entry.as_str());
    }
    while let Some(node) = queue.pop_front() {
        for edge in flow.edges.iter().filter(|e| e.from == node) {
            if seen.insert(edge.to.as_str()) {
                queue.push_back(edge.to.as_str());
            }
        }
    }
    seen
}

/// Reachability, dead-end, error-path and branch findings for one flow.
fn check_flow(path: &str, flow: &FlowFile, notes: &FlowNotes) -> Vec<FlowFinding> {
    let finding = |issue, subject: &str, message: String| FlowFinding {
        issue,
        path: path.to_owned(),
        subject: subject.to_owned(),
        message,
    };
    let mut out = Vec::new();
    let reached = reachable(flow);
    let mut sorted: Vec<&String> = flow.nodes.iter().collect();
    sorted.sort();
    for node in sorted {
        if !reached.contains(node.as_str()) {
            tracing::debug!(%path, %node, "flow state unreachable");
            out.push(finding(
                FlowIssue::Unreachable,
                node,
                format!("state `{node}` is unreachable from the entry"),
            ));
        }
        let outgoing: Vec<_> = flow.edges.iter().filter(|e| &e.from == node).collect();
        let single = flow.nodes.len() == 1;
        if outgoing.is_empty() && !single && !notes.terminal.contains(node) {
            tracing::debug!(%path, %node, "flow dead end");
            out.push(finding(
                FlowIssue::DeadEnd,
                node,
                format!("state `{node}` is a dead end; add an edge or mark it terminal"),
            ));
        }
        if notes.fallible.contains(node) && !outgoing.iter().any(|e| is_error_state(&e.to)) {
            out.push(finding(
                FlowIssue::NoErrorPath,
                node,
                format!("fallible state `{node}` has no error path"),
            ));
        }
        if let Some(branches) = notes.decisions.get(node) {
            for branch in branches {
                if !outgoing.iter().any(|e| &e.trigger == branch) {
                    out.push(finding(
                        FlowIssue::MissingBranch,
                        node,
                        format!("decision `{node}` has no `{branch}` branch"),
                    ));
                }
            }
        }
    }
    out
}

/// Brand tokens used by a wire-fidelity scene; any other fidelity is silent.
fn check_scene(scene: &SceneTokens) -> Vec<FlowFinding> {
    if scene.fidelity.as_deref() != Some(WIRE) {
        return Vec::new();
    }
    scene
        .tokens
        .iter()
        .filter(|t| is_brand(t))
        .map(|t| {
            tracing::debug!(path = %scene.path, token = %t, "brand token in wire scene");
            FlowFinding {
                issue: FlowIssue::BrandInWire,
                path: scene.path.clone(),
                subject: t.clone(),
                message: format!("wire scene uses brand token `{t}`"),
            }
        })
        .collect()
}

/// Run every flow and wireframe check. `notes` maps a flow path to its annotations (absent means
/// none); findings come in flow path order, then scene order.
#[must_use]
pub fn check_flow_rules(
    facts: &FlowFacts,
    notes: &BTreeMap<String, FlowNotes>,
    scenes: &[SceneTokens],
) -> Vec<FlowFinding> {
    let empty = FlowNotes::default();
    let mut out = Vec::new();
    for (path, flow) in &facts.files {
        out.extend(check_flow(path, flow, notes.get(path).unwrap_or(&empty)));
    }
    for scene in scenes {
        out.extend(check_scene(scene));
    }
    tracing::debug!(findings = out.len(), "flow checks done");
    out
}
