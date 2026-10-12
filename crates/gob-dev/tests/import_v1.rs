//! The v1 importer on a small synthetic ledger: mapping, aliases, integrity, refusals.

use std::path::Path;

use frob_ledger::model::{Category, Outcome, TicketType};
use frob_ledger::{doc, event::Event};
use gob_dev::import_v1::{
    ImportError, ImportOptions, load_tree, render_id_map, render_report_md, render_selection,
    render_table, run, verify,
};

const HEAD: &str = "origin: agent\ncreated: '2026-10-02'\npriority: high\nmilestone: 2.0.0\nworktree: /x\nbranch: t\n";

fn write(root: &Path, id: &str, front: &str, body: &str, report: Option<&str>) {
    let dir = root.join(id);
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("ticket.md"),
        format!("---\nid: {id}\n{front}---\n{body}\n"),
    )
    .expect("write");
    if let Some(r) = report {
        std::fs::write(dir.join("done-report.md"), r).expect("report");
    }
}

fn fixture(root: &Path) {
    write(
        root,
        "T-0001",
        &format!("title: Epic\nstate: queued\nkind: docs\n{HEAD}tier: epic\n"),
        "epic body",
        None,
    );
    write(
        root,
        "T-0002",
        &format!(
            "title: Done thing\nstate: done\nkind: feature\ntier: ticket\n{HEAD}parent: T-0001\nblocked_by:\n- T-0003\npoints: 5\nscope:\n- src/**\ncomponent: gob-text\nacceptance:\n- text: it works\n  evidence:\n  - 'cmd:cargo test exit=0 sha256=abcdef123456'\nevidence:\n- 'cmd:cargo test exit=0 sha256=abcdef123456'\n"
        ),
        "body",
        Some("## Done report\n\nshipped"),
    );
    write(
        root,
        "T-0003",
        &format!("title: Dropped\nstate: dropped\nkind: ux\n{HEAD}"),
        "text\n\n## Drop reason\n- superseded by T-0002\n\n## Other\nmore",
        None,
    );
    write(
        root,
        "T-draft-abc",
        "title: Draft\nstate: queued\nkind: bug\n",
        "",
        None,
    );
}

fn opts(root: &Path, dry_run: bool) -> ImportOptions {
    ImportOptions {
        from: root.join("v1"),
        to: root.join("v2"),
        dry_run,
        selection: None,
        privacy_dir: None,
        merge: false,
        open_category: Category::Todo,
    }
}

// frob:tests crates/gob-dev/src/import_v1.rs::run
#[test]
fn imports_maps_and_verifies() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    fixture(&tmp.path().join("v1"));
    let report = run(&opts(tmp.path(), false)).expect("import");
    assert_eq!(report.rows.len(), 3, "draft skipped");
    assert_eq!(report.dropped.get("worktree"), Some(&3));
    let tree = load_tree(&tmp.path().join("v2")).expect("load");
    assert!(verify(&tree).is_empty());
    let by_alias = |alias: &str| {
        tree.iter()
            .map(|t| doc::parse("t", &t.ticket_md).expect("parse"))
            .find(|t| t.front.aliases == [alias])
            .expect("alias present")
    };
    let epic = by_alias("T-0001");
    assert_eq!(epic.front.ty, TicketType::Epic);
    assert_eq!(epic.front.category, Category::Todo);
    let done = by_alias("T-0002");
    assert_eq!(done.front.outcome, Some(Outcome::Done));
    assert_eq!(done.front.parent, Some(epic.front.id));
    assert_eq!(done.front.links.len(), 1);
    assert!(done.front.labels.contains(&"component:gob-text".to_owned()));
    assert!(done.front.labels.contains(&"milestone:2.0.0".to_owned()));
    let dropped = by_alias("T-0003");
    assert_eq!(dropped.front.outcome, Some(Outcome::WontFix));
    assert_eq!(dropped.front.flavour.as_deref(), Some("ux"));
    let kinds: Vec<String> = tree
        .iter()
        .flat_map(|t| t.events.iter())
        .map(|(id, text)| Event::parse(*id, text).expect("event").kind)
        .collect();
    assert!(kinds.iter().any(|k| k == "evidence"));
    assert_eq!(kinds.iter().filter(|k| *k == "comment").count(), 2);
}

