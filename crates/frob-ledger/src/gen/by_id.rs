//! `indexes/by-id/<xx>.md`: the permanent lookup of every ticket by id (`navigation.md` section 1).
//!
//! A path is never a reference, so this page set is the stable place to find the current path of
//! an id. Tickets are split into pages by the two ULID characters after the 10-character time
//! part, which keeps every page small. The output is a pure function of the tree: no timestamps,
//! rows in id order, an "as of" event line.
// frob:ticket 01M3ZX868H7TQ34ZDPXY13NRRG

use std::collections::BTreeMap;
use std::fmt::Write as _;

use crate::doc;
use crate::id::{TicketId, compute_handles, display_handle};
use crate::reindex::{GENERATED_MARKER_PREFIX, GenInput};

/// Characters of a ULID taken by its time part.
const TIME_LEN: usize = 10;

/// Directory of the lookup pages on the ticket branch.
pub const DIR: &str = "indexes/by-id";

/// The page key of `id`: the two ULID characters after the time part.
#[must_use]
pub fn page_key(id: TicketId) -> String {
    id.to_string()[TIME_LEN..TIME_LEN + 2].to_owned()
}

/// The branch-relative path of the page that lists `id`.
#[must_use]
pub fn page_path(id: TicketId) -> String {
    format!("{DIR}/{}.md", page_key(id))
}

/// Escape `text` for one table cell.
fn cell(text: &str) -> String {
    text.replace('|', "\\|").replace(['\n', '\r'], " ")
}

/// Render one page per key that has tickets, listing ULID, handle, title and current path.
#[must_use]
pub fn render(input: &GenInput<'_>) -> Vec<(String, Vec<u8>)> {
    let ids: Vec<TicketId> = input.paths.keys().copied().collect();
    let handles = compute_handles(&ids, input.handle_min_len);
    let mut pages: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for (id, handle) in ids.iter().zip(&handles) {
        let path = &input.paths[id];
        let title = input
            .tree
            .get(path)
            .and_then(|b| std::str::from_utf8(b).ok())
            .and_then(|t| doc::parse(path, t).ok())
            .map(|p| p.front.title)
            .unwrap_or_default();
        let row = format!(
            "| {id} | {} | {} | [{}](../../{}) |\n",
            display_handle(handle),
            cell(&title),
            cell(path),
            path.replace(' ', "%20"),
        );
        pages.entry(page_key(*id)).or_default().push(row);
    }
    let as_of = input.as_of.unwrap_or("none");
    pages
        .into_iter()
        .map(|(key, rows)| {
            let mut out = format!(
                "{GENERATED_MARKER_PREFIX} v{}: DO NOT EDIT -->\n# Tickets by id: {key}\n\nAs of event {as_of}. Ids are permanent; the path changes when a ticket moves.\n\n| ULID | Handle | Title | Path |\n|---|---|---|---|\n",
                input.version
            );
            for row in rows {
                let _ = write!(out, "{row}");
            }
            (format!("{DIR}/{key}.md"), out.into_bytes())
        })
        .collect()
}
