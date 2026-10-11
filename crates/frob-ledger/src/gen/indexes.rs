//! `indexes/*.md`: the ticket lists by status, milestone, component, readiness, blocker, recency
//! and month done (`navigation.md` section 3.1).
//!
//! Every page is a pure function of the tree: no timestamps, an "as of" event line, stable row
//! order and a cap on rows per table so no page grows without bound. Milestones and components
//! come from the `milestone:` and `area:` labels.
// frob:ticket 01M3ZX864QGR220FTRGCDPXYZD

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use crate::doc;
use crate::id::{TicketId, compute_handles, display_handle};
use crate::layout::EVENTS_DIR;
use crate::links::edges_of;
use crate::model::{Category, Frontmatter, LinkKind, Priority};
use crate::reindex::{GENERATED_MARKER_PREFIX, GenInput};

/// Directory of the index pages on the ticket branch.
pub const DIR: &str = "indexes";

/// Most rows one table lists before it points at the by-id lookup.
pub const ROW_CAP: usize = 200;

/// Events listed by `recent.md`.
pub const RECENT_EVENTS: usize = 50;

/// Label prefix naming a ticket's milestone.
const MILESTONE_PREFIX: &str = "milestone:";

/// Label prefix naming a ticket's component.
const COMPONENT_PREFIX: &str = "area:";

/// One ticket as the index pages see it.
pub(super) struct Row {
    pub(super) id: TicketId,
    pub(super) handle: String,
    pub(super) front: Frontmatter,
    pub(super) body: String,
    pub(super) path: String,
    /// Open tickets that block this one.
    pub(super) blockers: Vec<TicketId>,
}

/// Escape `text` for one table cell.
pub(super) fn cell(text: &str) -> String {
    text.replace('|', "\\|").replace(['\n', '\r'], " ")
}

/// Position of `p` in the ascending priority order.
fn priority_rank(p: Priority) -> usize {
    Priority::ALL.iter().position(|x| *x == p).unwrap_or(0)
}

/// Sort key: highest priority first, then fewest points (unpointed last), then id.
fn ranked(r: &Row) -> (std::cmp::Reverse<usize>, u8, TicketId) {
    (
        std::cmp::Reverse(priority_rank(r.front.priority)),
        r.front.points.map_or(u8::MAX, crate::model::Points::get),
        r.id,
    )
}

pub(super) fn header(input: &GenInput<'_>, title: &str, intro: &str) -> String {
    format!(
        "{GENERATED_MARKER_PREFIX} v{}: DO NOT EDIT -->\n# {title}\n\nAs of event {}. {intro}\n\n",
        input.version,
        input.as_of.unwrap_or("none"),
    )
}

/// An extra table column: its header and how to fill a row.
type Extra<'a> = (&'a str, &'a dyn Fn(&Row) -> String);

/// A table of `rows` (capped), with an optional extra column.
fn table(rows: &[&Row], extra: Option<Extra<'_>>) -> String {
    let mut out = String::from("| Handle | Title | Priority | Points | Path |");
    let mut rule = String::from("|---|---|---|---|---|");
    if let Some((name, _)) = extra {
        let _ = write!(out, " {name} |");
        rule.push_str("---|");
    }
    let _ = write!(out, "\n{rule}\n");
    for r in rows.iter().take(ROW_CAP) {
        let _ = write!(
            out,
            "| {} | {} | {} | {} | [{}](../{}) |",
            r.handle,
            cell(&r.front.title),
            r.front.priority,
            r.front
                .points
                .map_or_else(|| "-".to_owned(), |p| p.get().to_string()),
            cell(&r.path),
            r.path.replace(' ', "%20"),
        );
        if let Some((_, f)) = extra {
            let _ = write!(out, " {} |", cell(&f(r)));
        }
        out.push('\n');
    }
    if rows.len() > ROW_CAP {
        let _ = writeln!(
            out,
            "\n{} more not shown; find any ticket in [by-id](by-id/).",
            rows.len() - ROW_CAP
        );
    }
    out
}

