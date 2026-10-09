//! The merge driver on a ticket-branch checkout: two branches add events to one ticket, git merges, the driver unions and refolds.
// frob:ticket 01M4A61GB9Y9M45R78K2Z70Y1B
#![cfg(unix)]

mod common;

use std::path::Path;
use std::sync::Arc;

use frob_ledger::branch::init_branch;
use frob_ledger::model::{CommentSubtype, Priority, TicketType};
use frob_ledger::ops::{NewTicket, Patch};
use frob_ledger::{Layout, Ledger, LedgerConfig};
use gob_git::Repo;

fn git(cwd: &Path, args: &[&str]) -> String {
    let out = std::process::Command::new("git")
        .args(args)
        .current_dir(cwd)
        .output()
        .expect("git");
    format!(
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

/// A ledger on `branch` of the repository at `root`, reading and writing the ticket-branch layout.
fn ledger(root: &Path, branch: &str) -> Ledger {
    let repo = Repo::discover(root).expect("discover");
    let cfg = LedgerConfig {
        ref_name: branch.to_owned(),
        ..LedgerConfig::default()
    };
    Ledger::open(repo, cfg, Arc::new(gob_time::SystemClock)).with_layout(Layout::Branch)
}

// frob:tests crates/frob/src/ticket/merge_cmd.rs::MergeDriver
#[test]
fn two_branches_adding_events_merge_through_the_driver_on_a_ticket_branch() {
    let dir = common::git_repo();
    let p = dir.path();
    let repo = Repo::discover(p).expect("discover");
    init_branch(&repo, "frob-tickets", 5).expect("branch init");
    let id = ledger(p, "frob-tickets")
        .new_ticket(NewTicket::new("Contended", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    git(p, &["branch", "left", "frob-tickets"]);
    git(p, &["branch", "right", "frob-tickets"]);
    let mut patch = Patch::default();
    patch.sets.push((
        "priority".to_owned(),
        Some(toml::Value::String("high".to_owned())),
    ));
    ledger(p, "left").update(id, &patch).expect("update");
    ledger(p, "right")
        .comment(id, CommentSubtype::Note, "from the right")
        .expect("comment");

    let bin = Path::new(env!("CARGO_BIN_EXE_frob"));
    git(
        p,
        &[
            "config",
            "merge.frob-ledger.driver",
            &format!("{} merge-driver %O %A %B %P", bin.display()),
        ],
    );
    git(p, &["checkout", "-q", "left"]);
    assert!(
        git(p, &["show", "left:.gitattributes"]).contains("*/*.md merge=frob-ledger"),
        "branch init wrote the layout's attributes"
    );
    let merged = git(p, &["merge", "--no-edit", "right"]);
    assert!(!merged.contains("CONFLICT"), "{merged}");
    assert_eq!(git(p, &["status", "--porcelain"]).trim(), "");

    let events = std::fs::read_dir(p.join(format!(".events/{id}")))
        .expect("events dir")
        .count();
    assert_eq!(events, 3, "create, priority and comment");
    let text = std::fs::read_to_string(p.join("_unfiled/contended.md")).expect("ticket file");
    let t = frob_ledger::doc::parse("m", &text).expect("parse");
    assert_eq!(t.front.priority, Priority::High);
}
