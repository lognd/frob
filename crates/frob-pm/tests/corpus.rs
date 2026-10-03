//! `PM034` and `PM013` markdown corpus: each block is a small ledger built from a line DSL.
// frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
// frob:ticket 01M4069TBHQ2YTFEEWHED96MPY

use std::collections::BTreeMap;

use frob_ledger::model::{Category, TicketType};
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig, TicketId};
use frob_pm::rules::{membership::evaluate, wip};
use frob_pm::{NewObject, ObjectKind, PmStore, event::Op};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_mdtest::Case;
use gob_rules::Finding;

/// A repository on `main` with a root commit, an identity and an open ledger.
fn ledger(dir: &std::path::Path) -> Ledger {
    let repo = Repo::init(dir).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(dir).expect("discover");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new("README.md").expect("path"),
            Some(b"hi\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    Ledger::open(repo, LedgerConfig::default())
}

/// `key=value` words of a DSL line.
fn opts<'a>(words: &[&'a str]) -> BTreeMap<&'a str, &'a str> {
    words.iter().filter_map(|w| w.split_once('=')).collect()
}

/// Build the ledger a block describes and evaluate the block's rule (`PM034` or `PM013`) over it.
fn runner(case: &Case) -> Vec<Finding> {
    // frob:tests crates/frob-pm/src/rules/membership.rs::pm034
    // frob:tests crates/frob-pm/src/rules/membership.rs::evaluate
    // frob:tests crates/frob-pm/src/rules/membership.rs::milestones
    let dir = tempfile::tempdir().expect("tempdir");
    let ledger = ledger(dir.path());
    let mut keys: BTreeMap<String, TicketId> = BTreeMap::new();
    let mut limit = 0_u32;
    for line in case.text.lines().filter(|l| !l.trim().is_empty()) {
        let w: Vec<&str> = line.split_whitespace().collect();
        let o = opts(&w);
        match w[0] {
            "epic" | "task" => {
                let ty = if w[0] == "epic" {
                    TicketType::Epic
                } else {
                    TicketType::Task
                };
                let mut t = NewTicket::new(w[1], ty);
                t.parent = o.get("parent").map(|k| keys[*k]);
                t.labels = o
                    .get("labels")
                    .map(|l| l.split(',').map(str::to_owned).collect())
                    .unwrap_or_default();
                let id = ledger.new_ticket(t).expect("ticket").ticket.front.id;
                if o.get("state") == Some(&"in_progress") {
                    ledger
                        .transition(id, Category::InProgress, None, None)
                        .expect("transition");
                }
                keys.insert(w[1].to_owned(), id);
            }
            "limit" => limit = w[1].parse().expect("limit"),
            "milestone" => {
                let applied = PmStore::new(&ledger)
                    .create(NewObject::Milestone {
                        version: w[1].to_owned(),
                        goal: "goal".to_owned(),
                        target: None,
                        criteria: Vec::new(),
                    })
                    .expect("milestone");
                for k in o
                    .get("epics")
                    .copied()
                    .unwrap_or("")
                    .split(',')
                    .filter(|k| !k.is_empty())
                {
                    PmStore::new(&ledger)
                        .set_member(ObjectKind::Milestone, applied.object.id(), keys[k], Op::Add)
                        .expect("member");
                }
            }
            other => unreachable!("unknown DSL verb {other}"),
        }
    }
    if case.rule.to_string() == "PM013" {
        // frob:tests crates/frob-pm/src/rules/wip.rs::pm013
        // frob:tests crates/frob-pm/src/rules/wip.rs::evaluate
        // frob:tests crates/frob-pm/src/rules/wip.rs::in_progress
        return wip::evaluate(&ledger, limit).expect("evaluate").findings;
    }
    evaluate(&ledger).expect("evaluate").findings
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
