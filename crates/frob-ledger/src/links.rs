//! The canonical link table: inverses, normalization and topology checks.
//!
//! Every link is stored on its source ticket as written (`A blocks B` on A,
//! or `B blocked-by A` on B). For identity and topology each link is
//! normalized to the forward spelling of the table's first column, so the two
//! spellings of one edge compare equal.

use crate::error::{LedgerError, Result};
use crate::id::TicketId;
use crate::model::{Frontmatter, LinkKind, TicketType};

impl LinkKind {
    /// The inverse spelling (`blocks` and `blocked-by`; `relates` is its own).
    #[must_use]
    pub const fn inverse(self) -> Self {
        match self {
            Self::Blocks => Self::BlockedBy,
            Self::BlockedBy => Self::Blocks,
            Self::Relates => Self::Relates,
            Self::Duplicates => Self::DuplicatedBy,
            Self::DuplicatedBy => Self::Duplicates,
            Self::Causes => Self::CausedBy,
            Self::CausedBy => Self::Causes,
            Self::SplitFrom => Self::Splits,
            Self::Splits => Self::SplitFrom,
            Self::DiscoveredFrom => Self::Spawned,
            Self::Spawned => Self::DiscoveredFrom,
            Self::EnablerFor => Self::EnabledBy,
            Self::EnabledBy => Self::EnablerFor,
            Self::Supersedes => Self::SupersededBy,
            Self::SupersededBy => Self::Supersedes,
        }
    }

    /// True for the first-column spelling of its row (and for `relates`).
    pub const fn is_forward(self) -> bool {
        matches!(
            self,
            Self::Blocks
                | Self::Relates
                | Self::Duplicates
                | Self::Causes
                | Self::Splits
                | Self::DiscoveredFrom
                | Self::EnablerFor
                | Self::Supersedes
        )
    }

    /// The forward spelling of this kind.
    #[must_use]
    pub const fn forward(self) -> Self {
        if self.is_forward() {
            self
        } else {
            self.inverse()
        }
    }

    /// True when the topology forbids cycles through this kind.
    pub const fn acyclic(self) -> bool {
        matches!(
            self,
            Self::Blocks | Self::Causes | Self::DiscoveredFrom | Self::Supersedes
        )
    }
}

/// A normalized edge: `from --kind--> to` with `kind` in forward spelling.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Edge {
    /// Source of the forward spelling.
    pub from: TicketId,
    /// Forward kind.
    pub kind: LinkKind,
    /// Target of the forward spelling.
    pub to: TicketId,
}

impl Edge {
    /// Normalize `src --kind--> dst`; `relates` orders its endpoints.
    pub fn normalize(src: TicketId, kind: LinkKind, dst: TicketId) -> Self {
        let (from, to) = if kind.is_forward() {
            (src, dst)
        } else {
            (dst, src)
        };
        let (from, to) = if kind == LinkKind::Relates && to < from {
            (to, from)
        } else {
            (from, to)
        };
        Self {
            from,
            kind: kind.forward(),
            to,
        }
    }
}

/// All normalized edges of a frontmatter.
pub fn edges_of(front: &Frontmatter) -> Vec<Edge> {
    front
        .links
        .iter()
        .map(|l| Edge::normalize(front.id, l.kind, l.target))
        .collect()
}

fn rejected(code: &'static str, message: impl Into<String>) -> LedgerError {
    LedgerError::LinkRejected {
        code,
        message: message.into(),
    }
}

fn reaches(edges: &[Edge], kind: LinkKind, start: TicketId, goal: TicketId) -> bool {
    let mut seen = std::collections::HashSet::new();
    let mut stack = vec![start];
    while let Some(n) = stack.pop() {
        if n == goal {
            return true;
        }
        if !seen.insert(n) {
            continue;
        }
        stack.extend(
            edges
                .iter()
                .filter(|e| e.kind == kind && e.from == n)
                .map(|e| e.to),
        );
    }
    false
}

/// Check that adding `src --kind--> dst` keeps the topology valid.
///
/// `edges` is the current normalized graph; `ty_of` gives a ticket's type.
///
/// # Errors
///
/// [`LedgerError::LinkRejected`] with `E-LINK-SELF`, `E-LINK-CYCLE`,
/// `E-LINK-ORIGIN` (a second `splits` origin), `E-LINK-DUPLICATE` or
/// `E-LINK-TARGET`.
pub fn check_add(
    edges: &[Edge],
    ty_of: &dyn Fn(TicketId) -> Option<TicketType>,
    src: TicketId,
    kind: LinkKind,
    dst: TicketId,
) -> Result<()> {
    if src == dst {
        return Err(rejected(
            "E-LINK-SELF",
            format!("{src} cannot link to itself"),
        ));
    }
    let e = Edge::normalize(src, kind, dst);
    if e.kind.acyclic() && reaches(edges, e.kind, e.to, e.from) {
        return Err(rejected(
            "E-LINK-CYCLE",
            format!("{} {} {} would close a cycle", e.from, e.kind, e.to),
        ));
    }
    match e.kind {
        LinkKind::Splits => {
            if let Some(other) = edges
                .iter()
                .find(|x| x.kind == LinkKind::Splits && x.to == e.to && x.from != e.from)
            {
                return Err(rejected(
                    "E-LINK-ORIGIN",
                    format!("{} was already split from {}", e.to, other.from),
                ));
            }
        }
        LinkKind::Duplicates => {
            if edges
                .iter()
                .any(|x| x.kind == LinkKind::Duplicates && x.from == e.to)
            {
                return Err(rejected(
                    "E-LINK-DUPLICATE",
                    format!("{} is itself a duplicate; point at the original", e.to),
                ));
            }
            if edges
                .iter()
                .any(|x| x.kind == LinkKind::Duplicates && x.to == e.from)
            {
                return Err(rejected(
                    "E-LINK-DUPLICATE",
                    format!(
                        "{} already has duplicates; it cannot be a duplicate itself",
                        e.from
                    ),
                ));
            }
        }
        LinkKind::EnablerFor if ty_of(e.to) != Some(TicketType::Story) => {
            return Err(rejected(
                "E-LINK-TARGET",
                format!("{} is not a story; enabler-for needs a story target", e.to),
            ));
        }
        _ => {}
    }
    Ok(())
}

