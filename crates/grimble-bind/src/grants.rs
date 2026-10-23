//! The grant ratchet: per-node grant counts and breadth, and their delta since a baseline model.
//!
//! A grant is `may ATOM [at SEL]` on a node (binding.md 7.2). Its breadth is the number of files
//! the selector matches (the node's `owns` files when there is no `at`). The ratchet only ever
//! compares like with like: both the current and the baseline grants are evaluated over the
//! SAME file universe, so a delta means a grant changed, not that the repo grew.
//!
//! Grants are identified across the two models by `(node, atom as written, string arguments)`.
//! A grant is widened when it matches a file its baseline did not (even if it also lost others),
//! narrowed when it only lost files, and added or removed when the identity is new or gone.

// frob:ticket 01M4GYBTXAPBEX9QYWYX5FKR67

use std::collections::{BTreeMap, BTreeSet};

use gob_walk::{Selector, WalkResult, select_files};
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

fn files_of(selectors: &[&Selector], walk: &WalkResult) -> BTreeSet<String> {
    selectors
        .iter()
        .flat_map(|s| select_files(s, walk))
        .map(|m| m.path)
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
