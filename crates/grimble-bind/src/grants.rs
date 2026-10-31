//! The grant ratchet: per-node grant counts and breadth, and their delta since a baseline model.
//!
//! A grant is `may ATOM [at SEL]` on a node (binding.md 7.2). Its breadth is the number of units
//! the selector matches: a file, or a `file::QUALNAME` entry for a symbol selector (the node's
//! `owns` files when there is no `at`). The ratchet only ever
//! compares like with like: both the current and the baseline grants are evaluated over the
//! SAME file universe, so a delta means a grant changed, not that the repo grew.
//!
//! Trust zones and ungated nodes (ticket 1DC0JFG) are read from the same facts: a zone is a node's
//! every-atom grant at one broad glob, an ungated node owns no code, so no capability check judges it.
//!
//! Grants are identified across the two models by `(node, atom as written, string arguments)`.
//! A grant is widened when it matches a file its baseline did not (even if it also lost others),
//! narrowed when it only lost files, and added or removed when the identity is new or gone.

// frob:ticket 01M4GYBTXAPBEX9QYWYX5FKR67
// frob:ticket 01M4GYBZZB9Z4QPMW451DC0JFG

use std::collections::{BTreeMap, BTreeSet};

use gob_walk::{Selector, WalkResult, select_breadth};
use grimble_model::ast::EntityKind;

use crate::model::Model;
use crate::types::Role;

/// A grant with the files its selector matches, ready to compare.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GrantFacts {
    /// The node anchor, `node/name`.
    pub node: String,
    /// The atom as written.
    pub atom: String,
    /// The string arguments of the grant.
    pub args: Vec<String>,
    /// The `at` selector text, `None` for a whole-node grant.
    pub at: Option<String>,
    /// The files the grant covers in the evaluated walk.
    pub files: BTreeSet<String>,
    /// True when the grant states a `because=` or `ticket=` reason.
    pub has_reason: bool,
    /// The .grmb file the grant is written in.
    pub file: String,
}

impl GrantFacts {
    /// The grant spelled as written, `fs.read("a") at "src/**"`.
    pub fn name(&self) -> String {
        let mut out = self.atom.clone();
        if !self.args.is_empty() {
            let args: Vec<String> = self.args.iter().map(|a| format!("{a:?}")).collect();
            out.push('(');
            out.push_str(&args.join(", "));
            out.push(')');
        }
        if let Some(at) = &self.at {
            out.push_str(" at ");
            out.push_str(at);
        }
        out
    }

    fn key(&self) -> GrantKey {
        (self.node.clone(), self.atom.clone(), self.args.clone())
    }
}

type GrantKey = (String, String, Vec<String>);

pub(crate) fn files_of(selectors: &[&Selector], walk: &WalkResult) -> BTreeSet<String> {
    selectors
        .iter()
        .flat_map(|s| select_breadth(s, walk))
        .collect()
}

/// Every node grant of `model` with its breadth measured over `walk`.
pub fn facts(model: &Model, walk: &WalkResult) -> Vec<GrantFacts> {
    let mut out = Vec::new();
    for e in model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node)
    {
        let owns: Vec<&Selector> = e
            .clauses_of(Role::Owns)
            .filter_map(|c| c.selector.as_ref())
            .collect();
        let owned = files_of(&owns, walk);
        for g in &e.grants {
            let files = match &g.at {
                Some(sel) => files_of(&[sel], walk),
                None => owned.clone(),
            };
            out.push(GrantFacts {
                node: e.anchor.clone(),
                atom: g.written.clone(),
                args: g.args.clone(),
                at: g.at_text.clone(),
                files,
                has_reason: g.because.is_some() || g.ticket.is_some(),
                file: g.file.clone(),
            });
        }
    }
    tracing::debug!(grants = out.len(), "grant facts collected");
    out
}

/// What happened to a grant since the baseline.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum ChangeKind {
    /// The grant is new.
    Added,
    /// The grant covers files its baseline did not.
    Widened,
    /// The grant covers fewer files and none new.
    Narrowed,
    /// The grant is gone.
    Removed,
}

impl ChangeKind {
    /// The lower-case word for reports.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Added => "added",
            Self::Widened => "widened",
            Self::Narrowed => "narrowed",
            Self::Removed => "removed",
        }
    }
}

/// One grant that differs from the baseline.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Change {
    /// The node anchor.
    pub node: String,
    /// The grant, named as in [`GrantFacts::name`] (current form; baseline form when removed).
    pub grant: String,
    /// How it changed.
    pub kind: ChangeKind,
    /// Files covered at the baseline.
    pub before: usize,
    /// Files covered now.
    pub after: usize,
}