/// Check that making `parent` the parent of `child` keeps the hierarchy a forest.
///
/// # Errors
///
/// [`LedgerError::LinkRejected`] with `E-LINK-SELF` or `E-LINK-CYCLE`.
pub fn check_parent(
    parent_of: &dyn Fn(TicketId) -> Option<TicketId>,
    child: TicketId,
    parent: TicketId,
) -> Result<()> {
    if child == parent {
        return Err(rejected(
            "E-LINK-SELF",
            format!("{child} cannot be its own parent"),
        ));
    }
    let mut cursor = Some(parent);
    let mut hops = 0;
    while let Some(n) = cursor {
        if n == child {
            return Err(rejected(
                "E-LINK-CYCLE",
                format!("{parent} is a descendant of {child}; the parent chain would loop"),
            ));
        }
        hops += 1;
        if hops > 10_000 {
            break;
        }
        cursor = parent_of(n);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ids(n: usize) -> Vec<TicketId> {
        (0..n).map(|_| TicketId::mint()).collect()
    }

    #[test]
    fn inverse_is_an_involution_and_forward_is_stable() {
        for k in LinkKind::ALL {
            assert_eq!(k.inverse().inverse(), *k);
            assert!(k.forward().is_forward());
            assert_eq!(k.forward().forward(), k.forward());
        }
    }

    #[test]
    fn both_spellings_normalize_alike() {
        let v = ids(2);
        assert_eq!(
            Edge::normalize(v[0], LinkKind::Blocks, v[1]),
            Edge::normalize(v[1], LinkKind::BlockedBy, v[0])
        );
        assert_eq!(
            Edge::normalize(v[0], LinkKind::Relates, v[1]),
            Edge::normalize(v[1], LinkKind::Relates, v[0])
        );
    }

    #[test]
    fn blocked_by_cycles_are_rejected_in_either_spelling() {
        let v = ids(3);
        let edges = vec![
            Edge::normalize(v[0], LinkKind::Blocks, v[1]),
            Edge::normalize(v[1], LinkKind::Blocks, v[2]),
        ];
        let ty = |_| Some(TicketType::Task);
        assert!(check_add(&edges, &ty, v[2], LinkKind::Blocks, v[0]).is_err());
        assert!(check_add(&edges, &ty, v[0], LinkKind::BlockedBy, v[2]).is_err());
        assert!(check_add(&edges, &ty, v[0], LinkKind::Blocks, v[2]).is_ok());
        assert!(check_add(&edges, &ty, v[0], LinkKind::Blocks, v[0]).is_err());
    }

    #[test]
    fn single_origin_and_duplicate_rules() {
        let v = ids(4);
        let ty = |_| Some(TicketType::Task);
        let edges = vec![Edge::normalize(v[0], LinkKind::Splits, v[1])];
        assert!(check_add(&edges, &ty, v[2], LinkKind::Splits, v[1]).is_err());
        assert!(check_add(&edges, &ty, v[0], LinkKind::Splits, v[1]).is_ok());
        let edges = vec![Edge::normalize(v[0], LinkKind::Duplicates, v[1])];
        assert!(check_add(&edges, &ty, v[2], LinkKind::Duplicates, v[0]).is_err());
        assert!(check_add(&edges, &ty, v[1], LinkKind::Duplicates, v[3]).is_err());
    }

    #[test]
    fn enabler_needs_a_story_target() {
        let v = ids(2);
        let story = |_| Some(TicketType::Story);
        let task = |_| Some(TicketType::Task);
        assert!(check_add(&[], &story, v[0], LinkKind::EnablerFor, v[1]).is_ok());
        assert!(check_add(&[], &task, v[0], LinkKind::EnablerFor, v[1]).is_err());
    }

    #[test]
    fn parent_chain_cycles_are_rejected() {
        let v = ids(3);
        let parents = |t: TicketId| {
            if t == v[1] {
                Some(v[0])
            } else if t == v[2] {
                Some(v[1])
            } else {
                None
            }
        };
        assert!(check_parent(&parents, v[0], v[2]).is_err());
        assert!(check_parent(&parents, v[2], v[0]).is_ok());
        assert!(check_parent(&parents, v[1], v[1]).is_err());
    }
}
