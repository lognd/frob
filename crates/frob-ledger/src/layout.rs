//! On-disk layouts of the ledger and the pure path rules of the ticket-branch layout.
//!
//! Design: `mirror.md` section 1 and `navigation.md` section 2.1 (decision D79). On the
//! ticket branch a ticket file lives at `<top-epic-slug>/<ticket-slug>.md` and its events
//! at `.events/<ULID>/<event>.toml`; the ULID in the frontmatter stays canonical and no
//! reader ever resolves an id through a path. The legacy layout, `tickets/<ULID>/ticket.md`
//! plus `tickets/<ULID>/events/`, stays readable until the fold reads the new one.

use crate::id::TicketId;
use crate::model::TicketType;

/// Directory of event logs on the ticket branch, one `<ULID>` subdirectory per ticket.
pub const EVENTS_DIR: &str = ".events";
/// Directory of tickets that have no epic.
pub const UNFILED_DIR: &str = "_unfiled";
/// File name of a top epic's own ticket inside its directory.
pub const EPIC_FILE: &str = "EPIC.md";
/// Longest ticket slug, cut on a word boundary.
pub const SLUG_MAX: usize = 60;

/// Which storage layout a ledger reads and writes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Layout {
    /// `tickets/<ULID>/ticket.md` and `tickets/<ULID>/events/` under the configured directory.
    #[default]
    Dir,
    /// `<top-epic-slug>/<slug>.md` and `.events/<ULID>/` at the root of the ticket branch.
    Branch,
}

/// The slug of `title` per `navigation.md` 2.1; an empty result becomes the handle without `~`.
///
/// ASCII letters and digits are kept lowercased, every other run becomes one `-`, the ends are
/// trimmed and the result is cut at [`SLUG_MAX`] on a word boundary.
#[must_use]
pub fn title_slug(title: &str, handle_fallback: &str) -> String {
    let mut slug = String::new();
    for c in title.chars() {
        if c.is_ascii_alphanumeric() {
            slug.push(c.to_ascii_lowercase());
        } else if !slug.ends_with('-') {
            slug.push('-');
        }
    }
    let slug = slug.trim_matches('-');
    let slug = if slug.len() > SLUG_MAX {
        // Cut on a word boundary when one exists inside the limit, else hard.
        let cut = if slug.as_bytes()[SLUG_MAX] == b'-' {
            SLUG_MAX
        } else {
            slug[..SLUG_MAX].rfind('-').unwrap_or(SLUG_MAX)
        };
        slug[..cut].trim_matches('-')
    } else {
        slug
    };
    if slug.is_empty() {
        handle_fallback.to_owned()
    } else {
        slug.to_owned()
    }
}

/// Ticket-branch path of a ticket from its type, slug and the slug of its top epic.
///
/// `top_epic` is the directory slug of the outermost epic ancestor (sub-epics never get a
/// directory). A ticket that is itself an epic with no epic ancestor is `<slug>/EPIC.md`;
/// a ticket with no epic at all is `_unfiled/<slug>.md`.
#[must_use]
pub fn branch_ticket_path(ty: TicketType, slug: &str, top_epic: Option<&str>) -> String {
    match (top_epic, ty) {
        (Some(dir), _) => format!("{dir}/{slug}.md"),
        (None, TicketType::Epic) => format!("{slug}/{EPIC_FILE}"),
        (None, _) => format!("{UNFILED_DIR}/{slug}.md"),
    }
}

/// The directory of the event files of `id` on the ticket branch.
#[must_use]
pub fn branch_events_dir(id: TicketId) -> String {
    format!("{EVENTS_DIR}/{id}")
}

/// Whether `path` (branch-relative) can be a ticket file: a markdown file outside dot
/// directories that is not the generated front page.
#[must_use]
pub fn is_branch_ticket_candidate(path: &str) -> bool {
    path.ends_with(".md") && path != "README.md" && !path.starts_with('.') && path.contains('/')
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M3ZX82Q2N145P3DWVVY4E868
    #[test]
    fn slugs_follow_the_title() {
        assert_eq!(title_slug("Hello, World -- v2!", "abc"), "hello-world-v2");
        assert_eq!(title_slug("!!!", "abc1234"), "abc1234");
        let long = "word ".repeat(30);
        let s = title_slug(&long, "x");
        assert!(s.len() <= SLUG_MAX && s.ends_with("word"), "{s}");
    }

    // frob:ticket 01M3ZX82Q2N145P3DWVVY4E868
    #[test]
    fn paths_are_flat_under_the_top_epic() {
        assert_eq!(
            branch_ticket_path(TicketType::Task, "a", Some("epic")),
            "epic/a.md"
        );
        assert_eq!(
            branch_ticket_path(TicketType::Epic, "epic", None),
            "epic/EPIC.md"
        );
        assert_eq!(
            branch_ticket_path(TicketType::Task, "a", None),
            "_unfiled/a.md"
        );
        assert!(is_branch_ticket_candidate("epic/a.md"));
        assert!(!is_branch_ticket_candidate(".events/x/y.toml"));
        assert!(!is_branch_ticket_candidate("README.md"));
    }
}