/// One `## name` section per group, in key order.
fn grouped(groups: &BTreeMap<String, Vec<&Row>>) -> String {
    let mut out = String::new();
    for (name, rows) in groups {
        let _ = write!(out, "## {name} ({})\n\n{}\n", rows.len(), table(rows, None));
    }
    out
}

pub(super) fn load(input: &GenInput<'_>) -> Vec<Row> {
    let ids: Vec<TicketId> = input.paths.keys().copied().collect();
    let handles = compute_handles(&ids, input.handle_min_len);
    let mut fronts: BTreeMap<TicketId, Frontmatter> = BTreeMap::new();
    let mut bodies: BTreeMap<TicketId, String> = BTreeMap::new();
    for (id, path) in input.paths {
        let parsed = input
            .tree
            .get(path)
            .and_then(|b| std::str::from_utf8(b).ok())
            .and_then(|t| doc::parse(path, t).ok());
        if let Some(t) = parsed {
            bodies.insert(*id, t.body);
            fronts.insert(*id, t.front);
        }
    }
    let mut blockers: BTreeMap<TicketId, Vec<TicketId>> = BTreeMap::new();
    for front in fronts.values() {
        for e in edges_of(front) {
            let open = fronts
                .get(&e.from)
                .is_some_and(|b| !b.category.is_terminal());
            if e.kind == LinkKind::Blocks && open {
                blockers.entry(e.to).or_default().push(e.from);
            }
        }
    }
    let handle_of: BTreeMap<TicketId, String> = ids
        .iter()
        .zip(&handles)
        .map(|(id, h)| (*id, display_handle(h)))
        .collect();
    fronts
        .into_iter()
        .map(|(id, front)| {
            let mut b = blockers.remove(&id).unwrap_or_default();
            b.sort();
            b.dedup();
            Row {
                id,
                handle: handle_of[&id].clone(),
                path: input.paths[&id].clone(),
                body: bodies.remove(&id).unwrap_or_default(),
                front,
                blockers: b,
            }
        })
        .collect()
}

/// `ready.md`: todo tickets with no open blocker, best first.
fn ready_page(input: &GenInput<'_>, rows: &[Row]) -> String {
    let mut ready: Vec<&Row> = rows
        .iter()
        .filter(|r| r.front.category == Category::Todo && r.blockers.is_empty())
        .collect();
    ready.sort_by_key(|r| ranked(r));
    let intro = "Doable and unblocked, ranked by priority, then fewest points.";
    format!("{}{}", header(input, "Ready", intro), table(&ready, None))
}

/// `blocked.md`: open tickets with an open blocker, naming each blocker.
fn blocked_page(input: &GenInput<'_>, rows: &[Row]) -> String {
    let handles: BTreeMap<TicketId, &str> =
        rows.iter().map(|r| (r.id, r.handle.as_str())).collect();
    let mut blocked: Vec<&Row> = rows
        .iter()
        .filter(|r| !r.front.category.is_terminal() && !r.blockers.is_empty())
        .collect();
    blocked.sort_by_key(|r| ranked(r));
    let names = |r: &Row| {
        r.blockers
            .iter()
            .map(|b| handles.get(b).copied().unwrap_or("?"))
            .collect::<Vec<_>>()
            .join(", ")
    };
    let intro = "Open tickets waiting on an open blocker.";
    format!(
        "{}{}",
        header(input, "Blocked", intro),
        table(&blocked, Some(("Blocked by", &names)))
    )
}

