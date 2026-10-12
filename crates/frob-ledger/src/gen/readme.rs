//! `README.md` of the ticket branch: the front door (`navigation.md` sections 3.1 and 3.3).
//!
//! `_unfiled` tickets come first, grouped by status, then one row per epic linking its page.
//! A pure function of the tree: no timestamps, an "as of" event line, stable order.
// frob:ticket 01M3ZX860YGPCJE6ETPJADMNFE

use std::fmt::Write as _;

use crate::layout::UNFILED_DIR;
use crate::reindex::GenInput;

use super::epic::{self, by_dir, dir_of, status_sections, top_of};
use super::indexes::{Row, cell, header, load};

/// Branch-relative path of the front door.
pub const PATH: &str = "README.md";

/// Render the front door.
#[must_use]
pub fn render(input: &GenInput<'_>) -> Vec<(String, Vec<u8>)> {
    let rows = load(input);
    let unfiled: Vec<&Row> = rows
        .iter()
        .filter(|r| dir_of(&r.path) == Some(UNFILED_DIR))
        .collect();
    let mut page = header(
        input,
        "Tickets",
        "Start with [GLOSSARY](GLOSSARY.md) for the vocabulary and [indexes](indexes/README.md) for lists.",
    );
    let _ = write!(
        page,
        "## {UNFILED_DIR} ({})\n\nTickets without an epic.\n\n{}",
        unfiled.len(),
        status_sections(&unfiled, None, "###")
    );
    page.push_str("## Epics\n\n| Epic | Handle | Open | Done | Page |\n|---|---|---|---|---|\n");
    for (dir, members) in by_dir(&rows) {
        let top = top_of(dir, &members);
        let done = members
            .iter()
            .filter(|r| r.front.category.is_terminal())
            .count();
        let _ = writeln!(
            page,
            "| {} | {} | {} | {done} | [{dir}/]({dir}/{}) |",
            cell(top.map_or(dir, |t| t.front.title.as_str())),
            top.map_or("-", |t| t.handle.as_str()),
            members.len() - done,
            epic::PAGE,
        );
    }
    vec![(PATH.to_owned(), page.into_bytes())]
}