#[test]
fn ulids_keep_creation_order() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    fixture(&tmp.path().join("v1"));
    let report = run(&opts(tmp.path(), true)).expect("dry run");
    let ulids: Vec<&str> = report.rows.iter().map(|r| r.ulid.as_str()).collect();
    let mut sorted = ulids.clone();
    sorted.sort_unstable();
    assert_eq!(ulids, sorted);
    assert!(!tmp.path().join("v2").exists(), "dry run writes nothing");
}

#[test]
fn refuses_a_non_empty_target() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    fixture(&tmp.path().join("v1"));
    std::fs::create_dir_all(tmp.path().join("v2")).expect("v2");
    std::fs::write(tmp.path().join("v2/x"), "x").expect("x");
    let err = run(&opts(tmp.path(), false)).expect_err("refused");
    assert!(matches!(err, ImportError::TargetNotEmpty(_)));
}

fn dry_report() -> gob_dev::import_v1::ImportReport {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    fixture(&tmp.path().join("v1"));
    run(&opts(tmp.path(), true)).expect("dry run")
}

// frob:tests crates/gob-dev/src/import_v1.rs::render_table
#[test]
fn renders_the_summary_table() {
    let table = render_table(&dry_report().rows);
    assert_eq!(table.len(), 4, "header plus three rows");
}

// frob:tests crates/gob-dev/src/import_v1.rs::render_id_map
#[test]
fn renders_the_id_map() {
    assert!(render_id_map(&dry_report().rows).starts_with("T-0001\t"));
}

// frob:tests crates/gob-dev/src/import_v1.rs::render_report_md
#[test]
fn renders_the_migration_report() {
    let md = render_report_md(&dry_report());
    assert!(md.contains("| `worktree` | 3 |"));
    assert!(md.contains("3 tickets"));
}

const TICKET_SELECTION: &str = r#"
[cluster.B1]
title = "system design lint"
status = "MISSING"
disposition = "import-open"
area = "grimble"
ids = ["T-0010"]

[cluster.C2]
title = "ledger store"
status = "BUILT"
disposition = "skip-built"
ids = ["T-0011"]

[cluster.G1]
title = "gate engine"
status = "V1-INTERNAL"
disposition = "skip-v1-internal"
ids = ["T-0012", "T-0013"]

[override."T-0013"]
disposition = "import-open"
reason = "PT-9 build identity"
"#;

fn open_fixture(root: &Path, extra_body: &str) {
    for (n, body) in [
        (10, extra_body),
        (11, "built"),
        (12, "internal"),
        (13, "override"),
    ] {
        write(
            root,
            &format!("T-00{n}"),
            &format!("title: Open {n}\nstate: queued\nkind: feature\n{HEAD}"),
            body,
            None,
        );
    }
    write(
        root,
        "T-0020",
        &format!("title: Done\nstate: done\nkind: bug\n{HEAD}"),
        "d",
        None,
    );
}

fn selecting(root: &Path, dry_run: bool) -> ImportOptions {
    let sel = root.join("sel.toml");
    std::fs::write(&sel, TICKET_SELECTION).expect("selection");
    ImportOptions {
        selection: Some(sel),
        ..opts(root, dry_run)
    }
}

// frob:tests crates/gob-dev/src/import_v1/select.rs::Selection.decide
// frob:tests crates/gob-dev/src/import_v1/select.rs::Disposition.name
// frob:tests crates/gob-dev/src/import_v1/select.rs::Disposition.imports
// frob:tests crates/gob-dev/src/import_v1/select.rs::Selection.stale
#[test]
fn selection_imports_requirement_bearing_open_tickets_only() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    open_fixture(&tmp.path().join("v1"), "body");
    let report = run(&selecting(tmp.path(), false)).expect("import");
    let count = |d: &str| report.dispositions.get(d).copied().unwrap_or(0);
    assert_eq!(count("import-open"), 2);
    assert_eq!(count("skip-built"), 1);
    assert_eq!(count("skip-v1-internal"), 1);
    assert_eq!(count("history-done"), 1);
    assert_eq!(report.rows.len(), 3, "two open plus one closed");
    assert_eq!(report.skipped.len(), 2);
    assert!(report.skipped.iter().all(|s| !s.reason.is_empty()));
    let tree = load_tree(&tmp.path().join("v2")).expect("load");
    let tickets: Vec<_> = tree
        .iter()
        .map(|t| doc::parse("t", &t.ticket_md).expect("parse"))
        .collect();
    let by_alias = |a: &str| tickets.iter().find(|t| t.front.aliases == [a]).expect(a);
    let b1 = by_alias("T-0010");
    assert!(b1.front.labels.contains(&"v1-cluster:B1".to_owned()));
    assert!(b1.front.labels.contains(&"area:grimble".to_owned()));
    let ov = by_alias("T-0013");
    assert!(ov.front.labels.contains(&"v1-cluster:G1".to_owned()));
    assert!(!ov.front.labels.iter().any(|l| l.starts_with("area:")));
    assert_eq!(ov.front.category, Category::Todo);
    assert!(tickets.iter().all(|t| t.front.aliases != ["T-0011"]));
    let open: Vec<_> = report.open.iter().map(|r| r.v1.as_str()).collect();
    assert_eq!(open, ["T-0010", "T-0013"]);
    assert!(
        render_selection(&report.dispositions, &report.open, &report.skipped)
            .iter()
            .any(|l| l.contains("import-open"))
    );
}

