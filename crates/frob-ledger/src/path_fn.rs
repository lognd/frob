//! The ticket path function (navigation.md 2.1): where every ticket file lives on the ticket branch.
//!
//! A pure function of the whole ticket set, so the answer never depends on creation order:
//! `<top-epic-slug>/<ticket-slug>.md`, sub-epics flattened into the top epic's directory, a top
//! epic's own ticket at `<slug>/EPIC.md`, tickets without an epic in `_unfiled/`. Two tickets
//! that would share a path both get `-<handle>` appended.
// frob:ticket 01M3ZX82K7HX9D2VKT25KS4MV2

use std::collections::BTreeMap;

use crate::id::{TicketId, compute_handles};
use crate::layout::{EPIC_FILE, UNFILED_DIR, title_slug};
use crate::model::TicketType;

/// The fields of a ticket the path depends on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PathTicket {
    /// The ticket's id.
    pub id: TicketId,
    /// Its type; an epic without an epic ancestor owns a directory.
    pub ty: TicketType,
    /// Its current title, which the slug follows.
    pub title: String,
    /// Its parent, when it has one.
    pub parent: Option<TicketId>,
}

/// Most parent hops followed when looking for the top epic (a cycle guard).
const MAX_DEPTH: usize = 64;

/// The id of the outermost epic ancestor of `t` (itself when `t` is an epic with none), if any.
fn top_epic(by_id: &BTreeMap<TicketId, &PathTicket>, t: &PathTicket) -> Option<TicketId> {
    let mut top = (t.ty == TicketType::Epic).then_some(t.id);
    let mut cur = t.parent;
    for _ in 0..MAX_DEPTH {
        let Some(p) = cur.and_then(|id| by_id.get(&id)) else {
            break;
        };
        if p.ty == TicketType::Epic {
            top = Some(p.id);
        }
        cur = p.parent;
    }
    top
}

/// Append `-<handle>` to every entry of `names` that another entry shares, in place.
fn disambiguate(names: &mut BTreeMap<TicketId, String>, handles: &BTreeMap<TicketId, String>) {
    let mut count: BTreeMap<String, usize> = BTreeMap::new();
    for n in names.values() {
        *count.entry(n.clone()).or_default() += 1;
    }
    for (id, n) in names.iter_mut() {
        if count[n.as_str()] > 1 {
            n.push('-');
            n.push_str(&handles[id]);
        }
    }
}

