//! `TOUR.md` has five stops and pins its examples deterministically (`navigation.md` section 5).
// frob:ticket 01M3ZX887RZB82G8HR5JKQ2FER

use std::collections::BTreeMap;

use frob_ledger::doc;
use frob_ledger::event::{Event, EventBody, EvidenceData, LandData};
use frob_ledger::r#gen::GENERATORS;
use frob_ledger::r#gen::tour::{self, Pins};
use frob_ledger::id::TicketId;
use frob_ledger::model::{
    Category, Class, Frontmatter, Outcome, Priority, Stamp, Ticket, TicketType,
};
use frob_ledger::reindex::{GenInput, ReindexOptions, Tree, reindex};

fn put(
    tree: &mut Tree,
    title: &str,
    ty: TicketType,
    parent: Option<TicketId>,
    done: bool,
    good_first: bool,
) -> TicketId {
    let id = TicketId::mint();
    let front = Frontmatter {
        id,
        title: title.into(),
        ty,
        flavour: None,
        category: if done { Category::Done } else { Category::Todo },
        outcome: done.then_some(Outcome::Fixed),
        priority: Priority::Medium,
        class: Class::Standard,
        due: None,
        points: None,
        parent,
        reporter: "t".into(),
        assignee: None,
        created: Stamp::from_unix(1_790_000_000),
        updated: Stamp::from_unix(1_790_000_000),
        persona: None,
        capability: None,
        outcome_text: None,
        idempotency_key: None,
        aliases: vec![],
        labels: if good_first {
            vec!["good-first".into()]
        } else {
            vec![]
        },
        scope: vec![],
        links: vec![],
        acceptance: vec![],
    };
    let text = doc::render(&Ticket {
        front,
        body: "b".into(),
    })
    .expect("render");
    tree.insert(format!("raw/{id}.md"), text.into_bytes());
    id
}

fn event(tree: &mut Tree, id: TicketId, at: i64, body: EventBody) {
    let e = Event::new(Stamp::from_unix(at), "t", body);
    tree.insert(
        format!(".events/{id}/{}.toml", e.id),
        e.to_toml().expect("toml").into_bytes(),
    );
}

fn close(tree: &mut Tree, id: TicketId, land_at: i64, with_evidence: bool) {
    if with_evidence {
        let data = EvidenceData {
            accepts: vec![1],
            record: toml::Table::new(),
        };
        event(tree, id, land_at - 10, EventBody::Evidence(data));
    }
    let land = LandData {
        base_ref: "refs/heads/main".into(),
        commit: "abc123".into(),
        branch: "b".into(),
        pushed: false,
    };
    event(tree, id, land_at, EventBody::Land(land));
}

fn reindexed(tree: &Tree) -> Tree {
    let opts = ReindexOptions {
        version: "9.9.9",
        handle_min_len: 26,
        generators: GENERATORS,
    };
    reindex(tree, &opts).expect("reindex").tree
}

fn paths_of(tree: &Tree) -> BTreeMap<TicketId, String> {
    tree.iter()
        .filter_map(|(p, b)| {
            let t = doc::parse(p, std::str::from_utf8(b).ok()?).ok()?;
            Some((t.front.id, p.clone()))
        })
        .collect()
}

fn text(tree: &Tree, path: &str) -> String {
    String::from_utf8(
        tree.get(path)
            .unwrap_or_else(|| panic!("no {path}"))
            .clone(),
    )
    .expect("utf8")
}

struct Ledger {
    tree: Tree,
    newer: TicketId,
    older: TicketId,
}

fn ledger() -> Ledger {
    let mut tree = Tree::new();
    let small = put(
        &mut tree,
        "Small epic",
        TicketType::Epic,
        None,
        false,
        false,
    );
    put(
        &mut tree,
        "Small child",
        TicketType::Task,
        Some(small),
        false,
        false,
    );
    let big = put(
        &mut tree,
        "Large epic",
        TicketType::Epic,
        None,
        false,
        false,
    );
    put(
        &mut tree,
        "Large child one",
        TicketType::Task,
        Some(big),
        false,
        false,
    );
    put(
        &mut tree,
        "Large child two",
        TicketType::Task,
        Some(big),
        false,
        false,
    );
    let older = put(
        &mut tree,
        "Landed older",
        TicketType::Task,
        None,
        true,
        false,
    );
    close(&mut tree, older, 1_790_000_100, true);
    let newer = put(
        &mut tree,
        "Landed newer",
        TicketType::Task,
        None,
        true,
        false,
    );
    close(&mut tree, newer, 1_790_000_900, true);
    let bare = put(
        &mut tree,
        "Landed without evidence",
        TicketType::Task,
        None,
        true,
        false,
    );
    close(&mut tree, bare, 1_790_009_000, false);
    put(
        &mut tree,
        "First starter",
        TicketType::Task,
        None,
        false,
        true,
    );
    put(
        &mut tree,
        "Second starter",
        TicketType::Task,
        None,
        false,
        true,
    );
    Ledger {
        tree: reindexed(&tree),
        newer,
        older,
    }
}

