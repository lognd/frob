//! The grimble-ci static `frob` verb table (CI012) must equal the real clap verb tree.
//!
//! `grimble-ci` may not depend on the CLI (layering), so it keeps a copied table; this is the
//! drift test that lives next to the CLI. Hidden deprecated aliases are real verbs and count.
// frob:ticket 01M5KE9866QXR3E94E7J94DZY4

use std::collections::{BTreeMap, BTreeSet};

/// Verb inventory: top-level verb to its direct subcommand words (empty for a leaf verb).
type Inventory = BTreeMap<String, BTreeSet<String>>;

/// The inventory of the real clap tree: first word of every verb path, and its second word if any.
fn tree_inventory() -> Inventory {
    let mut out = Inventory::new();
    for path in frob_cli::cli().verb_flags().keys() {
        let mut words = path.split(' ');
        let Some(top) = words.next().filter(|w| !w.is_empty()) else {
            continue;
        };
        let subs = out.entry(top.to_owned()).or_default();
        if let Some(sub) = words.next() {
            subs.insert(sub.to_owned());
        }
    }
    // clap adds `help` at the root itself, after the tree walked by `verb_flags` is built.
    out.entry("help".to_owned()).or_default();
    out
}

/// The inventory of a static table in the shape of `grimble_ci::VERBS`.
fn table_inventory(table: &[(&str, &[&str])]) -> Inventory {
    table
        .iter()
        .map(|(verb, subs)| {
            (
                (*verb).to_owned(),
                subs.iter().map(|s| (*s).to_owned()).collect(),
            )
        })
        .collect()
}

/// Every difference between `table` and `tree`, one line each, empty when they agree.
fn drift(table: &Inventory, tree: &Inventory) -> Vec<String> {
    let mut out = Vec::new();
    for (verb, subs) in tree {
        let Some(known) = table.get(verb) else {
            out.push(format!("verb `{verb}` is missing from the table"));
            continue;
        };
        for sub in subs.difference(known) {
            out.push(format!("`{verb} {sub}` is missing from the table"));
        }
        for sub in known.difference(subs) {
            out.push(format!(
                "`{verb} {sub}` is in the table but not in the tree"
            ));
        }
    }
    for verb in table.keys().filter(|v| !tree.contains_key(*v)) {
        out.push(format!("verb `{verb}` is in the table but not in the tree"));
    }
    out
}

/// The real tree, printed on failure so a drifted table is easy to fix.
fn render(inv: &Inventory) -> String {
    inv.iter()
        .map(|(v, s)| format!("{v}: {s:?}"))
        .collect::<Vec<_>>()
        .join("\n")
}

/// The table in the live crate agrees with the real clap tree.
// frob:tests Cli.verb_flags
#[test]
fn grimble_ci_table_matches_the_real_verb_tree() {
    let tree = tree_inventory();
    let table = table_inventory(grimble_ci::VERBS);
    let diff = drift(&table, &tree);
    assert!(
        diff.is_empty(),
        "grimble-ci VERBS drifted from the clap tree:\n{}\nreal tree:\n{}",
        diff.join("\n"),
        render(&tree)
    );
}

/// A verb the table lacks, a stale verb and a stale or missing subcommand each fail, both directions.
// frob:tests Cli.verb_flags
#[test]
fn drift_is_reported_in_both_directions() {
    let tree = tree_inventory();
    let mut table = table_inventory(grimble_ci::VERBS);
    assert!(drift(&table, &tree).is_empty(), "baseline must agree");

    let (verb, subs) = tree
        .iter()
        .find(|(_, s)| !s.is_empty())
        .expect("some verb has subcommands");
    let sub = subs.iter().next().expect("a subcommand").clone();

    table.remove(verb);
    assert!(!drift(&table, &tree).is_empty(), "verb missing from table");

    table = table_inventory(grimble_ci::VERBS);
    table.get_mut(verb).expect("verb").remove(&sub);
    assert!(
        !drift(&table, &tree).is_empty(),
        "subcommand missing from table"
    );

    table = table_inventory(grimble_ci::VERBS);
    table.insert("no-such-verb".to_owned(), BTreeSet::new());
    assert!(!drift(&table, &tree).is_empty(), "stale verb in table");

    table = table_inventory(grimble_ci::VERBS);
    table
        .get_mut(verb)
        .expect("verb")
        .insert("no-such-sub".to_owned());
    assert!(
        !drift(&table, &tree).is_empty(),
        "stale subcommand in table"
    );
}