/// The branch-relative path of every ticket in `tickets`; `handle_min_len` is `[tickets] handle_min_len`.
///
/// Top epics that share a slug both get `-<handle>` on their directory, and tickets that share a
/// slug within one directory both get it on their file name, whatever order they were created in.
pub fn ticket_paths(tickets: &[PathTicket], handle_min_len: usize) -> BTreeMap<TicketId, String> {
    let ids: Vec<TicketId> = tickets.iter().map(|t| t.id).collect();
    let handles: BTreeMap<TicketId, String> = ids
        .iter()
        .copied()
        .zip(compute_handles(&ids, handle_min_len))
        .collect();
    let by_id: BTreeMap<TicketId, &PathTicket> = tickets.iter().map(|t| (t.id, t)).collect();
    let slug = |t: &PathTicket| title_slug(&t.title, &handles[&t.id]);

    // Directory slug of each top epic, made unique among top epics.
    let tops: BTreeMap<TicketId, Option<TicketId>> = tickets
        .iter()
        .map(|t| (t.id, top_epic(&by_id, t)))
        .collect();
    let mut dirs: BTreeMap<TicketId, String> = tops
        .values()
        .flatten()
        .filter_map(|id| by_id.get(id).map(|t| (*id, slug(t))))
        .collect();
    disambiguate(&mut dirs, &handles);

    // File stem of every ticket that is not a top epic, unique within its directory.
    let mut stems: BTreeMap<(String, TicketId), String> = BTreeMap::new();
    let dir_of = |t: &PathTicket| match tops[&t.id] {
        Some(top) => dirs[&top].clone(),
        None => UNFILED_DIR.to_owned(),
    };
    let mut by_dir: BTreeMap<String, BTreeMap<TicketId, String>> = BTreeMap::new();
    for t in tickets.iter().filter(|t| tops[&t.id] != Some(t.id)) {
        by_dir.entry(dir_of(t)).or_default().insert(t.id, slug(t));
    }
    for (dir, names) in &mut by_dir {
        disambiguate(names, &handles);
        for (id, n) in names.iter() {
            stems.insert((dir.clone(), *id), n.clone());
        }
    }

    tickets
        .iter()
        .map(|t| {
            let path = if tops[&t.id] == Some(t.id) {
                format!("{}/{EPIC_FILE}", dirs[&t.id])
            } else {
                let dir = dir_of(t);
                let stem = &stems[&(dir.clone(), t.id)];
                format!("{dir}/{stem}.md")
            };
            (t.id, path)
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn t(ty: TicketType, title: &str, parent: Option<TicketId>) -> PathTicket {
        PathTicket {
            id: TicketId::mint(),
            ty,
            title: title.to_owned(),
            parent,
        }
    }

    #[test]
    fn sub_epic_tickets_sit_in_the_top_epic_directory() {
        // frob:tests crates/frob-ledger/src/path_fn.rs::ticket_paths
        let top = t(TicketType::Epic, "Parser rewrite", None);
        let sub = t(TicketType::Epic, "Lexer", Some(top.id));
        let leaf = t(TicketType::Task, "Fix tokens", Some(sub.id));
        let paths = ticket_paths(&[top.clone(), sub.clone(), leaf.clone()], 7);
        assert_eq!(paths[&top.id], "parser-rewrite/EPIC.md");
        assert_eq!(paths[&sub.id], "parser-rewrite/lexer.md");
        assert_eq!(paths[&leaf.id], "parser-rewrite/fix-tokens.md");
    }

    #[test]
    fn a_ticket_without_an_epic_is_unfiled() {
        // frob:tests crates/frob-ledger/src/path_fn.rs::ticket_paths
        let a = t(TicketType::Task, "Loose end", None);
        assert_eq!(
            ticket_paths(std::slice::from_ref(&a), 7)[&a.id],
            "_unfiled/loose-end.md"
        );
    }

    #[test]
    fn same_slug_in_one_directory_gets_the_handle_in_either_order() {
        // frob:tests crates/frob-ledger/src/path_fn.rs::ticket_paths
        // frob:tests crates/frob-ledger/src/path_fn.rs::disambiguate
        let a = t(TicketType::Task, "Same title", None);
        let b = t(TicketType::Task, "Same title", None);
        let forward = ticket_paths(&[a.clone(), b.clone()], 7);
        let reverse = ticket_paths(&[b.clone(), a.clone()], 7);
        assert_eq!(forward, reverse);
        let ha = &compute_handles(&[a.id, b.id], 7)[0];
        assert_eq!(forward[&a.id], format!("_unfiled/same-title-{ha}.md"));
        assert_ne!(forward[&a.id], forward[&b.id]);
    }

    #[test]
    fn same_slug_in_different_directories_is_left_alone() {
        // frob:tests crates/frob-ledger/src/path_fn.rs::ticket_paths
        let e = t(TicketType::Epic, "Epic", None);
        let a = t(TicketType::Task, "Same", Some(e.id));
        let b = t(TicketType::Task, "Same", None);
        let paths = ticket_paths(&[e, a.clone(), b.clone()], 7);
        assert_eq!(paths[&a.id], "epic/same.md");
        assert_eq!(paths[&b.id], "_unfiled/same.md");
    }

    #[test]
    fn two_top_epics_with_one_slug_get_distinct_directories() {
        // frob:tests crates/frob-ledger/src/path_fn.rs::ticket_paths
        let a = t(TicketType::Epic, "Work", None);
        let b = t(TicketType::Epic, "Work", None);
        let paths = ticket_paths(&[a.clone(), b.clone()], 7);
        assert_ne!(paths[&a.id], paths[&b.id]);
        assert!(paths[&a.id].ends_with("/EPIC.md"));
    }
}