// frob:tests crates/gob-dev/src/import_v1.rs::run
#[test]
fn an_unmapped_open_ticket_stops_the_run() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    open_fixture(&tmp.path().join("v1"), "body");
    write(
        &tmp.path().join("v1"),
        "T-0099",
        &format!("title: New\nstate: queued\nkind: bug\n{HEAD}"),
        "x",
        None,
    );
    let err = run(&selecting(tmp.path(), true)).expect_err("unmapped");
    assert!(err.to_string().contains("T-0099"), "{err}");
}

// frob:tests crates/gob-dev/src/import_v1/sanitize.rs::Sanitizer.text
#[test]
fn home_paths_and_private_terms_are_redacted() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    open_fixture(
        &tmp.path().join("v1"),
        "see /home/alice/projects/app/src/x.rs and zorblax-corp",
    );
    let common = tmp.path().join("common");
    std::fs::create_dir_all(common.join("frob")).expect("mkdir");
    std::fs::write(
        common.join("frob/privacy.toml"),
        "[[rule]]\npattern = \"zorblax-corp\"\nreplace = \"<customer>\"\n",
    )
    .expect("rules");
    let mut o = selecting(tmp.path(), false);
    o.privacy_dir = Some(common);
    let report = run(&o).expect("import");
    assert!(report.private_rules_loaded);
    assert!(report.blocked.is_empty());
    assert!(
        report
            .redactions
            .iter()
            .any(|(id, w)| id == "T-0010" && w.contains("path"))
    );
    assert!(
        report
            .redactions
            .iter()
            .any(|(_, w)| w.contains("private term rule <customer>#"))
    );
    assert!(!report.redactions.iter().any(|(_, w)| w.contains("zorblax")));
    let tree = load_tree(&tmp.path().join("v2")).expect("load");
    let text: String = tree
        .iter()
        .flat_map(|t| {
            std::iter::once(t.ticket_md.clone()).chain(t.events.iter().map(|(_, e)| e.clone()))
        })
        .collect();
    assert!(!text.contains("/home/alice"), "home path leaked");
    assert!(!text.contains("zorblax"), "private term leaked");
    assert!(text.contains("<customer>"));
}

fn dir_count(dir: &Path) -> usize {
    std::fs::read_dir(dir).expect("ls").count()
}

// frob:ticket 01M43BEAR3MSMEANKENBQ1KDT7
// frob:tests crates/gob-dev/src/import_v1.rs::run
#[test]
fn merge_adds_only_new_ticket_directories() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    fixture(&tmp.path().join("v1"));
    run(&opts(tmp.path(), false)).expect("first import");
    let before = load_tree(&tmp.path().join("v2")).expect("load");
    std::fs::write(tmp.path().join("v2/README"), "not a ticket").expect("stray file");
    let second = tmp.path().join("v1b");
    std::fs::create_dir(&second).expect("v1b");
    write(
        &second,
        "T-0050",
        "title: Later\nstate: queued\nkind: bug\norigin: agent\ncreated: '2026-10-03'\n",
        "later",
        None,
    );
    let mut o = opts(tmp.path(), false);
    o.from = second;
    o.merge = true;
    let report = run(&o).expect("merge");
    assert_eq!(report.rows.len(), 1);
    assert_eq!(dir_count(&tmp.path().join("v2")), before.len() + 2);
    for t in &before {
        let md = std::fs::read_to_string(tmp.path().join(format!("v2/{}/ticket.md", t.id)))
            .expect("old ticket");
        assert_eq!(md, t.ticket_md, "existing ticket untouched");
    }
}

