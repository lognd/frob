//! The front door and epic pages group tickets and GEN001 catches a missing one (`navigation.md` 3.1, 3.3).
// frob:ticket 01M3ZX860YGPCJE6ETPJADMNFE

use std::collections::BTreeMap;

use frob_ledger::doc;
use frob_ledger::r#gen::{GENERATORS, epic, readme};
use frob_ledger::id::TicketId;
use frob_ledger::model::{Category, Class, Frontmatter, Priority, Stamp, Ticket, TicketType};
use frob_ledger::reindex::{GenInput, ReindexOptions, Tree, reindex};

fn put(tree: &mut Tree, title: &str, ty: TicketType, parent: Option<TicketId>) -> TicketId {
    let id = TicketId::mint();
    let front = Frontmatter {
        id,
        title: title.into(),
        ty,
        flavour: None,
        category: Category::Todo,
        outcome: None,
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
        labels: vec![],
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

fn reindexed() -> Tree {
    let mut tree = Tree::new();
    let top = put(&mut tree, "Parser rewrite", TicketType::Epic, None);
    let sub = put(&mut tree, "Lexer", TicketType::Epic, Some(top));
    put(&mut tree, "Token spans", TicketType::Task, Some(sub));
    put(&mut tree, "Loose end", TicketType::Task, None);
    let opts = ReindexOptions {
        version: "9.9.9",
        handle_min_len: 26,
        generators: GENERATORS,
    };
    reindex(&tree, &opts).expect("reindex").tree
}

fn text(tree: &Tree, path: &str) -> String {
    String::from_utf8(
        tree.get(path)
            .unwrap_or_else(|| panic!("no {path}"))
            .clone(),
    )
    .expect("utf8")
}

#[test]
fn readme_lists_unfiled_first_and_the_epic_page_groups_the_sub_epic() {
    let tree = reindexed();
    let front = text(&tree, "README.md");
    let unfiled = front.find("## _unfiled (1)").expect("unfiled section");
    let epics = front.find("## Epics").expect("epics section");
    assert!(unfiled < epics, "{front}");
    assert!(
        front.contains("[parser-rewrite/](parser-rewrite/README.md)"),
        "{front}"
    );
    let page = text(&tree, "parser-rewrite/README.md");
    let sub = page.find("## Lexer (").expect("sub-epic group");
    assert!(
        page[sub..].contains("[parser-rewrite/token-spans.md](token-spans.md)"),
        "{page}"
    );
    assert!(page.contains("### todo (1)"), "{page}");
}

// frob:tests crates/frob-ledger/src/gen/epic.rs::CoverageDrift.rule
#[test]
fn a_ticket_missing_from_every_epic_page_is_reported_as_gen001() {
    let tree = reindexed();
    let paths: BTreeMap<TicketId, String> = tree
        .keys()
        .filter_map(|p| {
            let t = doc::parse(p, std::str::from_utf8(&tree[p]).ok()?).ok()?;
            Some((t.front.id, p.clone()))
        })
        .collect();
    let input = GenInput {
        tree: &tree,
        version: "9.9.9",
        handle_min_len: 26,
        as_of: None,
        paths: &paths,
    };
    let mut pages = epic::render(&input);
    pages.extend(readme::render(&input));
    assert!(epic::check(&input, &pages).is_empty());
    for (p, b) in &mut pages {
        if p == "parser-rewrite/README.md" {
            let all = String::from_utf8_lossy(b);
            let kept: Vec<&str> = all
                .lines()
                .filter(|l| !l.contains("](token-spans.md)"))
                .collect();
            *b = kept.join("\n").into_bytes();
        }
    }
    let drift = epic::check(&input, &pages);
    assert_eq!(drift.len(), 1, "{drift:?}");
    assert_eq!(drift[0].rule(), "GEN001");
    assert!(
        drift[0].to_string().contains("token-spans.md"),
        "{}",
        drift[0]
    );
}
