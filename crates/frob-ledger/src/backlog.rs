//! The backlog tree behind `ticket list --tree`: parent links as milestone, epic, story, task, with roll-ups.
// frob:ticket 01M48Q2A6GSSETPGKGJ6NJDNWV

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use schemars::JsonSchema;
use serde::Serialize;

use crate::TicketId;
use crate::index::Summary;
use crate::model::{Category, Priority, TicketType};
use crate::ops::doable_cmp;

/// One node of the backlog tree: a ticket with its points rolled up over its whole subtree.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct BacklogNode {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with its `~`.
    pub handle: String,
    /// Title.
    pub title: String,
    /// Ticket type.
    #[serde(rename = "type")]
    pub ty: TicketType,
    /// Workflow category.
    pub category: Category,
    /// Priority.
    pub priority: Priority,
    /// The ticket's own story points.
    pub points: Option<u8>,
    /// Own points plus every descendant's.
    pub rollup_points: u32,
    /// The part of `rollup_points` that sits on done tickets.
    pub done_points: u32,
    /// `done_points` over `rollup_points` as a whole percent; null when there are no points.
    pub percent_done: Option<u8>,
    /// True while an open blocker remains.
    pub blocked: bool,
    /// True when the ticket can be started now.
    pub doable: bool,
    /// Descendants hidden by the `--depth` fold.
    pub folded: usize,
    /// Children in rank order (empty when folded).
    pub children: Vec<BacklogNode>,
}

/// The whole backlog: parentless tickets as roots, everything else unreachable from them under Unparented.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Backlog {
    /// Tickets without a parent, in rank order.
    pub roots: Vec<BacklogNode>,
    /// Tickets whose parent is not in the listed set (missing, filtered out or cyclic); never dropped.
    pub unparented: Vec<BacklogNode>,
}

/// Build the backlog tree from `tickets`; `doable` marks startable ones; `depth` folds levels below it (1 = roots only).
#[must_use]
pub fn build(tickets: &[Summary], doable: &BTreeSet<TicketId>, depth: Option<usize>) -> Backlog {
    let by_id: BTreeMap<TicketId, &Summary> = tickets.iter().map(|s| (s.id, s)).collect();
    let mut kids: BTreeMap<TicketId, Vec<&Summary>> = BTreeMap::new();
    let mut roots: Vec<&Summary> = Vec::new();
    let mut orphans: Vec<&Summary> = Vec::new();
    for s in tickets {
        match s.parent {
            None => roots.push(s),
            Some(p) if by_id.contains_key(&p) => kids.entry(p).or_default().push(s),
            Some(_) => orphans.push(s),
        }
    }
    let mut seen = BTreeSet::new();
    let ctx = Ctx {
        kids: &kids,
        doable,
        depth,
    };
    let roots_out = ctx.nodes(roots, 1, &mut seen);
    // Orphans first, then whatever a parent cycle kept out of every list.
    let mut unparented = ctx.nodes(orphans, 1, &mut seen);
    let cyclic: Vec<&Summary> = tickets.iter().filter(|s| !seen.contains(&s.id)).collect();
    for s in cyclic {
        unparented.extend(ctx.nodes(vec![s], 1, &mut seen));
    }
    tracing::debug!(
        roots = roots_out.len(),
        unparented = unparented.len(),
        "backlog built"
    );
    Backlog {
        roots: roots_out,
        unparented,
    }
}

struct Ctx<'a> {
    kids: &'a BTreeMap<TicketId, Vec<&'a Summary>>,
    doable: &'a BTreeSet<TicketId>,
    depth: Option<usize>,
}

impl Ctx<'_> {
    fn nodes(
        &self,
        mut level: Vec<&Summary>,
        at: usize,
        seen: &mut BTreeSet<TicketId>,
    ) -> Vec<BacklogNode> {
        level.sort_by(|a, b| doable_cmp(a, b));
        let mut out = Vec::new();
        for s in level {
            if seen.insert(s.id) {
                out.push(self.node(s, at, seen));
            }
        }
        out
    }

    fn node(&self, s: &Summary, at: usize, seen: &mut BTreeSet<TicketId>) -> BacklogNode {
        let kids = self.nodes(
            self.kids.get(&s.id).cloned().unwrap_or_default(),
            at + 1,
            seen,
        );
        let own = u32::from(s.points.unwrap_or(0));
        let own_done = if s.category == Category::Done { own } else { 0 };
        let rollup = own + kids.iter().map(|k| k.rollup_points).sum::<u32>();
        let done = own_done + kids.iter().map(|k| k.done_points).sum::<u32>();
        let hidden = count(&kids);
        let fold = self.depth.is_some_and(|d| at >= d);
        BacklogNode {
            id: s.id,
            handle: s.handle.clone(),
            title: s.title.clone(),
            ty: s.ty,
            category: s.category,
            priority: s.priority,
            points: s.points,
            rollup_points: rollup,
            done_points: done,
            percent_done: (rollup > 0)
                .then(|| u8::try_from(u64::from(done) * 100 / u64::from(rollup)).unwrap_or(100)),
            blocked: s.blocked,
            doable: self.doable.contains(&s.id),
            folded: if fold { hidden } else { 0 },
            children: if fold { Vec::new() } else { kids },
        }
    }
}

