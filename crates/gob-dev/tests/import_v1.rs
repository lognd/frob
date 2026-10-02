//! The v1 importer on a small synthetic ledger: mapping, aliases, integrity, refusals.

use std::path::Path;

use frob_ledger::model::{Category, Outcome, TicketType};
use frob_ledger::{doc, event::Event};
use gob_dev::import_v1::{ImportError, ImportOptions, load_tree, run, verify};

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
    }
}

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
