//! Epic claim coverage (`distributed-tickets.md` sections 3.3 and 6.5, rows 59, 60 and 62): which claim covers a ticket.
//!
//! An epic claim covers its open leaves; a task claim covers only itself. A claim on a descendant stands and
//! shadows the epic's claim for that subtree ("the epic claim covers the rest"). Coverage is recomputed from the
//! parent links on every call, so a split or a move needs no stored state: identity is the ULID, the tree is the
//! truth. Nothing here reads a clock, the network or a `lease` event; callers hand in the tree and the claims.

// frob:ticket 01M5CW05FBNNJEAP2QQJ2S1737

use std::collections::HashMap;

use tracing::{debug, info, warn};

use crate::id::TicketId;

/// One ticket as coverage sees it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    /// The ticket.
    pub id: TicketId,
    /// Its parent, when it has one.
    pub parent: Option<TicketId>,
    /// True for an epic (a claim on it covers descendants).
    pub epic: bool,
    /// True while the ticket is not done (closed leaves are never covered).
    pub open: bool,
}

/// A live claim on one ticket.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Claim {
    /// Who holds it (actor, as written on the `lease` event).
    pub holder: String,
}

/// Why a ticket is covered.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Cover {
    /// The ticket that carries the claim.
    pub claimed: TicketId,
    /// Who holds it.
    pub holder: String,
    /// True when the claim is on an ancestor epic rather than on the ticket itself.
    pub via_epic: bool,
}

/// The tickets and claims coverage is computed over.
#[derive(Debug, Default)]
pub struct CoverMap {
    /// Every known ticket by id.
    nodes: HashMap<TicketId, Node>,
    /// Live claims by claimed ticket.
    claims: HashMap<TicketId, Claim>,
}

impl CoverMap {
    /// Build the map from every ticket and every live claim.
    pub fn new(nodes: impl IntoIterator<Item = Node>, claims: HashMap<TicketId, Claim>) -> Self {
        let nodes: HashMap<TicketId, Node> = nodes.into_iter().map(|n| (n.id, n)).collect();
        debug!(
            tickets = nodes.len(),
            claims = claims.len(),
            "coverage map built"
        );
        Self { nodes, claims }
    }

    /// The nearest claim covering `id`: its own, else the closest claimed ancestor epic's; `None` when free or closed.
    #[must_use]
    pub fn cover_of(&self, id: TicketId) -> Option<Cover> {
        let node = self.nodes.get(&id)?;
        if let Some(c) = self.claims.get(&id) {
            return Some(Cover {
                claimed: id,
                holder: c.holder.clone(),
                via_epic: false,
            });
        }
        if !node.open {
            return None;
        }
        let mut at = node.parent;
        // The walk is bounded by the ticket count so a corrupt parent cycle ends instead of hanging.
        for _ in 0..self.nodes.len() {
            let parent = self.nodes.get(&at?)?;
            if let Some(c) = self.claims.get(&parent.id).filter(|_| parent.epic) {
                return Some(Cover {
                    claimed: parent.id,
                    holder: c.holder.clone(),
                    via_epic: true,
                });
            }
            at = parent.parent;
        }
        warn!(ticket = %id, "parent chain does not end; treating as uncovered");
        None
    }

    /// True when someone other than `viewer` covers `id`: the ticket `doable` must exclude for `viewer`.
    #[must_use]
    pub fn blocked_for(&self, id: TicketId, viewer: &str) -> bool {
        self.cover_of(id).is_some_and(|c| c.holder != viewer)
    }

    /// The open leaves under `epic` that its claim covers (a leaf under a separately claimed child is not).
    #[must_use]
    pub fn covered_leaves(&self, epic: TicketId) -> Vec<TicketId> {
        let mut out: Vec<TicketId> = self
            .nodes
            .values()
            .filter(|n| n.open && n.id != epic)
            .filter(|n| {
                self.cover_of(n.id)
                    .is_some_and(|c| c.via_epic && c.claimed == epic)
            })
            .map(|n| n.id)
            .collect();
        out.sort();
        out
    }

    /// The notice for the holder when `child` is filed or split under `parent`; `None` when `parent` is unclaimed.
    ///
    /// An epic claim covers the new leaf; a task claim does not, so the holder is told to claim the children.
    #[must_use]
    pub fn split_notice(&self, parent: TicketId, child: TicketId) -> Option<String> {
        let claim = self.claims.get(&parent)?;
        let epic = self.nodes.get(&parent).is_some_and(|n| n.epic);
        info!(%parent, %child, holder = %claim.holder, epic, "claimed ticket gained a child");
        Some(if epic {
            format!(
                "{child} now falls under your epic claim on {parent}: it is covered, others will not see it as doable"
            )
        } else {
            format!(
                "{parent} was split and a task claim covers only itself: claim {child} (frob work {child}) to work it"
            )
        })
    }