/// `recent.md`: the newest [`RECENT_EVENTS`] events, newest first.
fn recent_page(input: &GenInput<'_>, rows: &[Row]) -> String {
    let prefix = format!("{EVENTS_DIR}/");
    let mut events: Vec<(&str, &str, &[u8])> = input
        .tree
        .iter()
        .filter_map(|(p, bytes)| {
            let rest = p.strip_prefix(&prefix)?;
            let (ticket, file) = rest.split_once('/')?;
            Some((file.strip_suffix(".toml")?, ticket, bytes.as_slice()))
        })
        .collect();
    events.sort_by(|a, b| b.0.cmp(a.0));
    let by_id: BTreeMap<String, &Row> = rows.iter().map(|r| (r.id.to_string(), r)).collect();
    let mut out = header(
        input,
        "Recent",
        &format!("The last {RECENT_EVENTS} events, newest first."),
    );
    out.push_str("| Event | Kind | Ticket | Title |\n|---|---|---|---|\n");
    for (event, ticket, bytes) in events.into_iter().take(RECENT_EVENTS) {
        let kind = std::str::from_utf8(bytes)
            .ok()
            .and_then(|t| t.lines().find_map(|l| l.strip_prefix("kind = ")))
            .map_or_else(String::new, |k| k.trim_matches('"').to_owned());
        let (handle, title) = by_id.get(ticket).map_or((ticket, ""), |r| {
            (r.handle.as_str(), r.front.title.as_str())
        });
        let _ = writeln!(
            out,
            "| {event} | {} | {handle} | {} |",
            cell(&kind),
            cell(title)
        );
    }
    out
}

/// Tickets grouped for the list pages.
struct Groups<'a> {
    by_status: BTreeMap<String, Vec<&'a Row>>,
    by_milestone: BTreeMap<String, Vec<&'a Row>>,
    by_component: BTreeMap<String, Vec<&'a Row>>,
    done_by_month: BTreeMap<String, Vec<&'a Row>>,
}

/// Group `rows` by status, milestone, component and month done, each group in rank order.
fn group(rows: &[Row]) -> Groups<'_> {
    let mut by_status: BTreeMap<String, Vec<&Row>> = BTreeMap::new();
    for c in Category::ALL {
        by_status.insert(c.as_str().to_owned(), Vec::new());
    }
    let mut by_milestone: BTreeMap<String, Vec<&Row>> = BTreeMap::new();
    let mut by_component: BTreeMap<String, Vec<&Row>> = BTreeMap::new();
    let mut done_by_month: BTreeMap<String, Vec<&Row>> = BTreeMap::new();
    for r in rows {
        by_status
            .entry(r.front.category.as_str().to_owned())
            .or_default()
            .push(r);
        let label = |prefix: &str| -> BTreeSet<String> {
            r.front
                .labels
                .iter()
                .filter_map(|l| l.strip_prefix(prefix))
                .map(str::to_owned)
                .collect()
        };
        let mut ms = label(MILESTONE_PREFIX);
        if ms.is_empty() {
            ms.insert("(none)".to_owned());
        }
        for m in ms {
            by_milestone.entry(m).or_default().push(r);
        }
        let mut cs = label(COMPONENT_PREFIX);
        if cs.is_empty() {
            cs.insert("(none)".to_owned());
        }
        for c in cs {
            by_component.entry(c).or_default().push(r);
        }
        if r.front.category.is_terminal() {
            let month: String = r.front.updated.to_string().chars().take(7).collect();
            done_by_month.entry(month).or_default().push(r);
        }
    }
    for list in by_status
        .values_mut()
        .chain(by_milestone.values_mut())
        .chain(by_component.values_mut())
    {
        list.sort_by_key(|r| ranked(r));
    }
    for list in done_by_month.values_mut() {
        list.sort_by(|a, b| b.front.updated.cmp(&a.front.updated).then(a.id.cmp(&b.id)));
    }
    Groups {
        by_status,
        by_milestone,
        by_component,
        done_by_month,
    }
}