#[test]
fn the_tour_has_five_stops_and_pins_the_newest_landed_the_largest_epic_and_the_first_good_first() {
    let l = ledger();
    let page = text(&l.tree, "TOUR.md");
    for n in 1..=5 {
        assert!(
            page.contains(&format!("## Stop {n}:")),
            "stop {n} missing: {page}"
        );
    }
    assert!(page.contains("Large epic"), "{page}");
    assert!(!page.contains("Small epic"), "{page}");
    assert!(page.contains("Landed newer"), "{page}");
    assert!(!page.contains("Landed older"), "{page}");
    assert!(!page.contains("Landed without evidence"), "{page}");
    assert!(
        page.contains("First starter") && !page.contains("Second starter"),
        "{page}"
    );
}

#[test]
fn a_pinned_ticket_that_vanishes_is_replaced_and_a_note_reports_it() {
    let l = ledger();
    let paths = paths_of(&l.tree);
    let view = GenInput {
        tree: &l.tree,
        version: "9.9.9",
        handle_min_len: 26,
        as_of: None,
        paths: &paths,
    };
    let first = tour::resolve(&view, &Pins::default());
    assert_eq!(first.pins.closed, Some(l.newer));
    assert!(first.notes.is_empty());

    let mut dropped = l.tree.clone();
    let gone = paths[&l.newer].clone();
    dropped.remove(&gone);
    let paths2 = paths_of(&dropped);
    let view2 = GenInput {
        tree: &dropped,
        version: "9.9.9",
        handle_min_len: 26,
        as_of: None,
        paths: &paths2,
    };
    let second = tour::resolve(&view2, &first.pins);
    assert_eq!(second.pins.closed, Some(l.older));
    assert_eq!(
        second.pins.epic, first.pins.epic,
        "still valid pins are kept"
    );
    assert_eq!(second.notes.len(), 1, "{:?}", second.notes);
    assert!(
        second.notes[0].contains(&l.newer.to_string()),
        "{:?}",
        second.notes
    );
    let page = String::from_utf8(
        tour::render_with(&view2, &second.pins, &second.notes)
            .remove(0)
            .1,
    )
    .expect("utf8");
    assert!(
        page.contains("## Notes") && page.contains(&second.notes[0]),
        "{page}"
    );
}

/// Comment events the tour never reads, on every ticket of `tree` except `skip`.
fn add_noise(tree: &mut Tree, per_ticket: usize, skip: Option<TicketId>) {
    let ids: Vec<TicketId> = paths_of(tree)
        .into_keys()
        .filter(|i| Some(*i) != skip)
        .collect();
    for id in ids {
        for n in 0..per_ticket {
            let data = frob_ledger::event::CommentData {
                subtype: frob_ledger::model::CommentSubtype::Note,
                body: format!("noise {n}"),
            };
            event(
                tree,
                id,
                1_700_000_000 + i64::try_from(n).unwrap_or(0),
                EventBody::Comment(data),
            );
        }
    }
}

// frob:ticket 01M5H85DZ6NF1Y2DACWGQ3NZVK
// frob:tests crates/frob-ledger/src/gen/tour.rs::render
#[test]
fn tour_reindex_skips_unread_event_kinds_without_changing_the_page() {
    let l = ledger();
    let before = text(&l.tree, "TOUR.md");
    let mut noisy = l.tree.clone();
    add_noise(&mut noisy, 20, Some(l.newer));
    noisy.insert(
        ".events/garbage/not-an-event.toml".into(),
        b"kind = [".to_vec(),
    );
    let after = text(&reindexed(&noisy), "TOUR.md");
    let body = |t: &str| {
        t.lines()
            .filter(|l| !l.starts_with("As of event"))
            .collect::<Vec<_>>()
            .join("\n")
    };
    assert_eq!(
        body(&before),
        body(&after),
        "unread event kinds must not move the tour"
    );
}

// frob:ticket 01M5H85DZ6NF1Y2DACWGQ3NZVK
// frob:tests crates/frob-ledger/src/gen/tour.rs::render_with
#[test]
fn tour_life_stop_still_lists_every_event_of_the_pinned_ticket() {
    let l = ledger();
    let mut noisy = l.tree.clone();
    add_noise(&mut noisy, 3, None);
    let page = text(&reindexed(&noisy), "TOUR.md");
    assert_eq!(
        page.matches("- `comment` at").count(),
        3,
        "the pinned ticket's comments belong in its life: {page}"
    );
}