// frob:ticket 01M43BEAR3MSMEANKENBQ1KDT7
// frob:tests crates/gob-dev/src/import_v1.rs::run
#[test]
fn merge_refuses_id_and_alias_collisions_without_writing() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    fixture(&tmp.path().join("v1"));
    run(&opts(tmp.path(), false)).expect("first import");
    let v2 = tmp.path().join("v2");
    let count = dir_count(&v2);
    // Same alias, different creation date: a fresh id but the alias T-0001 is taken.
    let other = tmp.path().join("v1b");
    std::fs::create_dir(&other).expect("v1b");
    write(
        &other,
        "T-0001",
        "title: Clash\nstate: queued\nkind: bug\norigin: agent\ncreated: '2026-09-01'\n",
        "x",
        None,
    );
    write(
        &other,
        "T-0060",
        "title: Fine\nstate: queued\nkind: bug\norigin: agent\ncreated: '2026-09-02'\n",
        "x",
        None,
    );
    let mut o = opts(tmp.path(), false);
    o.from = other;
    o.merge = true;
    let err = run(&o).expect_err("alias refused");
    assert!(matches!(&err, ImportError::Collision(m) if m.contains("alias T-0001")));
    assert_eq!(dir_count(&v2), count, "nothing written");
    // Same ledger again: ids carry a random tail, so every alias collides.
    o.from = tmp.path().join("v1");
    let err = run(&o).expect_err("repeat refused");
    assert!(matches!(&err, ImportError::Collision(m) if m.contains("alias T-0003")));
    assert_eq!(dir_count(&v2), count, "nothing written");
}

// frob:ticket 01M43BEAR3MSMEANKENBQ1KDT7
// frob:tests crates/gob-dev/src/import_v1.rs::run
#[test]
fn open_category_triage_places_open_tickets_in_triage() {
    let tmp = tempfile::tempdir().expect("tmp");
    std::fs::create_dir(tmp.path().join("v1")).expect("v1");
    fixture(&tmp.path().join("v1"));
    let mut o = opts(tmp.path(), false);
    o.open_category = Category::Triage;
    run(&o).expect("import");
    let tree = load_tree(&tmp.path().join("v2")).expect("load");
    assert!(verify(&tree).is_empty());
    let docs: Vec<_> = tree
        .iter()
        .map(|t| doc::parse("t", &t.ticket_md).expect("parse"))
        .collect();
    let by = |alias: &str| {
        docs.iter()
            .find(|d| d.front.aliases == [alias])
            .expect("alias")
    };
    assert_eq!(by("T-0001").front.category, Category::Triage);
    assert_eq!(
        by("T-0002").front.category,
        Category::Done,
        "closed stays done"
    );
    assert_eq!(by("T-0003").front.category, Category::Done);
}

// frob:ticket 01M4FCZT2N5WN3VPVJ8KB92Z06
// frob:tests crates/gob-dev/src/import_v1.rs::run
#[test]
fn crlf_tickets_import_and_a_sprint_becomes_a_label() {
    let tmp = tempfile::tempdir().expect("tmp");
    let v1 = tmp.path().join("v1");
    for (id, sprint) in [("T-0001", "sprint: s7\n"), ("T-0002", "sprint: 12\n")] {
        let dir = v1.join(id);
        std::fs::create_dir_all(&dir).expect("mkdir");
        let text = format!(
            "---\nid: {id}\ntitle: Crlf\nstate: queued\nkind: bug\n{HEAD}{sprint}---\nbody\n"
        )
        .replace('\n', "\r\n");
        std::fs::write(dir.join("ticket.md"), text).expect("write");
    }
    let report = run(&opts(tmp.path(), false)).expect("CRLF tickets import");
    assert_eq!(report.rows.len(), 2);
    assert!(!report.dropped.contains_key("sprint"));
    let tree = load_tree(&tmp.path().join("v2")).expect("load");
    let labels = |alias: &str| {
        tree.iter()
            .map(|t| doc::parse("t", &t.ticket_md).expect("parse"))
            .find(|t| t.front.aliases == [alias])
            .expect("alias present")
            .front
            .labels
    };
    assert!(labels("T-0001").contains(&"sprint:s7".to_owned()));
    assert!(labels("T-0002").contains(&"sprint:12".to_owned()));
}