/// Grant count and breadth of one node, with the baseline's when there is one.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NodeRow {
    /// The node anchor.
    pub node: String,
    /// Grants now.
    pub grants: usize,
    /// Distinct files covered by the node's grants now.
    pub breadth: usize,
    /// Grants at the baseline, when there is a baseline.
    pub base_grants: Option<usize>,
    /// Distinct files covered at the baseline, when there is a baseline.
    pub base_breadth: Option<usize>,
}

/// The full ratchet report.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Ratchet {
    /// True when a baseline was compared; false means counts only, no delta.
    pub has_baseline: bool,
    /// One row per node that has grants now or had them at the baseline.
    pub nodes: Vec<NodeRow>,
    /// Grants that differ from the baseline, widenings first; empty without a baseline.
    pub changes: Vec<Change>,
    /// Current grants that state no reason, as `node: grant`.
    pub unreasoned: Vec<String>,
}

/// Union of the files of `grants`.
fn breadth(grants: &[&GrantFacts]) -> usize {
    grants
        .iter()
        .flat_map(|g| g.files.iter())
        .collect::<BTreeSet<_>>()
        .len()
}

fn by_node(all: &[GrantFacts]) -> BTreeMap<&str, Vec<&GrantFacts>> {
    let mut m: BTreeMap<&str, Vec<&GrantFacts>> = BTreeMap::new();
    for g in all {
        m.entry(g.node.as_str()).or_default().push(g);
    }
    m
}

fn by_key(all: &[GrantFacts]) -> BTreeMap<GrantKey, (BTreeSet<&str>, &GrantFacts)> {
    let mut m: BTreeMap<GrantKey, (BTreeSet<&str>, &GrantFacts)> = BTreeMap::new();
    for g in all {
        let e = m.entry(g.key()).or_insert_with(|| (BTreeSet::new(), g));
        e.0.extend(g.files.iter().map(String::as_str));
    }
    m
}

fn classify(cur: &BTreeSet<&str>, base: &BTreeSet<&str>) -> Option<ChangeKind> {
    if cur.difference(base).next().is_some() {
        Some(ChangeKind::Widened)
    } else if base.difference(cur).next().is_some() {
        Some(ChangeKind::Narrowed)
    } else {
        None
    }
}

/// Compare `cur` with `base` (both measured over the same walk); `None` base reports counts only.
pub fn ratchet(cur: &[GrantFacts], base: Option<&[GrantFacts]>) -> Ratchet {
    let cur_nodes = by_node(cur);
    let base_nodes = base.map(by_node);
    let mut names: BTreeSet<&str> = cur_nodes.keys().copied().collect();
    if let Some(b) = &base_nodes {
        names.extend(b.keys().copied());
    }
    let nodes = names
        .into_iter()
        .map(|n| {
            let now = cur_nodes.get(n).map_or(&[][..], Vec::as_slice);
            let was = base_nodes
                .as_ref()
                .map(|b| b.get(n).map_or(&[][..], Vec::as_slice));
            NodeRow {
                node: n.to_owned(),
                grants: now.len(),
                breadth: breadth(now),
                base_grants: was.map(<[_]>::len),
                base_breadth: was.map(breadth),
            }
        })
        .collect();
    let mut changes = Vec::new();
    if let Some(base) = base {
        let (c, b) = (by_key(cur), by_key(base));
        for (key, (files, g)) in &c {
            match b.get(key) {
                None => changes.push(Change {
                    node: key.0.clone(),
                    grant: g.name(),
                    kind: ChangeKind::Added,
                    before: 0,
                    after: files.len(),
                }),
                Some((was, _)) => {
                    if let Some(kind) = classify(files, was) {
                        changes.push(Change {
                            node: key.0.clone(),
                            grant: g.name(),
                            kind,
                            before: was.len(),
                            after: files.len(),
                        });
                    }
                }
            }
        }
        for (key, (files, g)) in &b {
            if !c.contains_key(key) {
                changes.push(Change {
                    node: key.0.clone(),
                    grant: g.name(),
                    kind: ChangeKind::Removed,
                    before: files.len(),
                    after: 0,
                });
            }
        }
        // Widenings and additions first: they are what a reviewer must look at.
        changes.sort_by_key(|c| {
            let rank = match c.kind {
                ChangeKind::Widened => 0,
                ChangeKind::Added => 1,
                ChangeKind::Narrowed => 2,
                ChangeKind::Removed => 3,
            };
            (rank, c.node.clone(), c.grant.clone())
        });
    }
    let unreasoned = cur
        .iter()
        .filter(|g| !g.has_reason)
        .map(|g| format!("{}: {}", g.node, g.name()))
        .collect();
    tracing::info!(
        nodes = cur_nodes.len(),
        changes = changes.len(),
        baseline = base.is_some(),
        "grant ratchet computed"
    );
    Ratchet {
        has_baseline: base.is_some(),
        nodes,
        changes,
        unreasoned,
    }
}