    /// The warning when moving `id` under `new_parent` (`None` for top level) takes it out of an epic claim.
    ///
    /// Compares coverage before and after on a copy of the tree; the map itself is not changed.
    #[must_use]
    pub fn move_warning(&self, id: TicketId, new_parent: Option<TicketId>) -> Option<String> {
        let before = self.cover_of(id)?;
        if !before.via_epic {
            return None;
        }
        let mut moved = Self {
            nodes: self.nodes.clone(),
            claims: self.claims.clone(),
        };
        moved.nodes.get_mut(&id)?.parent = new_parent;
        let still = moved
            .cover_of(id)
            .is_some_and(|c| c.claimed == before.claimed);
        if still {
            return None;
        }
        warn!(ticket = %id, epic = %before.claimed, "move takes a ticket out of a claimed epic");
        Some(format!(
            "{id} leaves the epic claim of {} held by {}: it is no longer covered",
            before.claimed, before.holder
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tid(n: u8) -> TicketId {
        format!("01M5CW05FBNNJEAP2QQJ2S17{n:02}")
            .parse()
            .expect("valid ulid")
    }

    fn node(n: u8, parent: Option<u8>, epic: bool, open: bool) -> Node {
        Node {
            id: tid(n),
            parent: parent.map(tid),
            epic,
            open,
        }
    }

    fn claim(who: &str) -> Claim {
        Claim {
            holder: who.to_owned(),
        }
    }

    /// Epic 1 with leaves 2 and 3, a closed leaf 4, and a task 5 with child 6.
    fn map(claims: &[(u8, &str)]) -> CoverMap {
        CoverMap::new(
            [
                node(1, None, true, true),
                node(2, Some(1), false, true),
                node(3, Some(1), false, true),
                node(4, Some(1), false, false),
                node(5, None, false, true),
                node(6, Some(5), false, true),
            ],
            claims.iter().map(|(n, w)| (tid(*n), claim(w))).collect(),
        )
    }

    // frob:tests cover_of
    #[test]
    fn epic_claim_covers_open_leaves_only() {
        let m = map(&[(1, "ann")]);
        let c = m.cover_of(tid(2)).expect("covered");
        assert_eq!(
            (c.claimed, c.holder.as_str(), c.via_epic),
            (tid(1), "ann", true)
        );
        assert!(m.cover_of(tid(4)).is_none());
        assert!(m.cover_of(tid(6)).is_none());
    }

    // frob:tests cover_of
    #[test]
    fn task_claim_covers_only_itself() {
        let m = map(&[(5, "bob")]);
        assert!(!m.cover_of(tid(5)).expect("own").via_epic);
        assert!(m.cover_of(tid(6)).is_none());
    }

    // frob:tests cover_of
    #[test]
    fn child_claim_shadows_the_epic_claim() {
        let m = map(&[(1, "ann"), (2, "bob")]);
        assert_eq!(m.cover_of(tid(2)).expect("c").holder, "bob");
        assert_eq!(m.cover_of(tid(3)).expect("c").holder, "ann");
    }

    // frob:tests cover_of
    #[test]
    fn parent_cycle_ends() {
        let m = CoverMap::new(
            [node(1, Some(2), true, true), node(2, Some(1), true, true)],
            HashMap::new(),
        );
        assert!(m.cover_of(tid(1)).is_none());
    }

    // frob:tests blocked_for
    #[test]
    fn doable_exclusion_spares_the_holder() {
        let m = map(&[(1, "ann")]);
        assert!(m.blocked_for(tid(3), "bob"));
        assert!(!m.blocked_for(tid(3), "ann"));
        assert!(!m.blocked_for(tid(6), "bob"));
    }

    // frob:tests covered_leaves
    #[test]
    fn covered_leaves_skip_separately_claimed_children() {
        let m = map(&[(1, "ann"), (2, "bob")]);
        assert_eq!(m.covered_leaves(tid(1)), vec![tid(3)]);
    }

    // frob:tests split_notice
    #[test]
    fn split_notice_differs_for_epic_and_task() {
        let m = map(&[(1, "ann"), (5, "bob")]);
        assert!(
            m.split_notice(tid(1), tid(2))
                .expect("n")
                .contains("covered")
        );
        assert!(m.split_notice(tid(5), tid(6)).expect("n").contains("claim"));
        assert!(map(&[]).split_notice(tid(1), tid(2)).is_none());
    }

    // frob:tests move_warning
    #[test]
    fn move_out_of_a_claimed_epic_warns() {
        let m = map(&[(1, "ann")]);
        assert!(m.move_warning(tid(2), Some(tid(5))).is_some());
        assert!(m.move_warning(tid(2), None).is_some());
        assert!(m.move_warning(tid(2), Some(tid(1))).is_none());
        assert!(m.move_warning(tid(6), None).is_none());
        assert!(map(&[]).move_warning(tid(2), None).is_none());
    }
}