fn count(nodes: &[BacklogNode]) -> usize {
    nodes
        .iter()
        .map(|n| 1 + n.folded + count(&n.children))
        .sum()
}

impl Backlog {
    /// Every node of the tree, roots and unparented, counted.
    #[must_use]
    pub fn len(&self) -> usize {
        count(&self.roots) + count(&self.unparented)
    }

    /// True when no ticket is listed.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.roots.is_empty() && self.unparented.is_empty()
    }

    /// The indented text view, one line per node, orphans under an `Unparented` heading.
    #[must_use]
    pub fn render(&self) -> Vec<String> {
        let mut out = Vec::new();
        for n in &self.roots {
            line(n, 0, &mut out);
        }
        if !self.unparented.is_empty() {
            out.push("Unparented".to_owned());
            for n in &self.unparented {
                line(n, 1, &mut out);
            }
        }
        out
    }
}

fn line(n: &BacklogNode, indent: usize, out: &mut Vec<String>) {
    let mut s = format!("{}{} {} {}", "  ".repeat(indent), n.handle, n.ty, n.title);
    if let Some(p) = n.percent_done {
        let _ = write!(s, " [{} pts, {p}% done]", n.rollup_points);
    }
    if n.blocked {
        s.push_str(" (blocked)");
    } else if n.doable {
        s.push_str(" (doable)");
    }
    if n.folded > 0 {
        let _ = write!(s, " (+{} folded)", n.folded);
    }
    out.push(s);
    for c in &n.children {
        line(c, indent + 1, out);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sm(
        n: u8,
        parent: Option<u8>,
        ty: &str,
        cat: &str,
        pts: Option<u8>,
        blocked: bool,
    ) -> Summary {
        let id = |n: u8| -> TicketId {
            format!("01M48Q2A6GSSETPGKGJ6NJDN{n:02}")
                .parse()
                .expect("ulid")
        };
        let created: crate::model::Stamp = "2026-10-01T00:00:00Z".parse().expect("stamp");
        Summary {
            id: id(n),
            handle: format!("~T{n:02}"),
            title: format!("title {n}"),
            ty: ty.parse().expect("type"),
            category: cat.parse().expect("category"),
            outcome: None,
            priority: "medium".parse().expect("priority"),
            class: "standard".parse().expect("class"),
            due: None,
            points: pts,
            parent: parent.map(id),
            created,
            updated: created,
            blocked,
        }
    }

    fn fixture() -> Vec<Summary> {
        vec![
            sm(1, None, "epic", "in-progress", None, false),
            sm(2, Some(1), "story", "in-progress", None, false),
            sm(3, Some(2), "task", "done", Some(3), false),
            sm(4, Some(2), "task", "todo", Some(5), false),
            sm(5, Some(1), "task", "todo", Some(2), true),
            sm(6, Some(99), "task", "todo", Some(1), false),
        ]
    }

    // frob:ticket 01M48Q2A6GSSETPGKGJ6NJDNWV
    #[test]
    fn fixture_renders_the_tree_with_rollups_and_unparented() {
        let doable: BTreeSet<TicketId> = fixture()
            .iter()
            .filter(|s| s.id.to_string().ends_with("04") || s.id.to_string().ends_with("06"))
            .map(|s| s.id)
            .collect();
        let b = build(&fixture(), &doable, None);
        assert_eq!(
            b.render(),
            vec![
                "~T01 epic title 1 [10 pts, 30% done]",
                "  ~T02 story title 2 [8 pts, 37% done]",
                "    ~T03 task title 3 [3 pts, 100% done]",
                "    ~T04 task title 4 [5 pts, 0% done] (doable)",
                "  ~T05 task title 5 [2 pts, 0% done] (blocked)",
                "Unparented",
                "  ~T06 task title 6 [1 pts, 0% done] (doable)",
            ]
        );
    }

    // frob:ticket 01M48Q2A6GSSETPGKGJ6NJDNWV
    #[test]
    fn depth_folds_below_and_counts_hidden() {
        let b = build(&fixture(), &BTreeSet::new(), Some(2));
        let r = b.render();
        assert_eq!(r[1], "  ~T02 story title 2 [8 pts, 37% done] (+2 folded)");
        assert_eq!(b.len(), 6);
    }

    // frob:ticket 01M48Q2A6GSSETPGKGJ6NJDNWV
    #[test]
    fn parent_cycle_members_land_under_unparented() {
        let mut a = sm(7, Some(8), "task", "todo", None, false);
        let mut b = sm(8, Some(7), "task", "todo", None, false);
        a.title = "a".into();
        b.title = "b".into();
        let t = build(&[a, b], &BTreeSet::new(), None);
        assert!(t.roots.is_empty());
        assert_eq!(t.len(), 2);
    }

    // frob:tests crates/frob-ledger/src/backlog.rs::Backlog.is_empty
    #[test]
    fn is_empty_only_when_nothing_is_listed() {
        assert!(build(&[], &BTreeSet::new(), None).is_empty());
        assert!(!build(&fixture(), &BTreeSet::new(), None).is_empty());
    }
}