/// Render every index page.
#[must_use]
pub fn render(input: &GenInput<'_>) -> Vec<(String, Vec<u8>)> {
    let rows = load(input);
    let mut pages: Vec<(String, String)> = Vec::new();

    let Groups {
        by_status,
        by_milestone,
        by_component,
        done_by_month,
    } = group(&rows);
    pages.push((
        "by-status".into(),
        format!(
            "{}{}",
            header(input, "Tickets by status", "Highest priority first."),
            grouped(&by_status)
        ),
    ));
    pages.push((
        "by-milestone".into(),
        format!(
            "{}{}",
            header(
                input,
                "Tickets by milestone",
                "From the `milestone:` labels."
            ),
            grouped(&by_milestone)
        ),
    ));
    pages.push((
        "by-component".into(),
        format!(
            "{}{}",
            header(input, "Tickets by component", "From the `area:` labels."),
            grouped(&by_component)
        ),
    ));
    pages.push(("ready".into(), ready_page(input, &rows)));
    pages.push(("blocked".into(), blocked_page(input, &rows)));
    pages.push(("recent".into(), recent_page(input, &rows)));
    let mut map = String::from(
        "- [by-status](by-status.md)\n- [by-milestone](by-milestone.md)\n- [by-component](by-component.md)\n- [ready](ready.md)\n- [blocked](blocked.md)\n- [recent](recent.md)\n- [by-id](by-id/): the permanent lookup\n",
    );
    for (month, list) in &done_by_month {
        let intro = "Done tickets, newest first.";
        pages.push((
            format!("done/{month}"),
            format!(
                "{}{}",
                header(input, &format!("Done in {month}"), intro),
                table(list, None)
            ),
        ));
        let _ = writeln!(map, "- [done/{month}](done/{month}.md)");
    }
    pages.push((
        "README".into(),
        format!(
            "{}{map}",
            header(input, "Indexes", "Generated lists; never edited by hand.")
        ),
    ));

    pages
        .into_iter()
        .map(|(name, text)| (format!("{DIR}/{name}.md"), text.into_bytes()))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Class, Link, Stamp, Ticket, TicketType};
    use crate::reindex::Tree;

    fn put(
        tree: &mut Tree,
        paths: &mut BTreeMap<TicketId, String>,
        title: &str,
        cat: Category,
        pri: Priority,
        links: Vec<Link>,
        labels: Vec<String>,
    ) -> TicketId {
        let id = TicketId::mint();
        let front = Frontmatter {
            id,
            title: title.into(),
            ty: TicketType::Task,
            flavour: None,
            category: cat,
            outcome: cat.is_terminal().then_some(crate::model::Outcome::Fixed),
            priority: pri,
            class: Class::Standard,
            due: None,
            points: None,
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
            labels,
            scope: vec![],
            links,
            acceptance: vec![],
        };
        let path = format!("_unfiled/{}.md", title.replace(' ', "-"));
        let text = doc::render(&Ticket {
            front,
            body: "b".into(),
        })
        .expect("render");
        tree.insert(path.clone(), text.into_bytes());
        paths.insert(id, path);
        id
    }

    fn page(out: &[(String, Vec<u8>)], name: &str) -> String {
        let bytes = &out
            .iter()
            .find(|(p, _)| p == name)
            .unwrap_or_else(|| panic!("no {name}"))
            .1;
        String::from_utf8(bytes.clone()).expect("utf8")
    }

    fn run(tree: &Tree, paths: &BTreeMap<TicketId, String>) -> Vec<(String, Vec<u8>)> {
        render(&GenInput {
            tree,
            version: "9.9.9",
            handle_min_len: 26,
            as_of: Some("EV"),
            paths,
        })
    }

    #[test]
    fn ready_lists_only_unblocked_todo_by_priority_and_blocked_names_the_blocker() {
        let (mut tree, mut paths) = (Tree::new(), BTreeMap::new());
        let low = put(
            &mut tree,
            &mut paths,
            "Low one",
            Category::Todo,
            Priority::Low,
            vec![],
            vec![],
        );
        let high = put(
            &mut tree,
            &mut paths,
            "High one",
            Category::Todo,
            Priority::High,
            vec![],
            vec![],
        );
        let waits = put(
            &mut tree,
            &mut paths,
            "Waits",
            Category::Todo,
            Priority::Critical,
            vec![Link {
                kind: LinkKind::BlockedBy,
                target: low,
            }],
            vec![],
        );
        let out = run(&tree, &paths);
        let ready = page(&out, "indexes/ready.md");
        let (hi, lo) = (
            ready.find("High one").expect("high"),
            ready.find("Low one").expect("low"),
        );
        assert!(hi < lo, "ranked by priority: {ready}");
        assert!(!ready.contains("Waits"), "{ready}");
        let blocked = page(&out, "indexes/blocked.md");
        assert!(
            blocked.contains("Waits") && !blocked.contains("High one"),
            "{blocked}"
        );
        let all: Vec<TicketId> = paths.keys().copied().collect();
        let hs = compute_handles(&all, 26);
        let low_handle = display_handle(&hs[all.iter().position(|i| *i == low).expect("low")]);
        assert!(
            blocked.contains(&low_handle),
            "names blocker {low_handle}: {blocked}"
        );
        let _ = (high, waits);
    }

    #[test]
    fn a_done_blocker_no_longer_blocks() {
        let (mut tree, mut paths) = (Tree::new(), BTreeMap::new());
        let done = put(
            &mut tree,
            &mut paths,
            "Finished",
            Category::Done,
            Priority::Low,
            vec![],
            vec![],
        );
        put(
            &mut tree,
            &mut paths,
            "Free now",
            Category::Todo,
            Priority::Low,
            vec![Link {
                kind: LinkKind::BlockedBy,
                target: done,
            }],
            vec![],
        );
        let out = run(&tree, &paths);
        assert!(page(&out, "indexes/ready.md").contains("Free now"));
        assert!(!page(&out, "indexes/blocked.md").contains("Free now"));
    }

    #[test]
    fn recent_lists_the_last_fifty_of_eighty_events_newest_first() {
        let (mut tree, mut paths) = (Tree::new(), BTreeMap::new());
        let t = put(
            &mut tree,
            &mut paths,
            "Subject",
            Category::Todo,
            Priority::Low,
            vec![],
            vec![],
        );
        for n in 0..80u32 {
            let ev = format!("01M3ZX85S7ASFGT31GDY{n:06}");
            tree.insert(
                format!("{EVENTS_DIR}/{t}/{ev}.toml"),
                b"kind = \"comment\"\n".to_vec(),
            );
        }
        let recent = page(&run(&tree, &paths), "indexes/recent.md");
        let listed = recent
            .lines()
            .filter(|l| l.starts_with("| 01M3ZX85S7ASFGT31GDY"))
            .count();
        assert_eq!(listed, 50, "{recent}");
        assert!(
            recent.contains("GDY000079") && !recent.contains("GDY000029"),
            "{recent}"
        );
    }

    #[test]
    fn milestone_component_and_month_pages_group_by_label_and_update_month() {
        let (mut tree, mut paths) = (Tree::new(), BTreeMap::new());
        put(
            &mut tree,
            &mut paths,
            "Labelled",
            Category::Done,
            Priority::Low,
            vec![],
            vec!["milestone:2".into(), "area:navigation".into()],
        );
        let out = run(&tree, &paths);
        assert!(page(&out, "indexes/by-milestone.md").contains("## 2 (1)"));
        assert!(page(&out, "indexes/by-component.md").contains("## navigation (1)"));
        assert!(out.iter().any(|(p, _)| p.starts_with("indexes/done/20")));
    }

    #[test]
    fn tables_are_capped() {
        let (mut tree, mut paths) = (Tree::new(), BTreeMap::new());
        for n in 0..(ROW_CAP + 5) {
            put(
                &mut tree,
                &mut paths,
                &format!("T{n}"),
                Category::Todo,
                Priority::Low,
                vec![],
                vec![],
            );
        }
        let ready = page(&run(&tree, &paths), "indexes/ready.md");
        assert!(ready.contains("5 more not shown"), "{ready}");
    }
}
