//! The crunk importer on a synthetic crunk ledger: dry-run listing, friction dispositions, alias namespace.
// frob:ticket 01M43AVMN1DWBVTYW37JBTM6EF

use std::path::Path;

use frob_evidence::import_crunk::{self, ALIAS_PREFIX, REPO, clone_args, render_dispositions};
use frob_evidence::import_v1::{self, ImportError, ImportOptions, load_tree};
use frob_ledger::doc;
use frob_ledger::model::{Category, Outcome};

const HEAD: &str = "origin: agent\ncreated: '2026-10-02'\npriority: low\n";

fn write(root: &Path, id: &str, front: &str) {
    let dir = root.join(id);
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("ticket.md"),
        format!("---\nid: {id}\n{front}---\nbody of {id}\n"),
    )
    .expect("write");
}

/// A crunk ledger: one done, one open product item, one open frob-friction tracker.
fn crunk(root: &Path) {
    write(
        root,
        "T-0041",
        &format!("title: Shipped\nstate: done\nkind: feature\n{HEAD}"),
    );
    write(
        root,
        "T-0042",
        &format!("title: Palette ramps\nstate: queued\nkind: feature\n{HEAD}"),
    );
    write(
        root,
        "T-0043",
        &format!("title: Register TOKENS001 in frob\nstate: queued\nkind: bug\n{HEAD}"),
    );
}

const SELECTION: &str = r#"
[cluster.C1]
title = "crunk product"
status = "OPEN"
disposition = "import-open"
area = "crunk"
ids = ["T-0042"]

[cluster.C3]
title = "frob friction"
status = "FROB-FRICTION"
disposition = "wont-fix-history"
area = "crunk"
ids = ["T-0043"]
"#;

fn setup(tmp: &Path) -> ImportOptions {
    std::fs::create_dir(tmp.join("src")).expect("src");
    crunk(&tmp.join("src"));
    std::fs::write(tmp.join("sel.toml"), SELECTION).expect("sel");
    import_crunk::options(
        tmp.join("src"),
        tmp.join("v2"),
        tmp.join("sel.toml"),
        true,
        None,
    )
}

fn aliases_of(to: &Path) -> Vec<(String, Category, Option<Outcome>)> {
    load_tree(to)
        .expect("load")
        .iter()
        .map(|t| doc::parse("t", &t.ticket_md).expect("parse"))
        .map(|t| {
            (
                t.front.aliases[0].clone(),
                t.front.category,
                t.front.outcome,
            )
        })
        .collect()
}

// frob:tests crates/frob-evidence/src/import_crunk.rs::render_dispositions
// frob:tests crates/frob-evidence/src/import_crunk.rs::options
#[test]
fn dry_run_counts_dispositions_and_lists_open_tickets() {
    let tmp = tempfile::tempdir().expect("tmp");
    let opts = setup(tmp.path());
    let report = import_v1::run(&opts).expect("dry run");
    assert_eq!(report.dispositions.get("history-done"), Some(&1));
    assert_eq!(report.dispositions.get("import-open"), Some(&1));
    assert_eq!(report.dispositions.get("wont-fix-history"), Some(&1));
    assert_eq!(report.open.len(), 1);
    assert_eq!(report.open[0].v1, "T-0042");
    assert!(!tmp.path().join("v2").exists(), "a dry run writes nothing");
}

// frob:tests crates/frob-evidence/src/import_crunk.rs::render_dispositions
#[test]
fn friction_tracker_shows_disposition_and_reason_and_is_not_open() {
    let tmp = tempfile::tempdir().expect("tmp");
    let mut opts = setup(tmp.path());
    let report = import_v1::run(&opts).expect("dry run");
    assert!(report.open.iter().all(|o| o.v1 != "T-0043"));
    let lines = render_dispositions(&report).join("\n");
    let row = lines
        .lines()
        .find(|l| l.starts_with("T-0043"))
        .expect("listed");
    assert!(row.contains("wont-fix-history"), "{row}");
    assert!(row.contains("frob friction"), "reason shown: {row}");
    opts.dry_run = false;
    import_v1::run(&opts).expect("write");
    let found = aliases_of(&tmp.path().join("v2"));
    let (_, cat, outcome) = found
        .iter()
        .find(|(a, ..)| a == "crunk:T-0043")
        .expect("imported");
    assert_eq!(*cat, Category::Done);
    assert_eq!(*outcome, Some(Outcome::WontFix));
}

// frob:tests crates/frob-evidence/src/import_crunk.rs::options
#[test]
fn aliases_are_namespaced_and_a_rerun_refuses() {
    let tmp = tempfile::tempdir().expect("tmp");
    let mut opts = setup(tmp.path());
    // A frob ledger that already holds its own T-0042.
    let frob_src = tmp.path().join("frob");
    std::fs::create_dir(&frob_src).expect("frob");
    write(
        &frob_src,
        "T-0042",
        &format!("title: Frob's own\nstate: done\nkind: bug\n{HEAD}"),
    );
    let own = ImportOptions {
        from: frob_src,
        to: tmp.path().join("v2"),
        dry_run: false,
        selection: None,
        privacy_dir: None,
        merge: false,
        open_category: Category::Todo,
        alias_prefix: None,
        extra_labels: Vec::new(),
    };
    import_v1::run(&own).expect("frob ledger");
    opts.dry_run = false;
    import_v1::run(&opts).expect("crunk merges beside it");
    let found = aliases_of(&tmp.path().join("v2"));
    assert!(found.iter().any(|(a, ..)| a == "T-0042"));
    assert!(
        found
            .iter()
            .any(|(a, ..)| a == &format!("{ALIAS_PREFIX}T-0042"))
    );
    assert_ne!(format!("{ALIAS_PREFIX}T-0042"), "T-0042");
    let again = import_v1::run(&opts);
    assert!(matches!(again, Err(ImportError::Collision(_))), "{again:?}");
}

// frob:tests crates/frob-evidence/src/import_crunk.rs::clone_args
// frob:tests crates/frob-evidence/src/import_crunk.rs::fetch
#[test]
fn the_fetch_is_a_shallow_read_only_clone() {
    let args = clone_args(REPO, "main", Path::new("w/src"));
    assert_eq!(&args[..3], ["repo", "clone", REPO]);
    assert!(args.contains(&"--depth=1".to_owned()));
    assert!(args.iter().all(|a| a != "push"));
}