/// The glob a grant must carry to count as broad: a tree pattern, never a single file or symbol.
const BROAD_MARK: &str = "**";

/// One node's every-atom grant at one broad glob: a declared trust zone, not an enforced one.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TrustZone {
    /// The node anchor.
    pub node: String,
    /// The `at` selector text the atoms are granted at.
    pub at: String,
    /// Distinct files the zone covers in the evaluated walk.
    pub files: usize,
    /// The .grmb file the first of the zone's grants is written in.
    pub file: String,
}

/// The trust zones of a model and how much of the tree they cover together.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Zones {
    /// One entry per `(node, glob)` pair, ordered by node then glob.
    pub zones: Vec<TrustZone>,
    /// Distinct files covered by any zone: overlapping zones count a file once.
    pub files: usize,
}

/// The leaf atoms of the registry: every registered atom that has no registered child.
pub fn leaf_atoms() -> Vec<String> {
    let names: Vec<&str> = gob_ir::registry::atoms().iter().map(|a| a.name).collect();
    names
        .iter()
        .filter(|n| {
            !names
                .iter()
                .any(|m| m.strip_prefix(**n).is_some_and(|r| r.starts_with('.')))
        })
        .map(|n| (*n).to_owned())
        .collect()
}

/// True when the selector text names a tree of files (has `**`) and not a symbol.
fn is_broad(at: &str) -> bool {
    at.contains(BROAD_MARK) && !at.contains("::")
}

/// True when a grant of `granted` covers `atom`: the atom itself or its parent.
fn grant_covers(granted: &str, atom: &str) -> bool {
    let granted = gob_ir::registry::canonical(granted).unwrap_or(granted);
    granted == atom
        || atom
            .strip_prefix(granted)
            .is_some_and(|r| r.starts_with('.'))
}

/// The trust zones among `all`: grants at one broad glob of one node that together cover every
/// atom of `universe`. A grant's arguments do not exempt it (ticket 5X9CAQE: CAP001 now enforces
/// them, but a broad argument such as `fs.read("**")` is still a broad grant). Zones may overlap; each is listed and the union is counted once.
pub fn trust_zones(all: &[GrantFacts], universe: &[String]) -> Zones {
    let mut groups: BTreeMap<(&str, &str), Vec<&GrantFacts>> = BTreeMap::new();
    for g in all {
        if let Some(at) = g.at.as_deref().filter(|a| is_broad(a)) {
            groups.entry((g.node.as_str(), at)).or_default().push(g);
        }
    }
    let mut out = Zones::default();
    let mut seen: BTreeSet<&str> = BTreeSet::new();
    for ((node, at), grants) in groups {
        let every = !universe.is_empty()
            && universe
                .iter()
                .all(|a| grants.iter().any(|g| grant_covers(&g.atom, a)));
        if !every {
            continue;
        }
        let files: BTreeSet<&str> = grants
            .iter()
            .flat_map(|g| g.files.iter().map(String::as_str))
            .collect();
        seen.extend(files.iter().copied());
        out.zones.push(TrustZone {
            node: node.to_owned(),
            at: at.to_owned(),
            files: files.len(),
            file: grants[0].file.clone(),
        });
    }
    out.files = seen.len();
    tracing::info!(
        zones = out.zones.len(),
        files = out.files,
        "trust zones found"
    );
    out
}

/// How many nodes a capability check can judge and which it cannot.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Gating {
    /// Every node of the model.
    pub nodes: usize,
    /// External nodes (`kind external`): they own no code by definition and are not counted ungated.
    pub external: usize,
    /// Nodes with a code-owning selector: subjects of CAP001 and CAP002.
    pub gated: usize,
    /// Nodes that are neither external nor gated, as anchors in order.
    pub ungated: Vec<String>,
}

/// Classify the nodes of `model`. A node is gated when it has an `owns` clause whose selector
/// parsed; one whose every `owns` selector failed to parse owns no code and is ungated.
pub fn gating(model: &Model) -> Gating {
    let mut out = Gating::default();
    for e in model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node)
    {
        out.nodes += 1;
        if e.external {
            out.external += 1;
        } else if e.clauses_of(Role::Owns).any(|c| c.selector.is_some()) {
            out.gated += 1;
        } else {
            out.ungated.push(e.anchor.clone());
        }
    }
    out.ungated.sort();
    tracing::info!(
        nodes = out.nodes,
        gated = out.gated,
        ungated = out.ungated.len(),
        "node gating classified"
    );
    out
}
