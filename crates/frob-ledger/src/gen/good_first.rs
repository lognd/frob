//! `indexes/good-first.md`: ready `good-first` tickets, smallest first, with their `## Start here`
//! notes inline (`navigation.md` section 4.2).
//!
//! The selection helpers here are shared with `frob ticket doable --newcomer`, so the page and the
//! verb order tickets identically.
// frob:ticket 01M3ZX87QPD21PCSSSAJHVK7HJ

use std::fmt::Write as _;

use super::indexes::{Row, cell, header, load};
use crate::id::TicketId;
use crate::model::Category;
use crate::reindex::GenInput;

/// Branch-relative path of the page.
pub const PATH: &str = "indexes/good-first.md";

/// The label that marks a ticket as good-first (the same string `PM031` checks).
pub const LABEL: &str = "good-first";

/// Heading that opens the start notes of a ticket body.
const START_HEADING: &str = "## Start here";

/// True when `labels` carry the good-first label.
#[must_use]
pub fn is_good_first(labels: &[String]) -> bool {
    labels.iter().any(|l| l == LABEL)
}

/// The text of the `## Start here` section of `body`, without its heading, or `None` when absent.
#[must_use]
pub fn start_here(body: &str) -> Option<String> {
    let mut lines = body.lines().skip_while(|l| l.trim_end() != START_HEADING);
    lines.next()?;
    let text: Vec<&str> = lines.take_while(|l| !l.starts_with("## ")).collect();
    let text = text.join("\n").trim().to_owned();
    (!text.is_empty()).then_some(text)
}

/// Sort key shared by the page and the verb: fewest points first (unpointed last), then id.
#[must_use]
pub fn order_key(points: Option<u8>, id: TicketId) -> (u8, TicketId) {
    (points.unwrap_or(u8::MAX), id)
}

/// Render `indexes/good-first.md`.
#[must_use]
pub fn render(input: &GenInput<'_>) -> Vec<(String, Vec<u8>)> {
    let rows = load(input);
    let mut ready: Vec<&Row> = rows
        .iter()
        .filter(|r| {
            r.front.category == Category::Todo
                && r.blockers.is_empty()
                && is_good_first(&r.front.labels)
        })
        .collect();
    ready.sort_by_key(|r| order_key(r.front.points.map(crate::model::Points::get), r.id));
    let mut out = header(
        input,
        "Good first tickets",
        "Ready good-first tickets, smallest first, with their start notes.",
    );
    if ready.is_empty() {
        out.push_str("None are ready right now.\n");
    }
    for r in ready {
        let points = r
            .front
            .points
            .map_or_else(|| "-".to_owned(), |p| p.get().to_string());
        let _ = write!(
            out,
            "## {} {}\n\nPoints: {points}. [{}](../{})\n\n",
            r.handle,
            cell(&r.front.title),
            cell(&r.path),
            r.path.replace(' ', "%20"),
        );
        let _ = writeln!(
            out,
            "{}\n",
            start_here(&r.body).unwrap_or_else(|| "No start notes.".to_owned())
        );
    }
    vec![(PATH.to_owned(), out.into_bytes())]
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    use crate::doc;
    use crate::model::{Class, Frontmatter, Points, Priority, Stamp, Ticket, TicketType};
    use crate::reindex::Tree;

    fn put(
        tree: &mut Tree,
        paths: &mut BTreeMap<TicketId, String>,
        title: &str,
        points: u8,
        labels: &[&str],
        cat: Category,
    ) {
        let id = TicketId::mint();
        let front = Frontmatter {
            id,
            title: title.into(),
            ty: TicketType::Task,
            flavour: None,
            category: cat,
            outcome: None,
            priority: Priority::Medium,
            class: Class::Standard,
            due: None,
            points: Some(Points::new(points).expect("points")),
            parent: None,
            reporter: "t".into(),
            assignee: None,
            created: Stamp::from_unix(1_790_000_000),
            updated: Stamp::from_unix(1_790_000_000),
            persona: None,
            capability: None,
            outcome_text: None,
            idempotency_key: None,
            aliases: vec![],
            labels: labels.iter().map(|l| (*l).to_owned()).collect(),
            scope: vec![],
            links: vec![],
            acceptance: vec![],
        };
        let body = format!("Intro.\n\n## Start here\n\nRead {title}.rs first.\n\n## Other\n\nx");
        let path = format!("_unfiled/{}.md", title.replace(' ', "-"));
        tree.insert(
            path.clone(),
            doc::render(&Ticket { front, body })
                .expect("render")
                .into_bytes(),
        );
        paths.insert(id, path);
    }

    #[test]
    fn page_lists_ready_good_first_smallest_first_with_start_notes() {
        let (mut tree, mut paths) = (Tree::new(), BTreeMap::new());
        put(&mut tree, &mut paths, "Two a", 2, &[LABEL], Category::Todo);
        put(&mut tree, &mut paths, "One", 1, &[LABEL], Category::Todo);
        put(&mut tree, &mut paths, "Two b", 2, &[LABEL], Category::Todo);
        put(&mut tree, &mut paths, "Unlabelled", 1, &[], Category::Todo);
        put(
            &mut tree,
            &mut paths,
            "Started",
            1,
            &[LABEL],
            Category::InProgress,
        );
        let out = render(&GenInput {
            tree: &tree,
            version: "9",
            handle_min_len: 26,
            as_of: None,
            paths: &paths,
        });
        let page = String::from_utf8(out[0].1.clone()).expect("utf8");
        assert!(
            !page.contains("Unlabelled") && !page.contains("Started"),
            "{page}"
        );
        let one = page.find(" One\n").expect("one");
        assert!(one < page.find("Read Two a.rs").expect("a notes"), "{page}");
        assert!(
            page.contains("Read One.rs first.") && !page.contains("## Other"),
            "{page}"
        );
        // The two 2-point tickets follow in id order, the order the verb uses too.
        let ids: Vec<&TicketId> = paths
            .iter()
            .filter(|(_, p)| p.contains("Two"))
            .map(|(i, _)| i)
            .collect();
        let first = if ids[0] < ids[1] { "Two a" } else { "Two b" };
        let second = if first == "Two a" { "Two b" } else { "Two a" };
        assert!(
            page.find(first).expect("f") < page.find(second).expect("s"),
            "{page}"
        );
    }

    #[test]
    fn start_here_stops_at_the_next_heading() {
        assert_eq!(
            start_here("a\n## Start here\nx\ny\n## Z\nq").as_deref(),
            Some("x\ny")
        );
        assert_eq!(start_here("## Start here\n\n"), None);
        assert_eq!(start_here("### Start here\nx"), None);
    }
}
